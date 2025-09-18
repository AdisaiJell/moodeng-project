from pydantic import BaseModel
from typing import Optional


class RoleBase(BaseModel):
    roleName: str

class RoleCreate(RoleBase):
    roleId: Optional[int] = None

class RoleUpdate(RoleBase):
    pass

class RoleOut(RoleBase):
    roleId: int

    model_config = {
        "from_attributes": True
    }

