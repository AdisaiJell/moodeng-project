import re

import spacy
from datetime import datetime, timedelta
from typing import Optional, Tuple

from fuzzywuzzy import fuzz, process
from sqlalchemy.orm import Session

from models import Meta, Faction, Type


try:
  
    nlp_en = spacy.load("en_core_web_sm")
except Exception as e:
    print("SpaCy load failed:", e)
    nlp_en = None


# ------------------ 1) ฟังก์ชันช่วยแก้สะกด OCR เบื้องต้น ------------------ #
def ocr_spell_fix(text: str) -> str:
    # ตัวอย่าง: แก้คำผิดที่เจอบ่อยใน OCR
    replaces = {
        "ตั่งแต่": "ตั้งแต่",
        "ท.ศ.": "พ.ศ.",  # OCR ชอบเพี้ยน
        "ข้ือบังคับ": "ข้อบังคับ",
        # เพิ่มตามเคสที่เจอ
    }
    for wrong, right in replaces.items():
        text = text.replace(wrong, right)
    return text

# ------------------ 2) ฟังก์ชันแปลงสตริงวันที่ไทย -> datetime ------------------ #
def parse_thai_date(date_str: str) -> Optional[datetime]:
    """
    รองรับรูปแบบ:
    - DD เดือน(ไทย) [พ.ศ.] YYYY
    - DD-MM-YYYY
    - DD/MM/YYYY
    """
    date_str = date_str.strip()
    # Regex หลัก
    patterns = [
        # DD เดือน(ไทย) [พ.ศ.] YYYY
        r"^(\d{1,2})\s*(มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)(?:\s*พ\.ศ\.)?\s*(\d{4})$",
        # DD-MM-YYYY
        r"^(\d{1,2})-(\d{1,2})-(\d{4})$",
        # DD/MM/YYYY
        r"^(\d{1,2})/(\d{1,2})/(\d{4})$"
    ]
    month_map = {
        "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4,
        "พฤษภาคม": 5, "มิถุนายน": 6, "กรกฎาคม": 7, "สิงหาคม": 8,
        "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12
    }

    for pattern in patterns:
        match = re.match(pattern, date_str)
        if match:
            try:
                groups = match.groups()
                if len(groups) == 3:
                    # DD เดือน(ไทย) YYYY
                    day = int(groups[0])
                    month_thai = groups[1]
                    year = int(groups[2])
                    # แปลงเดือน
                    if month_thai in month_map:
                        month = month_map[month_thai]
                    else:
                        month = 1
                    # ถ้าเป็น พ.ศ. > 2400 -> ค.ศ.
                    if year > 2400:
                        year -= 543
                    return datetime(year, month, day)
                elif len(groups) == 4:
                    # DD-MM-YYYY หรือ DD/MM/YYYY
                    day = int(groups[0])
                    month = int(groups[1])
                    year = int(groups[2])
                    if year > 2400:
                        year -= 543
                    return datetime(year, month, day)
            except:
                pass
    return None

