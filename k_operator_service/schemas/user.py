from pydantic import BaseModel
from typing import List

# Placeholder User model for type hinting and dependency checks
# Assumes the actual user data and permissions are fetched/verified elsewhere
class User(BaseModel):
    id: str
    is_active: bool = True
    permissions: List[str] = [] 