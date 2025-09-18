import re
from fastapi import HTTPException
from sqlalchemy.orm import Session
import os, json, requests
from datetime import datetime
from typing import List
from collections import Counter

from models.document import Document
from models.wiki import Wiki
from schemas.wiki import WikiUpdate



OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "scb10x/llama3.1-typhoon2-8b-instruct")

# ---------- PROMPT ----------
SYS_PROMPT = """คุณคือผู้สรุปเอกสารราชการไทย/ระเบียบ/ประกาศ/ข้อบังคับ ให้เป็นหน้า wiki แบบสั้น กระชับ และครบประเด็น
ตอบเป็น JSON เท่านั้น โดยมีคีย์: title, summary, content (ห้ามมีคีย์อื่น และห้ามมี code block)

ข้อกำหนดรูปแบบ:
- ใช้เลขไทย (๐–๙) ทั้งหมด
- วันที่ให้แปลงเป็น พ.ศ. (คริสต์ศักราช + 543) และแสดงเป็น dd/mm/พ.ศ.
- ลบ Markdown/คราบ OCR (#, **, ###) ออก
- summary ≤ 2 บรรทัด; content เป็น bullet (ขึ้นต้นด้วย "• ") 6–10 บรรทัด
- หากมีข้อความ “ให้ใช้บังคับตั้งแต่วันถัดจากวันประกาศ” ให้คำนวณวันถัดไป

title: ใช้ชื่อจาก doc_name ถ้ามี มิฉะนั้นสกัดจากเนื้อหา
summary: ระบุผู้ออก/อำนาจตามกฎหมาย/สิ่งที่เปลี่ยนแปลง/วันประกาศและวันมีผลใช้บังคับ (รูปแบบ dd/mm/พ.ศ.)
content: bullet ครอบคลุม ขอบเขต/อำนาจ/สิ่งที่ยกเลิกหรือแก้ไข/สาระหลัก/ข้อย่อยที่สำคัญ/การรายงานหรือเส้นตาย/วันมีผลใช้บังคับ

ตัวอย่างเอาต์พุต:
{"title":"...", "summary":"...", "content":"• ...\n• ..."}"""

# ---------- TH digits / BE date helpers ----------
_TH_DIGITS = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")

def to_thai_digits(s: str) -> str:
    return s.translate(_TH_DIGITS)

def _fmt_date_th(v) -> str:
    """รับ date/datetime/str -> คืน dd/mm/พ.ศ. (เลขไทย)"""
    if not v:
        return "-"
    try:
        d = datetime.strptime(str(v)[:10], "%Y-%m-%d")
    except Exception:
        try:
            d = datetime.strptime(str(v)[:10], "%d/%m/%Y")
        except Exception:
            return "-"
    y = d.year + 543 if d.year < 2400 else d.year
    s = f"{d.day:02d}/{d.month:02d}/{y}"
    return to_thai_digits(s)

_DATE_YMD = re.compile(r"\b(?P<y>\d{4})[-/](?P<m>\d{1,2})[-/](?P<d>\d{1,2})\b")
_DATE_DMY = re.compile(r"\b(?P<d>\d{1,2})[-/](?P<m>\d{1,2})[-/](?P<y>\d{4})\b")

def _normalize_dates_to_be(text: str) -> str:
    """แปลงวันที่ในข้อความทั่วไปให้เป็น dd/mm/พ.ศ. และแปลงเลขทั้งหมดเป็นเลขไทย"""
    def _ymd(m: re.Match) -> str:
        y = int(m.group("y"))
        y = y + 543 if y < 2400 else y
        s = f"{int(m.group('d')):02d}/{int(m.group('m')):02d}/{y}"
        return to_thai_digits(s)

    def _dmy(m: re.Match) -> str:
        y = int(m.group("y"))
        y = y + 543 if y < 2400 else y
        s = f"{int(m.group('d')):02d}/{int(m.group('m')):02d}/{y}"
        return to_thai_digits(s)

    out = _DATE_YMD.sub(_ymd, text)
    out = _DATE_DMY.sub(_dmy, out)
    return to_thai_digits(out)