# ------------------ 3) ฟังก์ชันดึงวันที่ทั้งหมด + วิเคราะห์คีย์เวิร์ด ------------------ #
def extract_all_dates_with_context(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    ค้นหา 'ทุกวันที่' ที่เป็นไปได้ใน text
    แล้วดูบริบทก่อน/หลังวันที่ เพื่อดูว่าเป็น "ประกาศ" (publishedDate) หรือ "บังคับใช้" (effectiveDate)
    - ถ้าเจอหลายวัน ก็เอาวันแรกที่เจอคีย์เวิร์ด "ประกาศ" เป็น publishedDate
    - เอาวันแรกที่เจอคีย์เวิร์ด "บังคับใช้" หรือ "ตั้งแต่" เป็น effectiveDate
    - ถ้าไม่เจอเลย -> คืน None
    """

    # 1) Regex จับทุกวันที่
    #    ครอบคลุม DD เดือน(ไทย) [พ.ศ.] YYYY, DD-MM-YYYY, DD/MM/YYYY
    #    ใช้ finditer เพื่อได้ตำแหน่ง match
    date_pattern = re.compile(
        r"(\d{1,2}\s*(?:มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)(?:\s*พ\.ศ\.)?\s*\d{4}"
        r"|\d{1,2}-\d{1,2}-\d{4}"
        r"|\d{1,2}/\d{1,2}/\d{4})"
    )

    published_date_str = None
    effective_date_str = None

    for m in date_pattern.finditer(text):
        date_str = m.group(1).strip()
        # แปลงเป็น datetime
        dt = parse_thai_date(date_str)
        if not dt:
            continue

        # บริบทก่อน/หลัง (เช่น 50 อักขระ)
        start_idx = m.start()
        context_before = text[max(0, start_idx - 50): start_idx].lower()
        # context_after = text[m.end(): m.end() + 50].lower()  # ถ้าต้องการดูหลังด้วย

        # 2) เช็คคีย์เวิร์ดใน context_before
        #    เช่น "ประกาศ", "ณ วันที่", "ออกประกาศ", "ให้ใช้บังคับ", "ตั้งแต่", "บังคับใช้"
        #    ถ้าเจอ "ประกาศ" -> ถือเป็น candidate ของ published_date
        #    ถ้าเจอ "ตั้งแต่", "บังคับใช้" -> ถือเป็น candidate ของ effective_date

        if published_date_str is None:  # ยังไม่เคยตั้ง publishedDate
            if ("ประกาศ" in context_before) or ("ณ วันที่" in context_before):
                published_date_str = dt.strftime("%Y-%m-%d")

        if effective_date_str is None:  # ยังไม่เคยตั้ง effectiveDate
            if ("ตั้งแต่" in context_before) or ("บังคับใช้" in context_before):
                effective_date_str = dt.strftime("%Y-%m-%d")

        # ถ้าเจอแล้วทั้ง 2 วัน อาจ break ได้
        if published_date_str and effective_date_str:
            break

    return (published_date_str, effective_date_str)

# ------------------ 4) ฟังก์ชันค้นหา Faction / Type จาก DB (Fuzzy Matching) ------------------ #
def extract_faction_from_db(text: str, db: Session) -> str:
    all_factions = db.query(Faction).all()
    known_factions = [f.factionName for f in all_factions]
    if not known_factions:
        return "ไม่พบหน่วยงานใน DB"
    best_match, score = process.extractOne(text, known_factions, scorer=fuzz.partial_ratio)
    if best_match and score >= 60:
        return best_match
    return "ไม่พบหน่วยงาน"

def extract_type_from_db(text: str, db: Session) -> str:
    all_types = db.query(Type).all()
    known_types = [t.typeName for t in all_types]
    if not known_types:
        return "ไม่พบประเภทใน DB"
    best_match, score = process.extractOne(text, known_types, scorer=fuzz.partial_ratio)
    if best_match and score >= 60:
        return best_match
    return "ไม่พบประเภท"

# ------------------ 5) ฟังก์ชันหลัก: ดึง metadata จาก OCR Text ------------------ #
def extract_metadata(ocr_text: str, db: Session):
    import re
    from fastapi import HTTPException
    from pythainlp.tokenize import word_tokenize, syllable_tokenize
    from pythainlp.util import thai_digit_to_arabic_digit

    stopwords = {"และ", "หรือ", "ที่", "ให้", "ตาม", "ใน", "ของ", "กับ", "จาก", "ว่า", "ได้", "ด้วย", "เป็น", "โดย"}

    def is_valid_keyword(word: str, freq: int) -> bool:
        if word in stopwords:
            return False
        if len(word) < 2:
            return False
        if re.search(r"\d", word):  # ตัวเลข
            return False
        if re.search(r"[^\u0E00-\u0E7Fa-zA-Z]", word):  # อักขระพิเศษ
            return False
        if freq > 3:
            return False
        try:
            if len(syllable_tokenize(word)) < 2:
                return False
        except:
            return False
        return True

    try:
        # 1. แก้คำผิด OCR
        text_fixed = ocr_spell_fix(ocr_text)
        # 2. แปลงเลขไทย
        text_fixed = thai_digit_to_arabic_digit(text_fixed)
        # 3. หา date
        pub_date, eff_date = extract_all_dates_with_context(text_fixed)
         # ถ้าไม่เจอ effectiveDate → ใช้ publishedDate + 1 วัน
        if eff_date is None and pub_date:
            try:
                eff_dt = datetime.strptime(pub_date, "%Y-%m-%d") + timedelta(days=1)
                eff_date = eff_dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # fallback ถ้าไม่มีจริง ๆ
        pub_date = pub_date or "ไม่พบวันที่"
        eff_date = eff_date or "ไม่พบวันที่"
        # 4. แยกคำ
        thai_words = word_tokenize(text_fixed, keep_whitespace=False)
        english_words = []
        if nlp_en:
            try:
                doc_en = nlp_en(text_fixed)
                english_words = [token.text for token in doc_en if token.is_alpha]
            except:
                pass
        # 5. Faction + Type
        faction_name = extract_faction_from_db(text_fixed, db)
        type_name = extract_type_from_db(text_fixed, db)

        # 6. รวมคำและนับความถี่
        raw_keywords = thai_words + english_words
        freq_dict = {}
        for word in raw_keywords:
            freq_dict[word] = freq_dict.get(word, 0) + 1

        # 7. คัดกรอง
        filtered = [w for w in freq_dict if is_valid_keyword(w, freq_dict[w])]

        # 8. เรียงลำดับและเลือกไม่เกิน 6 คำ
        sorted_keywords = sorted(filtered, key=lambda w: freq_dict[w], reverse=True)
        keyword_list = sorted_keywords[:8]

        return {
            "factionName": faction_name,
            "typeName": type_name,
            "publishedDate": pub_date,
            "effectiveDate": eff_date,
            "keyword": keyword_list,
            "relateDoc": []
        }

    except Exception as e:
        print("❌ Metadata extraction failed:", e)
        raise HTTPException(status_code=500, detail="Metadata processing failed.")


# ------------------ ฟังก์ชันบันทึกลง DB ------------------ #
def save_metadata_to_db(db: Session, meta_data: dict):
    new_meta = Meta(
        factionName=meta_data["factionName"],
        typeName=meta_data["typeName"],
        publishedDate=meta_data["publishedDate"],
        effectiveDate=meta_data["effectiveDate"],
        keyword=meta_data["keyword"] if isinstance(meta_data["keyword"], list) else [],
        relateddoc=meta_data["relateDoc"] if isinstance(meta_data["relateDoc"], list) else []
    )
    db.add(new_meta)
    db.commit()
    db.refresh(new_meta)
    return new_meta
