from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from controllers.meta_controller import extract_metadata,  save_metadata_to_db
from schemas.meta import OCRTextRequest


router = APIRouter(prefix="/metadata", tags=["Metadata"])


@router.post("/extract")
async def extract_metadata_api(request: OCRTextRequest, db: Session = Depends(get_db)):
    meta_data = extract_metadata(request.ocrText, db)
    return meta_data

# บันทึก Metadata ที่แก้ไขแล้ว
@router.post("/save")
async def save_metadata_api(meta_data: dict, db: Session = Depends(get_db)):
    saved_meta = save_metadata_to_db(db, meta_data)
    return {"metaId": saved_meta.metaId, "message": "Metadata saved successfully"}
