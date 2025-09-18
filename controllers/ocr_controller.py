import os
import io
import cv2
import re
import fitz  # PyMuPDF
import thaispellcheck
import numpy as np
import tempfile
import os
import urllib.parse
# import pandas as pd
# import ollama
# import pytesseract
from celery.exceptions import Ignore
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
from tempfile import NamedTemporaryFile
from fastapi import UploadFile
from dotenv import load_dotenv
from typhoon_ocr import ocr_document
from celery import Celery
from redis import Redis

# from pytesseract import Output
# from fitz import TextWriter

load_dotenv()


redis_url = os.getenv("REDIS_URL")
url = urllib.parse.urlparse(redis_url)

celery_app = Celery("worker", broker=redis_url, backend=redis_url)
r = Redis(host=url.hostname, port=url.port, password=url.password, decode_responses=True)
# client = ollama.Client()
# model = "scb10x/llama3.1-typhoon2-8b-instruct"
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# def test_llm(text:str):
#     print('use llm')
#     prompt = f"""ข้อความต่อไปนี้มีคำผิด กรุณาแก้ไขคำสะกดผิดทั้งหมดให้ถูกต้อง และส่งกลับ **เฉพาะข้อความที่แก้ไขแล้วเท่านั้น** โดยไม่ต้องเพิ่มข้อความอื่น เช่น คำอธิบาย บรรทัดใหม่ หรือหัวข้อใดๆ
    
#             {text}"""
            
#     response = client.generate(model=model, prompt=prompt)
#     return response.response

def find_misspelled_words(text:str):
    """ ตรวจสอบคำผิดจากข้อความ OCR """
    # thaispellcheck.check(text, autocorrect=True) เเบบเเก้คำผิดอัตโนมัติ
    return thaispellcheck.check(text) 

def correct_text(text:str):  #เเก้คำที่ผิดบ่อย ทำมือ
    correct_text = re.sub(r'[ก-๙]\.ศ', 'พ.ศ', text) 
    return correct_text

def clean_df(df):
    def is_noise(text):
        # ตัดแถวที่มีแต่ - หรือมีตัวอักษรน้อยเกินไป
        return bool(re.fullmatch(r'[-\s\d]{1,4}', text.strip()))  # เช่น "-", "--", "- 0"

    df = df[~df['text'].apply(is_noise)]
    df = df.reset_index(drop=True)
    return df

def prepare_dataframe(df):
    index_to_drop = []
    for index, row in df.iterrows():
        if(index==(len(df)-1)):
            break
        if((df['top'].iloc[index+1] - df['top'].iloc[index]) < 20):
            df.at[index, 'text'] = df.at[index,'text'] + ' ' + df.at[index+1,'text']
            index_to_drop.append(index + 1)
        
    df = df.drop(index_to_drop).reset_index(drop=True)
    df = clean_df(df)
    return df

def format_ocr_result(ocr_result:str):
    lines = ['<br>' if line == '' else line for line in ocr_result.split('\n')]
    ocr_format = ''.join(f'<div style="text-align: left;">{line}</div>' for line in lines)
    ocr_format = find_misspelled_words(ocr_format)
    return ocr_format

def process_image_to_text(page, img, page_width, page_height):
    try:
        img_arr = np.array(img)
        img_arr = cv2.cvtColor(img_arr, cv2.COLOR_BGR2GRAY)
        img_arr = cv2.medianBlur(img_arr, 3)

        with NamedTemporaryFile(delete=True, suffix=".png") as tmp:
            temp_path = tmp.name
            tmp.close()
            img.save(temp_path)
            # Process a specific page from a PDF
            markdown = ocr_document(
                pdf_or_image_path=temp_path,
                task_type="default",
                page_num=1
            )
        ocr_text = markdown
        
        # ocr_text_list = [t.strip() for t in ocr_text.split('\n') if t.strip() != '']
        # ocr_df = pytesseract.image_to_data(img_arr, lang='tha', config='--psm 11', output_type=Output.DATAFRAME)
        # ocr_df = ocr_df.dropna()
        # ocr_df = ocr_df.groupby('block_num').agg({
        #     'left': 'first',
        #     'top': 'first',
        #     'width': 'first',
        #     'height': 'first',
        #     'text': lambda x: ''.join(x)
        # }).reset_index(drop=True)
        # ocr_df = prepare_dataframe(ocr_df)
        # ocr_df['text'] = ocr_text_list

        # img_width, img_height = img.size
        # scale_x = page_width / img_width
        # scale_y = page_height / img_height
        # font_size = ocr_df['height'].quantile(0.95) * scale_y * 0.8

        # tw = TextWriter(page.rect)
        # for _, row in ocr_df.iterrows():
        #     x = row['left'] * scale_x
        #     y = (row['top'] + row['height']) * scale_y
        #     tw.append((x, y), row['text'], fontsize=font_size)
        # tw.write_text(page, render_mode=3)

        return ocr_text + '\n\n'
    finally:
        os.remove(temp_path)

