# Back-End

## Installation

### Prerequisites

Ensure you have the following installed:

```sh
# Install Python (version < 3.12)
python-3.11

# Install Git if not already installed

```

### Setup

Clone the repository:

```sh
git clone https://gitlab.com/mo7204209/back_end_jell.git
cd back_end_jell
```

### Create and Activate Virtual Environment

It is recommended to use a virtual environment to manage dependencies.

```sh
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows
.venv\Scripts\activate

# On Mac/Linux
source .venv/bin/activate
```

### Install Dependencies

```sh
pip install -r requirements.txt
```

### Updating Dependencies

If you install new dependencies, update `requirements.txt` using:

```sh
pip freeze > requirements.txt
```

Then, make sure others update their dependencies by running:

```sh
pip install -r requirements.txt
```

### Running the Project

After installing dependencies, you can run the project using:

```sh
python main.py
```

---

## การตั้งค่า Environment Variables (.env)

โปรเจกต์นี้ใช้ไฟล์ .env เพื่อเก็บค่าคอนฟิกต่าง ๆ ที่สำคัญ เช่น การเชื่อมต่อฐานข้อมูล, API Keys และการตั้งค่าอื่น ๆ

---

## วิธีสร้างไฟล์ .env

1. ให้สร้างไฟล์ชื่อ .env ในโฟลเดอร์รากของโปรเจกต์ (ที่เดียวกับไฟล์ README.md)

2. ใส่ค่าตัวแปรต่าง ๆ ตามไฟล์ .env.example ได้เลย

---

## Run Project ด้วย Docker

### ติดตั้ง Docker Desktop ผ่านลิงก์นี้เลย
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

คำสั่ง build เเละ start containers
```sh
docker compose up -d --build
```
คำสั่ง stop containers
```sh
docker compose down
```

