import io
import os
import subprocess
import sys
import tempfile
import img2pdf

from urllib.parse import quote
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from controllers.wiki_controller import make_wiki_from_payload
from models.document import Document
from models.faction import Faction
from models.meta import Meta
from models.type import Type
from controllers.ocr_controller import richtext_to_plaintext
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from pathlib import Path


from models.wiki import Wiki


TEMP_FOLDER = "file/"
os.makedirs(TEMP_FOLDER, exist_ok=True)

try:
    from docx2pdf import convert as docx_to_pdf  # type: ignore
except Exception:
    docx_to_pdf = None

def convert_to_pdf(file: UploadFile) -> bytes:
    """
    แปลง DOCX/PNG/JPG/JPEG/PDF เป็น PDF แล้วคืนค่าเป็น bytes
    - DOCX: Windows/Mac ใช้ docx2pdf; Linux/Container ใช้ libreoffice --headless
    - รูปภาพ: ใช้ img2pdf
    - PDF: ส่งผ่าน (pass-through)
    """
    # เผื่อบางกรณีไม่มีชื่อไฟล์
    filename = file.filename or "upload.bin"
    ext = Path(filename).suffix.lower().lstrip(".")

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        in_path = td_path / f"in.{ext if ext else 'bin'}"
        out_path = td_path / "out.pdf"

        # อ่านเนื้อไฟล์จาก UploadFile (pointer ของ FastAPI)
        in_path.write_bytes(file.file.read())

        if ext == "docx":
            # 1) ถ้าใช้ได้ ให้ใช้ docx2pdf (ดีบน Windows/Mac)
            if docx_to_pdf is not None and sys.platform in ("win32", "darwin"):
                # บางเวอร์ชัน docx2pdf ต้องชี้โฟลเดอร์ output
                docx_to_pdf(str(in_path), str(td_path))
            else:
                # 2) Linux/container → ใช้ LibreOffice
                cmd = [
                    "libreoffice", "--headless",
                    "--convert-to", "pdf",
                    "--outdir", str(td_path),
                    str(in_path),
                ]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if res.returncode != 0:
                    raise RuntimeError(
                        f"LibreOffice convert failed: {res.stderr.decode('utf-8', 'ignore')}"
                    )

            # หาไฟล์ PDF ที่ได้ (docx2pdf/LO ตั้งชื่อจากต้นฉบับ)
            pdf_files = list(td_path.glob("*.pdf"))
            if not pdf_files:
                raise RuntimeError("PDF not generated from DOCX.")
            return pdf_files[0].read_bytes()

        elif ext in {"png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp"}:
            # img2pdf รองรับ path หรือ bytes ก็ได้
            out_path.write_bytes(img2pdf.convert(str(in_path)))
            return out_path.read_bytes()

        elif ext == "pdf":
            # ส่งผ่าน
            return in_path.read_bytes()

        else:
            raise ValueError("Unsupported file type. Only DOCX, images, and PDF are allowed.")