@celery_app.task(bind=True)
def process_ocr(self,file_bytes, file_name):   
    ocr_result = ''
    
    content_type = os.path.splitext(file_name)[1].lower()
    
    # ถ้าเป็น PDF
    if 'pdf' in content_type:
        with fitz.open(stream=file_bytes, filetype='pdf') as doc:
            
            task_id = self.request.id
            total_pages = doc.page_count
            progress = "0"
            
            with fitz.open() as new_doc:
                for page in doc:
                    page_width, page_height = page.rect.br
                    page_rot = page.rotation
                    page.set_rotation(0)
                    new_doc_page = new_doc.new_page(width=page_width, height=page_height)
                    new_doc_page.show_pdf_page(
                        new_doc_page.rect,
                        doc,
                        page.number,
                        rotate=-page_rot
                    )

                    pix = new_doc_page.get_pixmap(matrix=fitz.Matrix(2,2))
                    with Image.open(io.BytesIO(pix.tobytes('png'))) as img:
                        #OCR
                        if(r.get(f'{task_id}_cancel')):
                            r.delete(f'{task_id}_cancel')
                            self.update_state(state="CANCEL", meta={"current_page": page.number, "total_page": total_pages, "progress": progress})
                            raise Ignore()
                        self.update_state(state="PROGRESS", meta={"current_page": page.number, "total_page": total_pages, "progress": progress})
                        try:
                            ocr_result += process_image_to_text(new_doc_page, img, page_width, page_height)
                        except Exception as e:
                            print(f'OCR failed: {e}')
                            self.update_state(state="FAILURE")
                            raise Ignore()
                        progress = str(round((page.number/total_pages)*100))
                        self.update_state(state="PROGRESS", meta={"current_page": page.number, "total_page": total_pages, "progress": progress})
        # formatting ocr_result
        ocr_format = format_ocr_result(ocr_result)

        # new_doc.ez_save('file/output.pdf')
        return ocr_format

    # ถ้าเป็นภาพ (jpg, png ฯลฯ)
    elif 'image' in content_type:
        with Image.open(BytesIO(file_bytes)) as img:
            progress = "0"

            # สร้างหน้ากระดาษใหม่ให้พอดีกับขนาดภาพ
            page_width, page_height = 595.276, 841.890 #ขนาด A4 ใน pdf
            with fitz.open() as new_doc:
                new_doc_page = new_doc.new_page(width=page_width, height=page_height)

                # วางภาพลงบนหน้ากระดาษ (optional)
                new_doc_page.insert_image(new_doc_page.rect, stream=file_bytes)

                # OCR
                if(r.get(f'{task_id}_cancel')):
                    r.delete(f'{task_id}_cancel')
                    self.update_state(state="CANCEL", meta={"current_page": 1, "total_page": 1, "progress": progress})
                    raise Ignore()
                self.update_state(state="PROGRESS", meta={"current_page": 1, "total_page": 1, "progress": progress})
                try:
                    ocr_result += process_image_to_text(new_doc_page, img, page_width, page_height)
                except Exception as e:
                    print(f'OCR failed: {e}')
                    self.update_state(state="FAILURE")
                    raise Ignore()
        # formatting ocr_result
        ocr_format = format_ocr_result(ocr_result)

        # new_doc.ez_save('file/output.pdf')
        return ocr_format

    else:
        return {"error": "Unsupported file type"}

    
def richtext_to_plaintext(text:str):
    html = text
    # Parse and extract text
    soup = BeautifulSoup(html, 'html.parser')
    
    plain_text = soup.get_text(separator=' ', strip=True)
    
    for span in soup.find_all('span'):
        span.unwrap()
    del_span_text = str(soup)

    return plain_text, del_span_text