from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from f_operator_service.schemas.feature_flag import FeatureFlag
from f_operator_service.app.services.feature_flag_service import get_feature_flag_service

router = APIRouter()

@router.get("/feature-flags", response_model=List[FeatureFlag], tags=["Feature Flags"])
def list_feature_flags():
    service = get_feature_flag_service()
    return service.get_all_flags()

@router.get("/feature-flags/{flag_name}", response_model=FeatureFlag, tags=["Feature Flags"])
def get_feature_flag(flag_name: str):
    service = get_feature_flag_service()
    flag = service.get_flag(flag_name)
    if not flag:
        raise HTTPException(status_code=404, detail=f"Feature flag '{flag_name}' not found.")
    return flag

@router.get("/feature-flags/{flag_name}/active", response_model=bool, tags=["Feature Flags"])
def is_feature_flag_active(
    flag_name: str,
    agent_id: Optional[str] = Query(None, description="Agent ID for targeting rules"),
    environment: Optional[str] = Query(None, description="Environment for environment rules")
):
    service = get_feature_flag_service()
    context = {}
    if agent_id:
        context["agent_id"] = agent_id
    if environment:
        context["environment"] = environment
    return service.is_flag_active(flag_name, context) 