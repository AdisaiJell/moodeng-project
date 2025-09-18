from datetime import date
from typing import List
from pydantic import BaseModel

#ข้อมูลที่จะรับมาจากหน้าบ้าน
class MetaCreate(BaseModel):
    pass

#ข้อมูลที่จะส่งไปหน้าบ้าน
class MetaResponse(BaseModel):
    pass


class MetaSchema(BaseModel):
    factionName: str
    typeName: str
    publishDate: date  
    effectiveDate: date  
    keyword: List[str]
    relateDoc: List[str]

class OCRTextRequest(BaseModel):
    ocrText: str
