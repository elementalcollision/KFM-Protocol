import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from f_operator_service import crud, schemas
from f_operator_service.models.experiment import Experiment, ExperimentStatusEnum
from f_operator_service.services.feature_flag_service import FeatureFlagService
from f_operator_service.services.metrics_service import ExperimentMetricsService
from f_operator_service.services.sandbox_service import SandboxService
# from f_operator_service.core.config import get_settings # For thresholds, etc.

logger = logging.getLogger(__name__)

class ExperimentService:
    def __init__(
        self,
        db: AsyncSession, # Pass session per request? Or factory?
        feature_flag_service: FeatureFlagService,
        metrics_service: ExperimentMetricsService,
        sandbox_service: SandboxService,
        config: Optional[Dict] = None # For thresholds etc.
    ):
        self.db = db # Note: Consider passing session per method if service is singleton
        self.feature_flag_service = feature_flag_service
        self.metrics_service = metrics_service
        self.sandbox_service = sandbox_service
        # self.settings = get_settings() # Or pass config dict
        self.config = config or {}
        logger.info("Initialized ExperimentService")

    async def get_experiment(self, experiment_id: int) -> Optional[Experiment]:
        """Get experiment details from DB."""
        return await crud.get_experiment(self.db, experiment_id=experiment_id)

    async def create_experiment(self, experiment_in: schemas.ExperimentCreate) -> Experiment:
        """Create a new experiment definition."""
        # TODO: Add validation (e.g., variant weights sum to 1?)
        return await crud.create_experiment(self.db, obj_in=experiment_in)

    async def update_experiment_config(self, experiment_id: int, update_data: schemas.ExperimentUpdate) -> Optional[Experiment]:
        """Update experiment configuration (only allowed in DRAFT state)."""
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            return None
        if experiment.status != ExperimentStatusEnum.DRAFT:
            raise ValueError("Cannot update configuration of an experiment unless it is in DRAFT state.")
        return await crud.update_experiment(self.db, db_obj=experiment, obj_in=update_data)
        
    async def list_experiments(self, skip: int = 0, limit: int = 100, status: Optional[ExperimentStatusEnum] = None) -> Tuple[List[Experiment], int]:
         """List experiments with optional status filter."""
         return await crud.get_experiments(self.db, skip=skip, limit=limit, status=status)

    async def start_experiment(self, experiment_id: int, reason: Optional[str] = None) -> Experiment:
        """Start an experiment."""
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        if experiment.status != ExperimentStatusEnum.DRAFT:
            raise ValueError(f"Cannot start experiment {experiment_id}: current state is {experiment.status.value}, expected DRAFT")

        # Activate feature flag override with experiment configuration
        flag_name = experiment.feature_flag
        # Construct the flag config for the dynamic override
        # This needs to map experiment variants/audience to flag rules
        # Example: Assuming a simple structure where variants map to flag values
        # More complex mapping might be needed based on flag system capabilities
        override_config = {
            "is_active": True,
            "targeting": experiment.audience, # Assuming audience schema matches flag targeting
            "variants": {v.name: v.parameters for v in experiment.variants} # Or map to specific flag return values
        }
        self.feature_flag_service.set_dynamic_flag_override(flag_name, override_config)
        logger.info(f"Activated dynamic override for flag '{flag_name}' for experiment {experiment_id}")
        
        # Update experiment status in DB
        updated_experiment = await crud.update_experiment_status(self.db, db_obj=experiment, new_status=ExperimentStatusEnum.RUNNING)
        logger.info(f"Started experiment {experiment_id} ('{updated_experiment.name}')")
        
        # Optional: Create sandboxes if needed by strategy
        # for variant in updated_experiment.variants:
        #    await self.sandbox_service.create_sandbox(experiment_id, variant['name'], agent_id) # Need agent context?
            
        return updated_experiment

    async def pause_experiment(self, experiment_id: int, reason: Optional[str] = None) -> Experiment:
         """Pause a running experiment."""
         experiment = await self.get_experiment(experiment_id)
         if not experiment:
             raise ValueError(f"Experiment {experiment_id} not found")
         if experiment.status != ExperimentStatusEnum.RUNNING:
             raise ValueError(f"Cannot pause experiment {experiment_id}: current state is {experiment.status.value}, expected RUNNING")
         
         # Deactivate feature flag override
         self.feature_flag_service.remove_dynamic_flag_override(experiment.feature_flag)
         logger.info(f"Removed dynamic override for flag '{experiment.feature_flag}' for paused experiment {experiment_id}")

         # Update status
         updated_experiment = await crud.update_experiment_status(self.db, db_obj=experiment, new_status=ExperimentStatusEnum.PAUSED)
         logger.info(f"Paused experiment {experiment_id} ('{updated_experiment.name}')")
         return updated_experiment

    async def resume_experiment(self, experiment_id: int, reason: Optional[str] = None) -> Experiment:
        """Resume a paused experiment."""
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        if experiment.status != ExperimentStatusEnum.PAUSED:
            raise ValueError(f"Cannot resume experiment {experiment_id}: current state is {experiment.status.value}, expected PAUSED")

        # Reactivate feature flag override
        override_config = {
            "is_active": True,
            "targeting": experiment.audience,
            "variants": {v.name: v.parameters for v in experiment.variants} 
        }
        self.feature_flag_service.set_dynamic_flag_override(experiment.feature_flag, override_config)
        logger.info(f"Reactivated dynamic override for flag '{experiment.feature_flag}' for resumed experiment {experiment_id}")

        # Update status
        updated_experiment = await crud.update_experiment_status(self.db, db_obj=experiment, new_status=ExperimentStatusEnum.RUNNING)
        logger.info(f"Resumed experiment {experiment_id} ('{updated_experiment.name}')")
        return updated_experiment

    async def conclude_experiment(self, experiment_id: int, success: Optional[bool] = None, reason: Optional[str] = None) -> Experiment:
        """Conclude a running experiment, analyze results, and potentially rollback."""
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        if experiment.status not in [ExperimentStatusEnum.RUNNING, ExperimentStatusEnum.PAUSED]: # Allow concluding paused?
            raise ValueError(f"Cannot conclude experiment {experiment_id}: current state is {experiment.status.value}, expected RUNNING or PAUSED")

        # Fetch metrics and analyze results
        time_range = (experiment.start_date, datetime.utcnow())
        metrics_to_collect = [crit.metric for crit in experiment.success_criteria]
        metrics_data = await self.metrics_service.collect_metrics(experiment.name, metrics_to_collect, time_range)
        analysis_results = self._analyze_experiment_results(experiment, metrics_data)

        # Determine success (use manual override if provided)
        if success is None:
            success = self._evaluate_success_criteria(experiment, analysis_results)
            logger.info(f"Automated decision for experiment {experiment_id}: Success = {success}")
        else:
            logger.info(f"Manual decision for experiment {experiment_id}: Success = {success}")

        conclusion = "success" if success else "failure"
        
        # Handle feature flag (remove override regardless of outcome for conclusion)
        await self._handle_conclusion_flag(experiment, success)
        
        # Update experiment status and store results/conclusion
        status_data = {"results": analysis_results, "conclusion": conclusion}
        updated_experiment = await crud.update_experiment_status(self.db, db_obj=experiment, new_status=ExperimentStatusEnum.COMPLETED, status_data=status_data)
        logger.info(f"Concluded experiment {experiment_id} ('{updated_experiment.name}') with conclusion: {conclusion}")
        
        # Optional: Destroy sandboxes
        # await self.sandbox_service.destroy_sandbox(...) 

        return updated_experiment
        
    async def cancel_experiment(self, experiment_id: int, reason: str) -> Experiment:
         """Cancel an experiment before conclusion."""
         experiment = await self.get_experiment(experiment_id)
         if not experiment:
             raise ValueError(f"Experiment {experiment_id} not found")
         if experiment.status == ExperimentStatusEnum.COMPLETED:
              raise ValueError("Cannot cancel an already completed experiment.")
              
         # Remove feature flag override if running/paused
         if experiment.status in [ExperimentStatusEnum.RUNNING, ExperimentStatusEnum.PAUSED]:
             self.feature_flag_service.remove_dynamic_flag_override(experiment.feature_flag)
             logger.info(f"Removed dynamic override for flag '{experiment.feature_flag}' for cancelled experiment {experiment_id}")
             
         # Update status
         status_data = {"results": None, "conclusion": f"cancelled: {reason}"}
         updated_experiment = await crud.update_experiment_status(self.db, db_obj=experiment, new_status=ExperimentStatusEnum.CANCELLED, status_data=status_data)
         logger.info(f"Cancelled experiment {experiment_id} ('{updated_experiment.name}'). Reason: {reason}")
         return updated_experiment

    # --- Private Helper Methods --- 

    def _analyze_experiment_results(self, experiment: Experiment, metrics_data: Dict) -> Dict[str, Any]:
        """Analyze collected metrics against success criteria."""
        logger.debug(f"Analyzing results for experiment {experiment.id}")
        analysis = {}
        for criterion in experiment.success_criteria:
            metric_name = criterion.metric
            if metric_name not in metrics_data or 'control' not in metrics_data[metric_name] or 'treatment' not in metrics_data[metric_name]:
                analysis[metric_name] = {"status": "missing_data", "error": "Metrics data incomplete"}
                continue
                
            control_summary = metrics_data[metric_name]["control"]
            treatment_summary = metrics_data[metric_name]["treatment"]
            
            # Handle potential errors during metric collection
            if control_summary.get("error") or treatment_summary.get("error"):
                 analysis[metric_name] = {"status": "error", "error": f"Control Error: {control_summary.get('error')}, Treatment Error: {treatment_summary.get('error')}"}
                 continue
                 
            control_mean = control_summary.get("mean")
            treatment_mean = treatment_summary.get("mean")

            if control_mean is None or treatment_mean is None:
                analysis[metric_name] = {"status": "insufficient_data", "error": "Mean value missing"}
                continue

            # Calculate relative change
            if control_mean == 0:
                relative_change = float('inf') if treatment_mean > 0 else 0
            else:
                relative_change = (treatment_mean - control_mean) / abs(control_mean) # Use abs for denominator robustness
                
            analysis[metric_name] = {
                "status": "analyzed",
                "control_mean": control_mean,
                "treatment_mean": treatment_mean,
                "relative_change": relative_change,
                "control_count": control_summary.get("count", 0),
                "treatment_count": treatment_summary.get("count", 0),
            }
            logger.debug(f"Analyzed metric '{metric_name}': {analysis[metric_name]}")

        return analysis

    def _evaluate_success_criteria(self, experiment: Experiment, analysis_results: Dict) -> bool:
        """Evaluate if the overall experiment met its success criteria based on analysis."""
        logger.debug(f"Evaluating success criteria for experiment {experiment.id}")
        all_criteria_met = True
        for criterion in experiment.success_criteria:
            metric_name = criterion.metric
            if metric_name not in analysis_results or analysis_results[metric_name]["status"] != "analyzed":
                logger.warning(f"Criterion '{metric_name}' could not be evaluated (missing/error in analysis).")
                all_criteria_met = False
                break # If one criterion fails evaluation, experiment fails

            analysis = analysis_results[metric_name]
            relative_change = analysis["relative_change"]
            threshold = criterion.threshold
            direction = criterion.direction
            
            # Check minimum sample size if defined
            min_samples = criterion.minimum_sample_size
            if min_samples and (analysis["control_count"] < min_samples or analysis["treatment_count"] < min_samples):
                 logger.info(f"Criterion '{metric_name}' did not meet minimum sample size ({min_samples}).")
                 all_criteria_met = False
                 break

            # Check direction and threshold
            criterion_met = False
            if direction == "increase" and relative_change >= threshold:
                criterion_met = True
            elif direction == "decrease" and relative_change <= threshold:
                criterion_met = True
            
            if not criterion_met:
                logger.info(f"Criterion '{metric_name}' not met (Change: {relative_change:.4f}, Threshold: {threshold}, Direction: {direction})")
                all_criteria_met = False
                break
            else:
                 logger.info(f"Criterion '{metric_name}' met.")

        logger.info(f"Overall success evaluation for experiment {experiment.id}: {all_criteria_met}")
        return all_criteria_met

    async def _handle_conclusion_flag(self, experiment: Experiment, success: bool):
        """Handle feature flag state upon experiment conclusion."""
        flag_name = experiment.feature_flag
        # Always remove the dynamic override upon conclusion
        self.feature_flag_service.remove_dynamic_flag_override(flag_name)
        logger.info(f"Removed dynamic override for flag '{flag_name}' for concluded experiment {experiment.id}")

        # Optional: If successful, potentially update the *base* flag configuration
        # This requires interacting with the config service/source, which is complex.
        # if success:
        #    logger.info(f"Experiment {experiment.id} succeeded. Consider promoting changes for flag '{flag_name}'.")
        #    # await config_service.update_feature_flag(flag_name, new_config) # Example

# Example usage (dependency injection pattern)
# def get_experiment_service(
#     db: AsyncSession = Depends(get_db),
#     ff_service: FeatureFlagService = Depends(get_feature_flag_service),
#     metrics_service: ExperimentMetricsService = Depends(get_metrics_service),
#     sandbox_service: SandboxService = Depends(get_sandbox_service)
# ) -> ExperimentService:
#     return ExperimentService(db, ff_service, metrics_service, sandbox_service) 