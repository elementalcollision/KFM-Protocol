from enum import Enum

class PromotionStatus(str, Enum):
    INITIATED = "INITIATED"
    CHECKLIST_PENDING = "CHECKLIST_PENDING"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

# --- Maintenance Enums ---
class ReviewStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"

class ReviewType(str, Enum):
    PERIODIC = "PERIODIC"
    ADHOC = "ADHOC"
    # Add more specific types if needed, e.g.:
    # SECURITY = "SECURITY"
    # PERFORMANCE = "PERFORMANCE"

class ReviewOutcome(str, Enum):
    PASSED = "PASSED"
    PASSED_WITH_CONDITIONS = "PASSED_WITH_CONDITIONS"
    FAILED = "FAILED"
    # Potential outcomes leading to state change:
    RECOMMEND_DEPRECATION = "RECOMMEND_DEPRECATION" 