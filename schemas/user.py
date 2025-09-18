from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    userName: str
    email: Optional[str]
    roleId: Optional[int] = None
    factId: Optional[int] = None

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    userId: int
    userName: str
    email: Optional[str]
    roleId: Optional[int] = None
    factId: Optional[int] = None

class UserOut(UserBase):
    userId: int
    image: Optional[str] = None 
    model_config = {
        "from_attributes": True
    }

