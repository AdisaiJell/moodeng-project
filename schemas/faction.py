from pydantic import BaseModel
from typing import Optional

#ข้อมูลที่จะรับมาจากหน้าบ้าน
class FactionCreate(BaseModel): 
    factId: Optional[int] = None
    factionName: str

#ข้อมูลที่จะส่งไปหน้าบ้าน
class FactionResponse(BaseModel):
    pass

class FactionUpdate(FactionCreate):
    pass

class FactionOut(FactionCreate):
    factId: int

    model_config = {
        "from_attributes": True
    }
