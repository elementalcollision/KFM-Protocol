import logging
from typing import Optional, List
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from f_operator_service.models.provenance import ProvenanceRecord
from f_operator_service.schemas.provenance import ProvenanceRecordCreate, ProvenanceRecord as ProvenanceRecordSchema
from uuid import UUID

logger = logging.getLogger(__name__)

class ProvenanceService:
    def __init__(self):
        pass

    async def create_provenance_record(self, db: AsyncSession, record_in: ProvenanceRecordCreate) -> Optional[ProvenanceRecordSchema]:
        try:
            db_obj = ProvenanceRecord(**record_in.model_dump())
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return ProvenanceRecordSchema.model_validate(db_obj)
        except SQLAlchemyError as e:
            logger.error(f"Failed to create provenance record: {e}")
            await db.rollback()
            return None
        except Exception as e:
            logger.error(f"Unexpected error in provenance logging: {e}")
            await db.rollback()
            return None

    async def get_provenance_records_by_entity(self, db: AsyncSession, entity_id: UUID) -> List[ProvenanceRecordSchema]:
        try:
            result = await db.execute(
                ProvenanceRecord.__table__.select().where(ProvenanceRecord.entity_id == entity_id)
            )
            records = result.fetchall()
            return [ProvenanceRecordSchema.model_validate(dict(r)) for r in records]
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch provenance records: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in fetching provenance records: {e}")
            return []

@lru_cache(maxsize=None)
def get_provenance_service() -> ProvenanceService:
    return ProvenanceService() 