# ---------- OCR cleanup helpers ----------
def _normalize_thai_abbrev(s: str) -> str:
    """รวมคำย่อไทยที่ OCR ชอบตัด เช่น 'พ ศ' หรือ 'พ . ศ .' -> 'พ.ศ.'"""
    if not s:
        return s
    # zero-width space
    s = s.replace("\u200b", "")
    # พ.ศ.
    s = re.sub(r"พ\s*[\.\u200b]?\s*ศ\s*[\.\u200b]?\s*\.?", "พ.ศ.", s)
    # พ.ร.บ. / พ.ร.ก. / ร.ศ. (เพิ่มได้ตามต้องการ)
    s = re.sub(r"พ\s*[\.\u200b]?\s*ร\s*[\.\u200b]?\s*บ\s*[\.\u200b]?\s*\.?", "พ.ร.บ.", s)
    s = re.sub(r"พ\s*[\.\u200b]?\s*ร\s*[\.\u200b]?\s*ก\s*[\.\u200b]?\s*\.?", "พ.ร.ก.", s)
    s = re.sub(r"ร\s*[\.\u200b]?\s*ศ\s*[\.\u200b]?\s*\.?", "ร.ศ.", s)
    # ตัดอักษรไทยเดี่ยวที่ลอยก่อนขึ้นบรรทัดใหม่
    s = re.sub(r"(?<=\s)([ก-๙])\s*(?=\n)", "", s)
    return s


def _strip_markdown(s: str) -> str:
    if not s:
        return s
    # ลบ # ** * ` ที่ติดมาจาก OCR/Markdown
    s = re.sub(r"[#`*_]+", "", s)
    return s

# ---------- LLM call ----------
def _force_json(s: str) -> dict:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.IGNORECASE|re.DOTALL).strip()
    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if m:
        s = m.group(0)
    return json.loads(s)

def summarize_with_ollama(doc_name: str, meta: dict, ocr_text: str):
    user_payload = {
        "doc_name": doc_name,
        "meta": {
            "factionName": meta.get("factionName"),
            "typeName": meta.get("typeName"),
            "publishDate": meta.get("publishedDate") or meta.get("publishDate"),
            "effectiveDate": meta.get("effectiveDate"),
        },
        "ocr_excerpt": (_strip_markdown(_normalize_thai_abbrev(ocr_text)) or "")[:8000],
    }
    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": SYS_PROMPT},
                {"role": "user",   "content": json.dumps(user_payload, ensure_ascii=False)}
            ],
            "stream": False,
            "options": {"temperature": 0.2},
        },
        timeout=90,
    )
    r.raise_for_status()
    data = _force_json(r.json()["message"]["content"].strip())

    title   = (data.get("title") or doc_name or "เอกสาร").strip()
    summary = (data.get("summary") or "").strip()
    content = (data.get("content") or "").strip()

    # ทำความสะอาด + ปรับ พ.ศ./เลขไทย + รวมคำย่อไทย
    title   = _normalize_thai_abbrev(_normalize_dates_to_be(_strip_markdown(title)))
    summary = _normalize_thai_abbrev(_normalize_dates_to_be(_strip_markdown(summary)))
    content = _normalize_thai_abbrev(_normalize_dates_to_be(_strip_markdown(content)))

    if len(content) > 1200:
        content = content[:1200].rstrip()
    return title, summary, content

# ---------- Utils (scoring fallback) ----------
def _clean_ocr(txt: str | None) -> str:
    if not txt:
        return ""
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    txt = _strip_markdown(txt)
    txt = _normalize_thai_abbrev(txt)
    return txt.strip()

def _split_sentences_th(text: str) -> List[str]:
    parts = re.split(r"[\.!\?…\n]+", text)
    sents = [s.strip() for s in parts if len(s.strip()) > 0]
    return [s for s in sents if len(s) >= 25]

def _dedup_keep_order(items: List[str], threshold: int = 15) -> List[str]:
    def fingerprint(s: str) -> Counter:
        tokens = list(s)
        grams = [tuple(tokens[i:i+3]) for i in range(len(tokens)-2)]
        return Counter(grams)
    out, prints = [], []
    for s in items:
        fp = fingerprint(s)
        if any(((fp & fp2).total() / (fp | fp2).total() * 100 if (fp | fp2).total() else 0) >= threshold for fp2 in prints):
            continue
        out.append(s); prints.append(fp)
    return out

CORE_KEYWORDS = [
    "วัตถุประสงค์","เพื่อกำหนด","ขอบเขต","ให้ใช้บังคับ","บังคับใช้","ประกาศ","ประกาศ ณ",
    "ยกเลิก","ให้ยกเลิก","หลักเกณฑ์","เกณฑ์","นิยาม","คำจำกัดความ",
    "ภาระงาน","งานสอน","งานวิจัย","ผลงานทางวิชาการ","บริการวิชาการ",
    "ทำนุบำรุงศิลปะและวัฒนธรรม","คณะกรรมการ","อธิการบดี","การประเมิน","เลื่อนเงินเดือน","สิทธิประโยชน์",
]

def _score_sentence(sent: str, title: str, keywords: List[str]) -> float:
    score = 0.0
    for kw in keywords:
        if kw in sent: score += 3.0
    for t in re.split(r"\s+", title.strip()):
        if len(t) >= 3 and t in sent: score += 0.8
    L = len(sent)
    if 40 <= L <= 220: score += 1.5
    elif L > 250: score -= 0.5
    return score

