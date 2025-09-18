import os
# import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from routes import faction_route, type_route, document_route, meta_route,user_route,role_route, ocr_route, wiki_route

app = FastAPI()

if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

ALLOWED_ORIGINS_RAW = os.getenv("ALLOWED_ORIGINS", "")

# แตกเป็น list + trim + กรองค่าว่าง + กันซ้ำ
origins = []
if ALLOWED_ORIGINS_RAW:
    origins = [o.strip() for o in ALLOWED_ORIGINS_RAW.split(",") if o.strip()]

# เพิ่ม local default เผื่อไม่ได้ใส่ใน ENV
for o in ("http://localhost:5173", "http://localhost:9000"):
    if o not in origins:
        origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(faction_route.router)
app.include_router(type_route.router)
app.include_router(document_route.router)
app.include_router(meta_route.router)
app.include_router(user_route.router)
app.include_router(role_route.router)
app.include_router(ocr_route.router)
app.include_router(wiki_route.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
@app.get("/healthz")
def healthz():
    return {"ok": True}
