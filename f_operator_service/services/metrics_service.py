import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

import httpx
import numpy as np

# from f_operator_service.core.config import get_settings

logger = logging.getLogger(__name__)

class ExperimentMetricsService:
    def __init__(self, metrics_endpoint: str, timeout: int = 10):
        # self.settings = get_settings()
        # self.metrics_endpoint = self.settings.METRICS_API_ENDPOINT
        self.metrics_endpoint = metrics_endpoint
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=self.timeout)
        logger.info(f"Initialized ExperimentMetricsService with endpoint: {self.metrics_endpoint}")

    async def collect_metrics(
        self, 
        experiment_name: str, 
        metrics_to_collect: List[str], 
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Dict[str, Dict]]:
        """Collect metrics for control and treatment variants of an experiment."""
        logger.debug(f"Collecting metrics {metrics_to_collect} for experiment '{experiment_name}' in range {time_range}")
        
        collected_data = {}
        
        if not time_range:
            # Default to a reasonable time range if not provided (e.g., last hour?)
            # Or require time_range based on experiment start/end?
            # For now, let's assume time_range must be derived from the experiment object before calling this.
            logger.warning("Time range not provided for metric collection.")
            return {}
            
        start_ts = int(time_range[0].timestamp())
        end_ts = int(time_range[1].timestamp())
        step = 60 # Default step (e.g., 1 minute)

        for metric_name in metrics_to_collect:
            try:
                # Query metrics for control variant
                control_query = self._build_prometheus_query(metric_name, experiment_name, "control")
                control_data_raw = await self._query_prometheus(control_query, start_ts, end_ts, step)
                control_summary = self._summarize_metric(control_data_raw)

                # Query metrics for treatment variant(s) - assuming one treatment for now
                # TODO: Extend to handle multiple treatment variants if needed
                treatment_query = self._build_prometheus_query(metric_name, experiment_name, "treatment")
                treatment_data_raw = await self._query_prometheus(treatment_query, start_ts, end_ts, step)
                treatment_summary = self._summarize_metric(treatment_data_raw)

                collected_data[metric_name] = {
                    "control": control_summary,
                    "treatment": treatment_summary
                }
                logger.debug(f"Collected metric '{metric_name}': control={control_summary}, treatment={treatment_summary}")
            except Exception as e:
                logger.error(f"Failed to collect or process metric '{metric_name}' for experiment '{experiment_name}': {e}", exc_info=True)
                # Optionally store partial results or mark metric as failed
                collected_data[metric_name] = {"control": {"error": str(e)}, "treatment": {"error": str(e)}}
                
        return collected_data
        
    def _build_prometheus_query(self, metric_name: str, experiment_name: str, variant_name: str) -> str:
        """Build a Prometheus query string for a given metric, experiment, and variant."""
        # Example query - adjust based on actual metric labels used
        # Assumes metrics have labels 'experiment_name' and 'variant'
        # Example: f'avg_over_time({metric_name}{{experiment_name="{experiment_name}", variant="{variant_name}"}}[5m])'
        # This is a placeholder - the actual query depends heavily on how metrics are exported
        query = f'{metric_name}{{experiment_name="{experiment_name}", variant="{variant_name}"}}'
        logger.debug(f"Built Prometheus query: {query}")
        return query

    async def _query_prometheus(self, query: str, start: int, end: int, step: int) -> Optional[Dict]:
        """Query the Prometheus range query API."""
        if not self.metrics_endpoint:
            logger.error("Prometheus metrics endpoint is not configured.")
            return None
            
        api_url = f"{self.metrics_endpoint}/api/v1/query_range"
        params = {
            'query': query,
            'start': start,
            'end': end,
            'step': step
        }
        try:
            response = await self.client.get(api_url, params=params)
            response.raise_for_status() # Raise HTTP errors
            data = response.json()
            if data.get('status') == 'success':
                return data.get('data', {}).get('result')
            else:
                logger.error(f"Prometheus query failed: Status={data.get('status')}, Error={data.get('error')}")
                return None
        except httpx.RequestError as e:
            logger.error(f"HTTP error querying Prometheus: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error processing Prometheus response: {e}", exc_info=True)
            return None

    def _summarize_metric(self, prom_result: Optional[List[Dict]]) -> Dict[str, Any]:
        """Summarize Prometheus range query result with statistical measures."""
        summary = {"count": 0, "mean": None, "median": None, "p95": None, "min": None, "max": None}
        if not prom_result or not isinstance(prom_result, list):
            logger.debug("No valid data received from Prometheus for summarization.")
            return summary

        all_values = []
        for series in prom_result:
            values = series.get('values')
            if values and isinstance(values, list):
                # Extract numeric values (second element of each pair [timestamp, value])
                numeric_values = [float(v[1]) for v in values if v[1] is not None]
                all_values.extend(numeric_values)

        if not all_values:
            logger.debug("No numeric values found in Prometheus result.")
            return summary

        try:
            summary["count"] = len(all_values)
            summary["mean"] = np.mean(all_values) if all_values else None
            summary["median"] = np.median(all_values) if all_values else None
            summary["p95"] = np.percentile(all_values, 95) if all_values else None
            summary["min"] = np.min(all_values) if all_values else None
            summary["max"] = np.max(all_values) if all_values else None
            logger.debug(f"Summarized metrics: {summary}")
        except Exception as e:
            logger.error(f"Error summarizing metrics: {e}", exc_info=True)
            summary["error"] = str(e)

        return summary

# Example usage (dependency injection pattern)
# settings = get_settings()
# metrics_service = ExperimentMetricsService(metrics_endpoint=settings.METRICS_API_ENDPOINT)
# def get_metrics_service():
#    return metrics_service 