def summarize_rule_based(ocr_text: str, title: str, max_lines: int = 10) -> str:
    text = _clean_ocr(ocr_text)
    sents = _split_sentences_th(text)
    scored = []
    for idx, s in enumerate(sents):
        base = _score_sentence(s, title, CORE_KEYWORDS)
        pos_bonus = max(0.0, 2.0 - 0.05*idx)
        scored.append((base + pos_bonus, idx, s))
    scored.sort(key=lambda x: (-x[0], x[1]))
    ranked = _dedup_keep_order([s for _,_,s in scored], threshold=18)
    pick = ranked[:max_lines] or (sents[:max_lines] if sents else [text[:300]])
    return "\n".join(pick)

def summarize_compact_rule_based(ocr_text: str, title: str) -> str:
    txt = _clean_ocr(ocr_text)
    m_eff = re.search(r"(ให้ใช้บังคับตั้งแต่[^.\n]+)", txt)
    m_rep = re.search(r"(ให้ยกเลิก[^.\n]+)", txt)
    m_pow = re.search(r"(อาศัยอำนาจ[^.\n]+)", txt)
    items = re.findall(r"[\(（]\s*[๑-๙0-9]+\s*[\)）]\s*([^(\n]+)", txt)
    items = [re.sub(r"\s+", " ", it).strip(" ,.;") for it in items][:6]
    bullets = []
    if m_eff: bullets.append(m_eff.group(1).strip())
    if m_rep: bullets.append(m_rep.group(1).strip())
    if m_pow: bullets.append(m_pow.group(1).strip())
    if items:
        bullets.append("กำหนดอำนาจ/แนวทางหลัก เช่น " + "; ".join(items))
    return " ".join(bullets) if bullets else summarize_rule_based(ocr_text, title, max_lines=6)

# ---------- main entry (LLM + fallback) ----------
def make_wiki_from_payload(doc_name: str, meta: dict, ocr_text: str) -> tuple[str, str, str]:
    title = doc_name or "เอกสาร"
    faction = meta.get("factionName") or "-"
    dtype   = meta.get("typeName") or "-"
    pub     = _fmt_date_th(meta.get("publishedDate") or meta.get("publishDate"))
    eff     = _fmt_date_th(meta.get("effectiveDate"))

    summary_default = f"{dtype}ฉบับนี้ออกโดย{faction} ประกาศเมื่อ {pub} และมีผลใช้บังคับตั้งแต่ {eff}"

    try:
        t, s, c = summarize_with_ollama(title, meta, ocr_text)
        # กันพลาดอีกชั้น
        t = _normalize_thai_abbrev(_normalize_dates_to_be(t))
        s = _normalize_thai_abbrev(_normalize_dates_to_be(s))
        c = _normalize_thai_abbrev(_normalize_dates_to_be(c))
        return t or title, s or summary_default, c or summarize_compact_rule_based(ocr_text, title)
    except Exception:
        return to_thai_digits(title), summary_default, to_thai_digits(summarize_compact_rule_based(ocr_text, title))   
#------------------get,update,del-----------------
def update_wiki(db: Session, wiki_id: int, payload: WikiUpdate) -> Wiki:
    wiki = db.query(Wiki).filter(Wiki.wikiId == wiki_id).first()
    if not wiki:
        raise HTTPException(status_code=404, detail="Wiki not found")
    try:
        updates = payload.model_dump(exclude_unset=True, exclude_none=True)  
    except AttributeError:
     
        updates = payload.dict(exclude_unset=True, exclude_none=True)

    updates.pop("wikiId", None) 

    for k, v in updates.items():
        setattr(wiki, k, v)


    db.commit()
    db.refresh(wiki)
    return wiki


def get_all_wiki(db: Session):
    return db.query(Wiki).all()

def get_wiki_by_id(db: Session, wiki_id: int):
    wiki = db.query(Wiki).filter(Wiki.wikiId == wiki_id).first()  
    if not wiki:
        raise HTTPException(status_code=404, detail="Wiki not found")
    return wiki

def delete_wiki(db: Session, wiki_id: int):
    wiki = db.query(Wiki).filter(Wiki.wikiId == wiki_id).first()
    if not wiki:
        raise HTTPException(status_code=404, detail="Wiki not found")

    # 1) เคลียร์ wikiId ใน Document ที่อ้าง wiki นี้อยู่
    docs = db.query(Document).filter(Document.wikiId == wiki_id).all()
    for d in docs:
        d.wikiId = None

    # 2) ลบ wiki
    db.delete(wiki)
    db.commit()

    return {"detail": f"Wiki {wiki_id} deleted", "docs_unlinked": [d.docId for d in docs]}