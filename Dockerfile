FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=300

# Base libs สำหรับภาพ/PDF/LibreOffice + poppler (ใช้แปลง DOCX เป็น PDF และงาน PDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ libpq-dev \
    ffmpeg libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    libjpeg62-turbo zlib1g libpng16-16 libgomp1 \
    libreoffice-writer fonts-dejavu-core \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONPATH=/app

# 1) ติดตั้ง requirements
COPY requirements.txt .
RUN pip install --retries 20 --timeout 600 -r requirements.txt

# 2) (ถ้ามี) ติดตั้ง ML เพิ่ม — แต่ถ้าโปรเจกต์นี้ไม่ต้องใช้ torch/vision/audio สามารถตัดส่วนนี้ทิ้งได้
# COPY requirements-ml.txt .
# RUN pip install --retries 20 --timeout 1200 \
#     --index-url https://download.pytorch.org/whl/cpu \
#     torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 && \
#     pip install --retries 20 --timeout 1200 -r requirements-ml.txt

# 3) คัดลอกโค้ด
COPY . .

# โฟลเดอร์เก็บไฟล์
RUN mkdir -p /app/file

EXPOSE 8000
