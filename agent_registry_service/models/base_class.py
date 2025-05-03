from typing import Any

from sqlalchemy.orm import as_declarative, declared_attr

@as_declarative()
class Base:
    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        # Converts CamelCase class name to snake_case table name
        import re
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        # Make plural (simple version, may need adjustment for irregular plurals)
        if name.endswith('s'):
             return name + 'es' # e.g., Status -> statuses
        elif name.endswith('y'):
             return name[:-1] + 'ies' # e.g., Category -> categories
        else:
             return name + 's' # e.g., Agent -> agents 