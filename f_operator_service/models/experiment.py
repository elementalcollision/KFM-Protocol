from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum as SQLEnum, Boolean
from sqlalchemy.sql import func
import enum

from f_operator_service.db.base import Base
# Remove schema import from model file to avoid potential circular dependency
# from f_operator_service.schemas.experiment import ExperimentBase 

class ExperimentStatusEnum(str, enum.Enum):
    DRAFT = "draft" # Added based on snippet
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled" # Added based on snippet
    # Removed ARCHIVED, PLANNING

class Experiment(Base):
    __tablename__ = "experiments" # Explicit table name based on snippet

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    feature_flag = Column(String, index=True, nullable=False) # Renamed from feature_flag_name, made non-nullable
    status = Column(SQLEnum(ExperimentStatusEnum), default=ExperimentStatusEnum.DRAFT, nullable=False)
    
    # Configuration (added based on snippet)
    variants = Column(JSON, nullable=False) # Schema: List[ExperimentVariant]
    success_criteria = Column(JSON, nullable=False) # Schema: List[SuccessCriterion]
    audience = Column(JSON, nullable=True) # Schema: Optional[ExperimentAudience]

    # Timing (renamed based on snippet)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Results (added based on snippet)
    results = Column(JSON, nullable=True) # Stores collected metrics & analysis
    conclusion = Column(String, nullable=True) # e.g., 'success', 'failure', 'inconclusive'

    # Removed fields not in snippet: parameters, metrics (replaced by more specific fields) 