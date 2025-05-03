from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, desc, asc
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Tuple, Any, Dict
from f_operator_service.models.experiment import Experiment, ExperimentStatusEnum
from f_operator_service.schemas.experiment import ExperimentCreate, ExperimentUpdate
import logging
from datetime import datetime
import sqlalchemy as sa

logger = logging.getLogger(__name__)

class ExperimentCRUD:
    async def get(self, db: AsyncSession, experiment_id: int) -> Optional[Experiment]:
        try:
            result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching experiment by id: {e}")
            return None

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[Experiment]:
        try:
            result = await db.execute(select(Experiment).where(Experiment.name == name))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching experiment by name: {e}")
            return None

    async def list(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Experiment]:
        try:
            result = await db.execute(select(Experiment).offset(skip).limit(limit))
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error listing experiments: {e}")
            return []

    async def create(self, db: AsyncSession, obj_in: ExperimentCreate) -> Optional[Experiment]:
        try:
            db_obj = Experiment(**obj_in.dict())
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Error creating experiment: {e}")
            return None

    async def update(self, db: AsyncSession, db_obj: Experiment, obj_in: ExperimentUpdate) -> Optional[Experiment]:
        try:
            update_data = obj_in.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_obj, field, value)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Error updating experiment: {e}")
            return None

    async def delete(self, db: AsyncSession, experiment_id: int) -> bool:
        try:
            result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
            db_obj = result.scalar_one_or_none()
            if db_obj is None:
                return False
            await db.delete(db_obj)
            await db.commit()
            return True
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Error deleting experiment: {e}")
            return False

    async def get_experiments(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100, 
        status: Optional[ExperimentStatusEnum] = None,
        sort_by: str = 'created_at',
        sort_desc: bool = True
    ) -> Tuple[List[Experiment], int]:
        """Get multiple experiments with filtering, sorting, and pagination."""
        query = select(Experiment)
        
        if status:
            query = query.filter(Experiment.status == status)
        
        # Get total count before pagination/sorting
        total_query = select(sa.func.count()).select_from(query.subquery())
        total_result = await db.execute(total_query)
        total = total_result.scalar_one()

        # Apply sorting
        sort_column = getattr(Experiment, sort_by, Experiment.created_at)
        if sort_desc:
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        experiments = result.scalars().all()
        return experiments, total

    async def update_experiment_status(
        self,
        db: AsyncSession, *, db_obj: Experiment, new_status: ExperimentStatusEnum, status_data: Optional[Dict] = None
    ) -> Experiment:
        """Update only the status of an experiment, optionally setting date fields."""
        db_obj.status = new_status
        now = datetime.utcnow()
        db_obj.updated_at = now
        
        if new_status == ExperimentStatusEnum.RUNNING and not db_obj.start_date:
            db_obj.start_date = now
        elif new_status in [ExperimentStatusEnum.COMPLETED, ExperimentStatusEnum.CANCELLED] and not db_obj.end_date:
            db_obj.end_date = now
            if status_data:
                db_obj.results = status_data.get('results')
                db_obj.conclusion = status_data.get('conclusion')
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

experiment_crud = ExperimentCRUD() 