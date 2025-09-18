import json
import asyncio
from redis import Redis
from fastapi import APIRouter, UploadFile, File, WebSocket
from controllers.ocr_controller import find_misspelled_words, richtext_to_plaintext, process_ocr

r = Redis(host="redis", port=6379, decode_responses=True)

router = APIRouter(prefix="/ocr", tags=["OCR"])

@router.post("/process")
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
    
@router.post('/cancel-ocr/{task_id}')
def cancel_ocr(task_id:str):
    r.setex(f'{task_id}_cancel', 600, 1)
    return {"task_id": task_id, "status": "CANCEL"}
    
    

@router.websocket('/progress/{task_id}')
async def progress(websocket: WebSocket, task_id: str):
    await websocket.accept()
    while True:
        result = process_ocr.AsyncResult(task_id)
        if result.state == "SUCCESS":
            progress = "100"
            await websocket.send_text(json.dumps({"state": result.state, "progress": progress, "result": result.result}))
            print('result: ',result.result)
            break
        elif result.state == "PROGRESS":
            progress = result.info.get("progress")
            await websocket.send_text(json.dumps({"state": result.state, "progress": progress}))
        elif result.state == "CANCEL":
            progress = result.info.get("progress")
            await websocket.send_text(json.dumps({"state": "CANCEL", "progress": progress}))
            break
        elif result.state == "FAILURE":
            await websocket.send_text(json.dumps({"state": "FAILURE", "progress": "0"}))
            break
        await asyncio.sleep(0.5)  
    await websocket.close()

@router.post("/find_misspelled_words")
async def find_misspelled(text:str):
    return find_misspelled_words(text)

@router.post("/richtext_to_plaintext")
async def convert_to_plaintext(text:str):
    return richtext_to_plaintext(text)