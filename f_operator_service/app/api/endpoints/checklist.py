from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import Optional, List

from f_operator_service.db.session import get_db
from f_operator_service.models.checklist import ChecklistTemplate, ChecklistCriteria, TemplateStatus
from f_operator_service.schemas.checklist import (
    ChecklistTemplateCreate,
    ChecklistTemplateUpdate,
    ChecklistTemplateResponse,
    ChecklistTemplateListResponse,
    ChecklistCriteriaCreate,
    ChecklistCriteriaUpdate,
    ChecklistCriteriaResponse
)
from f_operator_service.app.services.provenance_service import get_provenance_service
from f_operator_service.schemas.provenance import ProvenanceRecordCreate
from f_operator_service.app.security.deps import get_current_active_user, check_permission
from f_operator_service.schemas.user import User

router = APIRouter()

@router.post("/templates", 
    response_model=ChecklistTemplateResponse, 
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_permission("templates:create"))]
)
async def create_checklist_template(
    template: ChecklistTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new checklist template with its criteria.
    Requires 'templates:create' permission.
    """
    try:
        # Create template
        db_template = ChecklistTemplate(
            name=template.name,
            description=template.description,
            target_level=template.target_level,
            version=template.version,
            status=template.status,
            created_by=current_user.id,
        )
        db.add(db_template)
        await db.flush()  # Get template.id before creating criteria

        # Create criteria
        for idx, criteria in enumerate(template.criteria):
            db_criteria = ChecklistCriteria(
                template_id=db_template.id,
                title=criteria.title,
                description=criteria.description,
                criteria_type=criteria.criteria_type,
                order=criteria.order or idx,  # Use provided order or index as fallback
                evidence_required=criteria.evidence_required
            )
            db.add(db_criteria)

        await db.commit()
        await db.refresh(db_template)

        # Load criteria for response
        await db.refresh(db_template, ["criteria"])

        # Log provenance
        provenance_service = get_provenance_service()
        try:
            prov_record = ProvenanceRecordCreate(
                entity_id=db_template.id,
                operation_type="checklist_template_created",
                operation_id=db_template.id,
                user_id=current_user.id,
                parameters=template.model_dump(),
                outcome_status="success"
            )
            await provenance_service.create_provenance_record(db, prov_record)
        except Exception as prov_err:
            import logging
            logging.getLogger(__name__).error(f"Failed to log provenance for template creation: {prov_err}")

        return db_template

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create template: {e}")

@router.get("/templates", 
    response_model=ChecklistTemplateListResponse,
    dependencies=[Depends(check_permission("templates:read"))]
)
async def list_checklist_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[TemplateStatus] = None,
    target_level: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List checklist templates with optional filtering and pagination.
    Requires 'templates:read' permission.
    """
    try:
        # Build query
        query = select(ChecklistTemplate).options(selectinload(ChecklistTemplate.criteria))
        
        # Apply filters
        if status:
            query = query.where(ChecklistTemplate.status == status)
        if target_level:
            query = query.where(ChecklistTemplate.target_level == target_level)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)

        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        templates = result.scalars().all()

        return ChecklistTemplateListResponse(
            templates=list(templates),
            total=total or 0
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {e}")

@router.get("/templates/{template_id}", 
    response_model=ChecklistTemplateResponse,
    dependencies=[Depends(check_permission("templates:read"))]
)
async def get_checklist_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific checklist template by ID.
    Requires 'templates:read' permission.
    """
    template = await db.get(ChecklistTemplate, template_id, options=[selectinload(ChecklistTemplate.criteria)])
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.patch("/templates/{template_id}", 
    response_model=ChecklistTemplateResponse,
    dependencies=[Depends(check_permission("templates:update"))]
)
async def update_checklist_template(
    template_id: UUID,
    template_update: ChecklistTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a checklist template's metadata.
    Requires 'templates:update' permission.
    """
    try:
        template = await db.get(ChecklistTemplate, template_id, options=[selectinload(ChecklistTemplate.criteria)])
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Update fields if provided
        update_data = template_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(template, field, value)

        # Special handling for status changes
        if template_update.status == TemplateStatus.ARCHIVED and not template.archived_at:
            template.archived_at = datetime.utcnow()
        elif template_update.status != TemplateStatus.ARCHIVED and template.archived_at:
            template.archived_at = None

        await db.commit()
        await db.refresh(template)

        # Log provenance
        provenance_service = get_provenance_service()
        try:
            prov_record = ProvenanceRecordCreate(
                entity_id=template.id,
                operation_type="checklist_template_updated",
                operation_id=template.id,
                user_id=current_user.id,
                parameters=update_data,
                outcome_status="success"
            )
            await provenance_service.create_provenance_record(db, prov_record)
        except Exception as prov_err:
            import logging
            logging.getLogger(__name__).error(f"Failed to log provenance for template update: {prov_err}")

        return template

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update template: {e}")

@router.post("/templates/{template_id}/criteria", 
    response_model=ChecklistCriteriaResponse,
    dependencies=[Depends(check_permission("criteria:create"))]
)
async def add_template_criteria(
    template_id: UUID,
    criteria: ChecklistCriteriaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Add a new criteria to an existing template.
    Requires 'criteria:create' permission.
    """
    try:
        template = await db.get(ChecklistTemplate, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Get max order to append new criteria
        result = await db.execute(
            select(func.max(ChecklistCriteria.order))
            .where(ChecklistCriteria.template_id == template_id)
        )
        max_order = result.scalar() or -1

        # Create new criteria
        db_criteria = ChecklistCriteria(
            template_id=template_id,
            title=criteria.title,
            description=criteria.description,
            criteria_type=criteria.criteria_type,
            order=criteria.order or max_order + 1,
            evidence_required=criteria.evidence_required
        )
        db.add(db_criteria)
        await db.commit()
        await db.refresh(db_criteria)

        # Log provenance
        provenance_service = get_provenance_service()
        try:
            prov_record = ProvenanceRecordCreate(
                entity_id=template_id,
                operation_type="checklist_criteria_added",
                operation_id=db_criteria.id,
                user_id=current_user.id,
                parameters=criteria.model_dump(),
                outcome_status="success"
            )
            await provenance_service.create_provenance_record(db, prov_record)
        except Exception as prov_err:
            import logging
            logging.getLogger(__name__).error(f"Failed to log provenance for criteria addition: {prov_err}")

        return db_criteria

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add criteria: {e}")

@router.patch("/templates/{template_id}/criteria/{criteria_id}", 
    response_model=ChecklistCriteriaResponse,
    dependencies=[Depends(check_permission("criteria:update"))]
)
async def update_template_criteria(
    template_id: UUID,
    criteria_id: UUID,
    criteria_update: ChecklistCriteriaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an existing criteria in a template.
    Requires 'criteria:update' permission.
    """
    try:
        # Get criteria and verify template ownership
        criteria = await db.get(ChecklistCriteria, criteria_id)
        if not criteria or criteria.template_id != template_id:
            raise HTTPException(status_code=404, detail="Criteria not found in template")

        # Update fields if provided
        update_data = criteria_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(criteria, field, value)

        await db.commit()
        await db.refresh(criteria)

        # Log provenance
        provenance_service = get_provenance_service()
        try:
            prov_record = ProvenanceRecordCreate(
                entity_id=template_id,
                operation_type="checklist_criteria_updated",
                operation_id=criteria_id,
                user_id=current_user.id,
                parameters=update_data,
                outcome_status="success"
            )
            await provenance_service.create_provenance_record(db, prov_record)
        except Exception as prov_err:
            import logging
            logging.getLogger(__name__).error(f"Failed to log provenance for criteria update: {prov_err}")

        return criteria

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update criteria: {e}")

@router.delete("/templates/{template_id}/criteria/{criteria_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(check_permission("criteria:delete"))]
)
async def delete_template_criteria(
    template_id: UUID,
    criteria_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a criteria from a template.
    Requires 'criteria:delete' permission.
    """
    try:
        criteria = await db.get(ChecklistCriteria, criteria_id)
        if not criteria or criteria.template_id != template_id:
            raise HTTPException(status_code=404, detail="Criteria not found in template")

        await db.delete(criteria)
        await db.commit()

        # Log provenance
        provenance_service = get_provenance_service()
        try:
            prov_record = ProvenanceRecordCreate(
                entity_id=template_id,
                operation_type="checklist_criteria_deleted",
                operation_id=criteria_id,
                user_id=current_user.id,
                parameters={"criteria_id": str(criteria_id)},
                outcome_status="success"
            )
            await provenance_service.create_provenance_record(db, prov_record)
        except Exception as prov_err:
            import logging
            logging.getLogger(__name__).error(f"Failed to log provenance for criteria deletion: {prov_err}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete criteria: {e}")

@router.post("/templates/{template_id}/version", 
    response_model=ChecklistTemplateResponse,
    dependencies=[Depends(check_permission("templates:create"))]
)
async def create_template_version(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new version of an existing template.
    Requires 'templates:create' permission.
    """
    try:
        # Get existing template with criteria
        template = await db.get(ChecklistTemplate, template_id, options=[selectinload(ChecklistTemplate.criteria)])
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Create new template version
        new_template = ChecklistTemplate(
            name=template.name,
            description=template.description,
            target_level=template.target_level,
            version=template.version + 1,
            status=TemplateStatus.DRAFT,
            created_by=current_user.id,
        )
        db.add(new_template)
        await db.flush()

        # Copy criteria to new version
        for criteria in template.criteria:
            new_criteria = ChecklistCriteria(
                template_id=new_template.id,
                title=criteria.title,
                description=criteria.description,
                criteria_type=criteria.criteria_type,
                order=criteria.order,
                evidence_required=criteria.evidence_required
            )
            db.add(new_criteria)

        await db.commit()
        await db.refresh(new_template, ["criteria"])

        # Log provenance
        provenance_service = get_provenance_service()
        try:
            prov_record = ProvenanceRecordCreate(
                entity_id=new_template.id,
                operation_type="checklist_template_versioned",
                operation_id=new_template.id,
                user_id=current_user.id,
                parameters={"source_template_id": str(template_id)},
                outcome_status="success"
            )
            await provenance_service.create_provenance_record(db, prov_record)
        except Exception as prov_err:
            import logging
            logging.getLogger(__name__).error(f"Failed to log provenance for template versioning: {prov_err}")

        return new_template

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create template version: {e}") 