from typing import Optional
from pydantic import BaseModel
from fastapi import UploadFile, File
from schemas.meta import MetaSchema

#ข้อมูลที่จะรับมาจากหน้าบ้าน
class DocumentCreate(BaseModel):
    pass

#ข้อมูลที่จะส่งไปหน้าบ้าน
class DocumentResponse(BaseModel):
    pass


class DocumentSchema(BaseModel):
    docName: str
    meta: MetaSchema
    ocrText: str
    status: bool
    file: Optional[bytes]  # ใช้เก็บข้อมูลไฟล์ไบนารี