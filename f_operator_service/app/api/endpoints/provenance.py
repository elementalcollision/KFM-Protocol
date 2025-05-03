from fastapi import APIRouter, Depends, Query
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from f_operator_service.db.session import get_db
from f_operator_service.app.services.provenance_service import get_provenance_service
from f_operator_service.schemas.provenance import ProvenanceRecord

router = APIRouter()

@router.get("/", response_model=List[ProvenanceRecord])
async def get_provenance_records(
    entity_id: UUID = Query(..., description="The entity ID to filter provenance records by"),
    db: AsyncSession = Depends(get_db)
) -> List[ProvenanceRecord]:
    provenance_service = get_provenance_service()
    records = await provenance_service.get_provenance_records_by_entity(db, entity_id)
    return records 