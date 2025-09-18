import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from controllers.wiki_controller import make_wiki_from_payload
from database import get_db
from controllers.document_controller import StatusUpdate, update_document_status, delete_document, download_document, get_all_documents, get_document_by_id, get_document_counts_by_year, get_documents_by_faction, save_doc, update_doc, soft_delete_doc, update_document
from controllers.ocr_controller import richtext_to_plaintext, process_ocr
from models.document import Document
from models.meta import Meta
from fastapi import Query
from models.wiki import Wiki


router = APIRouter(prefix="/document", tags=["Document"])

@router.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    print(f"Received file: {file.filename}")
    file_name = file.filename
    file_bytes = await file.read()
    try:
        task = process_ocr.delay(file_bytes, file_name)
        return {"task_id": task.id}
    except Exception as e:
        print(f"OCR endpoint error: {e}")
        return {"error": str(e)}

# @router.post("/create")
# async def create_document_api(document:documentCreate, db: Session = Depends(get_db)):
#     return create_document(db, document)

# @router.get("/")
# async def get_documents_api(db: Session = Depends(get_db)):
#     return get_all_documents(db)


@router.post("/save")
async def save_document(
    doc: str = Form(...),  # รับ JSON เป็น String
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # แปลง JSON String -> Dictionary
    doc_data = json.loads(doc, strict=False)
    
    ocrTextWithFormat = doc_data['ocrText']
    ocrText, ocrTextWithFormat = richtext_to_plaintext(ocrTextWithFormat) #ลบ tag html ออก ให้เหลือเเต่ข้อความธรรมดา
    
    doc_data.update({"ocrText": ocrText, "ocrTextWithFormat": ocrTextWithFormat})

   # wiki
    title, summary, content = make_wiki_from_payload(
        doc_name=doc_data.get("docName", ""),
        meta=doc_data.get("meta", {}) or {},
        ocr_text=ocrText,
    )
    wiki = Wiki(title=title, summary=summary, content=content)
    db.add(wiki)
    db.flush()            

    # 3) save document 
    new_doc = save_doc(db, doc_data, file, wiki_id=wiki.wikiId)

    # 4) commit ครั้งเดียว
    db.commit()

    # 5) refresh objects
    db.refresh(wiki)
    db.refresh(new_doc)

    return {"message": "Document saved successfully", "doc_id": new_doc.docId,
            "wiki": {
                "wikiId": wiki.wikiId,
                "title": wiki.title,
                "summary": wiki.summary,
                "content": wiki.content,
            }}

@router.get("/download/{doc_id}")
async def download_document_api(doc_id: int, db: Session = Depends(get_db)):
    return download_document(db, doc_id)


#-------------------------------------------------------------------------------------------------
@router.get("/all")
async def fetch_all_documents(db: Session = Depends(get_db)):
    return get_all_documents(db)


@router.get("/faction/{faction_name}")
async def fetch_documents_by_faction(faction_name: str, db: Session = Depends(get_db)):
    return get_documents_by_faction(db, faction_name)

@router.get("/getById/{doc_id}", summary="Get document by ID")
async def get_document(doc_id: int, db: Session = Depends(get_db)):
    return get_document_by_id(db, doc_id)
    """
    ดึงข้อมูลเอกสารตาม doc_id พร้อมข้อมูล meta
    """
    doc = (
        db.query(Document)
        .join(Meta, Document.metaId == Meta.metaId)
        .filter(Document.docId == doc_id)
        .first()
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    result = {
        "docId": doc.docId,
        "docName": doc.docName,
        "meta": {
            "factionName": doc.meta.factionName if doc.meta else "",
            "typeName": doc.meta.typeName if doc.meta else "",
            "publishDate": str(doc.meta.publishedDate) if doc.meta and doc.meta.publishedDate else "",
            "effectiveDate": str(doc.meta.effectiveDate) if doc.meta and doc.meta.effectiveDate else "",
            "keyword": doc.meta.keyword if doc.meta else [],
            "relateDoc": doc.meta.relateddoc if doc.meta else []
        },
        "ocrText": doc.ocrText,
        "status": doc.status,
        "files": [f"/document/download/{doc.docId}"]  # ลิงก์ดาวน์โหลดไฟล์
    }

    return result


@router.get("/summary/counts")
async def document_counts(
    year: int = Query(..., description="ระบุปี พ.ศ."),
    faction_name: str = Query("ทุกฝ่าย", description="ชื่อฝ่าย หรือ 'ทุกฝ่าย'"),
    db: Session = Depends(get_db)
):
    return get_document_counts_by_year(db, year, faction_name)


#-----update-------------------------------------------------------
@router.put("/update/{doc_id}")
async def update_document_api(
    doc_id: int,
    doc: str = Form(...),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    try:
        doc_data = json.loads(doc)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in 'doc' field")

    return update_document(db, doc_id, doc_data, file)


@router.delete("/delete/{doc_id}", summary="Soft delete a document")
async def delete_document_api(
    doc_id: int,
    db: Session = Depends(get_db)
):
    return delete_document(db, doc_id)

@router.put("/status/{doc_id}", summary="Update document status (True/False)")
async def update_document_status_api(
    doc_id: int, 
    body: StatusUpdate, # Use the imported StatusUpdate model
    db: Session = Depends(get_db)
):
    """
    Changes the status of a document (e.g., enable/disable).
    """
    # Delegate the status update logic to the controller
    updated_doc = update_document_status(db, doc_id, body.status)
    return {
        "message": f"Document status updated to {updated_doc.status}",
        "doc_id": updated_doc.docId,
        "status": updated_doc.status
    }