from pydantic import BaseModel
from typing import Optional

#ข้อมูลที่จะรับมาจากหน้าบ้าน
class TypeCreate(BaseModel):
    typeId: Optional[int] = None
    typeName:str

#ข้อมูลที่จะส่งไปหน้าบ้าน
class TypeResponse(TypeCreate):
    pass

class TypeUpdate(TypeCreate):
    pass

class TypeOut(TypeCreate):
    typeId: int

    model_config = {
        "from_attributes": True
    }