def save_doc(db: Session, doc_data: dict, file: UploadFile, wiki_id: int):
    file_data = convert_to_pdf(file)

    # Extract faction name and type name from either str or dict
    faction_raw = doc_data["meta"]["factionName"]
    type_raw = doc_data["meta"]["typeName"]
    faction_name = faction_raw["value"] if isinstance(faction_raw, dict) else faction_raw
    type_name = type_raw["value"] if isinstance(type_raw, dict) else type_raw

    # ดึงหรือสร้าง factionId และ typeId
    factid = get_or_create_faction(db, faction_name)
    typeid = get_type_id(db, type_name)
    if typeid is None:
        raise ValueError(f"Type '{type_name}' not found.")

    new_meta = Meta(
        factId=factid,
        typeId=typeid,
        factionName=faction_name,
        typeName=type_name,
        publishedDate=doc_data["meta"]["publishDate"],
        effectiveDate=doc_data["meta"]["effectiveDate"],
        keyword=doc_data["meta"]["keyword"],
        relateddoc=doc_data["meta"]["relateDoc"]
    )
    db.add(new_meta)
    db.commit()
    db.refresh(new_meta)


    # บันทึก Document พร้อม Metadata
    new_doc = Document(
        docName=doc_data["docName"],
        metaId=new_meta.metaId,
        ocrText=doc_data["ocrText"],
        ocrTextWithFormat=doc_data['ocrTextWithFormat'],
        status=True,
        file=file_data,  # เก็บไฟล์เป็นไบนารี
        wikiId=wiki_id
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    return new_doc

def get_or_create_faction(db: Session, faction_name: str):
    """ ค้นหา factid จาก factionname ถ้าไม่เจอให้สร้างใหม่ """
    faction = db.query(Faction).filter(Faction.factionName == faction_name).first()
    if not faction:
        faction = Faction(factionName=faction_name)
        db.add(faction)
        db.commit()
        db.refresh(faction)
    return faction.factId


def get_type_id(db: Session, type_name: str):
    """ ดึง typeid จาก typename """
    type_obj = db.query(Type).filter(Type.typeName == type_name).first()
    return type_obj.typeId if type_obj else None

#update doc-----------------------------------------------------------------------------------
def update_doc(db: Session, doc_id: int, doc_data: dict, file: UploadFile | None = None):
  
    
    """
    อัพเดตทั้ง Metadata และ Document
    - ถ้ามี field ใน meta ให้ไปอัพเดตในตาราง meta
    - ถ้ามีไฟล์ใหม่ ส่งมาให้แปลงเป็น PDF แล้วอัพเดต Document.file
    """
    # 1) ดึง Document เดิม
    db_doc = db.query(Document).filter(Document.docId == doc_id).first()
    if not db_doc:
        raise ValueError(f"Document with id={doc_id} not found")

    ocr_updated = False

    # 2) อัพเดตชื่อเอกสาร และ OCR text ถ้ามี
    if "docName" in doc_data:
        db_doc.docName = doc_data["docName"]
    # if "ocrText" in doc_data:
    #     ocr_text, ocr_text_with_format = richtext_to_plaintext(doc_data['ocrText'])
    #     db_doc.ocrTextWithFormat = ocr_text_with_format
    #     db_doc.ocrText = ocr_text

    if "ocrText" in doc_data:
        new_ocr_plain, new_ocr_with_format = richtext_to_plaintext(doc_data["ocrText"])

        old_plain = db_doc.ocrText or ""
        if (new_ocr_plain or "") != old_plain:
            ocr_updated = True
            db_doc.ocrText = new_ocr_plain
            db_doc.ocrTextWithFormat = new_ocr_with_format

    # 3) ถ้ามีไฟล์ใหม่ ให้แปลงเป็น PDF แล้วอัพเดต
    if file:
        pdf_bytes = convert_to_pdf(file)
        db_doc.file = pdf_bytes

    # 4) อัพเดต Metadata (ถ้ามี)
    if "meta" in doc_data:
        meta_data = doc_data["meta"]
        db_meta = db.query(Meta).filter(Meta.metaId == db_doc.metaId).first()
        if db_meta:
            # ตัวอย่างอัพเดต field หลักๆ
            for key in ("factionName", "typeName", "publishedDate", "effectiveDate", "keyword", "relateddoc"):
                if key in meta_data:
                    setattr(db_meta, key, meta_data[key])


      # 5) ถ้า OCR เปลี่ยน → สร้างสรุปใหม่ แล้ว "อัปเดต wiki เดิม" หรือ "สร้าง wiki ใหม่"
    if ocr_updated:
        title, summary, content = make_wiki_from_payload(
            doc_name=db_doc.docName or "",
            meta=doc_data.get("meta", {}) or {},
            ocr_text=db_doc.ocrText or ""
        )

        wiki = db.query(Wiki).filter(Wiki.wikiId == db_doc.wikiId).first() if db_doc.wikiId else None

        if wiki:
            wiki.title = title
            wiki.summary = summary
            wiki.content = content
        else:
            wiki = Wiki(title=title, summary=summary, content=content)
            db.add(wiki)
            db.flush()              # ให้ได้ wikiId ก่อน commit
            db_doc.wikiId = wiki.wikiId



    # 5) Commit & Refresh
    db.commit()
    db.refresh(db_doc)
    
    return db_doc


#-------delete doc (change status)-------------------
def soft_delete_doc(db: Session, doc_id: int) -> Document:
    """
    Soft-delete document: แค่เปลี่ยน status เป็น False
    """
    db_doc = db.query(Document).filter(Document.docId == doc_id).first()
    if not db_doc:
        raise ValueError(f"Document with id={doc_id} not found")
    # เปลี่ยนสถานะ
    db_doc.status = False
    db.commit()
    db.refresh(db_doc)
    return db_doc

class StatusUpdate(BaseModel):
    """Pydantic model for updating document status."""
    status: bool

def update_document_status(db: Session, doc_id: int, new_status: bool) -> Document:
    """Toggles a document's status (True <-> False)."""
    doc_to_update = db.query(Document).filter(Document.docId == doc_id).first()
    if not doc_to_update:
        raise HTTPException(status_code=404, detail=f"Document with id={doc_id} not found")
    
    doc_to_update.status = new_status
    db.commit()
    db.refresh(doc_to_update)
    return doc_to_update

#-------------------------------------------------------------------------------------
def get_document_by_id(db: Session, doc_id: int):
    """
    ดึงเอกสารตาม doc_id
    """
    doc = (
        db.query(Document)
        .join(Meta, Document.metaId == Meta.metaId)
        .join(Wiki, Document.wikiId == Wiki.wikiId)
        .filter(Document.docId == doc_id)
        .first()
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "docId": doc.docId,
        "docName": doc.docName,
        "ocrTextWithFormat": doc.ocrTextWithFormat,
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
        "files": [f"/document/download/{doc.docId}"],
        "wiki": {
                "wikiId": doc.wiki.wikiId,
                "title": doc.wiki.title,
                "summary": doc.wiki.summary,
                "content": doc.wiki.content,
            }
    }

def get_document_counts_by_year(db: Session, year: int, faction_name: str):
    """
    ดึงจำนวนเอกสารแยกตามประเภท (ข้อบังคับ, ระเบียบ, ประกาศ) ของปีที่กำหนด
    - ถ้า faction_name เป็น 'ทุกฝ่าย' จะรวมทุกฝ่าย
    """
    query = (
        db.query(Meta.typeName, func.count().label("count"))
        .join(Document, Document.metaId == Meta.metaId)
        .filter(func.extract('year', Meta.publishedDate) == year)
        .group_by(Meta.typeName)
    )

    if faction_name != "ทุกฝ่าย":
        query = query.filter(Meta.factionName == faction_name)

    results = query.all()

    # ค่าเริ่มต้น
    count_map = {
        "ข้อบังคับ": 0,
        "ระเบียบ": 0,
        "ประกาศ": 0
    }

    for type_name, count in results:
        if type_name in count_map:
            count_map[type_name] = count

    return {
        "rule": count_map["ข้อบังคับ"],
        "regulation": count_map["ระเบียบ"],
        "announcement": count_map["ประกาศ"]
    }


def get_documents_by_faction(db: Session, faction_name: str):
    docs = (
        db.query(Document)
        .join(Meta, Document.metaId == Meta.metaId)
        .filter(Meta.factionName == faction_name)
        .all()
    )

    if not docs:
        raise HTTPException(status_code=404, detail="No documents found for this faction.")

    results = []
    for doc in docs:
        results.append({
            "docId": doc.docId,
            "docName": doc.docName,
            "ocrTextWithFormat": doc.ocrTextWithFormat,
            "meta": {
                "factionName": doc.meta.factionName,
                "typeName": doc.meta.typeName,
                "publishDate": str(doc.meta.publishedDate) if doc.meta and doc.meta.publishedDate else "",
                "effectiveDate": str(doc.meta.effectiveDate) if doc.meta and doc.meta.effectiveDate else "",
                "keyword": doc.meta.keyword,
                "relateDoc": doc.meta.relateddoc
            },
            "ocrText": doc.ocrText,
            "status": doc.status,
            "files": [f"/document/download/{doc.docId}"],
            "wiki":doc.wikiId
        })

    return results


def get_all_documents(db: Session):
    """
    ดึงเอกสารทั้งหมด โดย Join กับตาราง Meta
    """
    docs = db.query(Document).join(Meta, Document.metaId == Meta.metaId).all()
    results = []

    for doc in docs:
        results.append({
            "docId": doc.docId,
            "docName": doc.docName,
            "ocrTextWithFormat": doc.ocrTextWithFormat,
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
            "files": [f"/document/download/{doc.docId}"],
            "wiki":doc.wikiId
        })

    return results

def download_document(db: Session, doc_id: int):
    document = db.query(Document).filter(Document.docId == doc_id).first()

    if not document or not document.file:
        raise HTTPException(status_code=404, detail="Document not found")

    # ใช้ urllib.parse.quote และกำหนด safe=""
    safe_filename = quote(f"{document.docName}.pdf", safe="")

    return StreamingResponse(
        io.BytesIO(document.file),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"
        }
    )

def update_document(db: Session, doc_id: int, doc_data: dict, file: UploadFile | None):
    """
    อัพเดตเอกสาร:
    - รับข้อมูล doc_data (dict)
    - ถ้ามีไฟล์ใหม่ให้ทำการอัพเดต
    """
    try:
        updated = update_doc(db, doc_id, doc_data, file)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "message": "Document updated successfully",
        "doc_id": updated.docId
    }


def delete_document(db: Session, doc_id: int):
    """
    Soft delete เอกสาร: เปลี่ยน status เป็น False
    """
    try:
        deleted = soft_delete_doc(db, doc_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "message": "Document status set to false",
        "doc_id": deleted.docId,
        "status": deleted.status
    }