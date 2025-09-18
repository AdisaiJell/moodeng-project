
from typing import Optional
from pydantic import BaseModel

#ข้อมูลที่จะรับมาจากหน้าบ้าน
class WikiCreate(BaseModel):
    pass

#ข้อมูลที่จะส่งไปหน้าบ้าน
class WikiResponse(BaseModel):
    wikiId: int
    title: str
    summary: str
    content: str
    class Config:
        from_attributes = True


class WikiSchema(BaseModel):
    title: str
    summary: str
    content: str  
    
class WikiUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    
class WikiOut(BaseModel):
    wikiId: int
    title: str
    summary: str | None = None
    content: str | None = None

    class Config:
        from_attributes = True 


