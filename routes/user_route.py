from fastapi import APIRouter, Depends, UploadFile, Form, File
from sqlalchemy.orm import Session
from database import get_db
from schemas.user import UserCreate, UserUpdate, UserOut
from typing import List
import controllers.user_controller as user_controller
import uuid
from typing import Optional

router = APIRouter(prefix="/user", tags=["User"])

@router.post("/create")
def create_user(
    userName: str = Form(...),
    email: str = Form(...),
    roleId: int = Form(...),
    factId: int = Form(...),
    image: Optional[UploadFile] = File(None),  # รับไฟล์
    db: Session = Depends(get_db),
):
    image_filename = "default_image.jpg"
    if image:
        print(image.filename)
    
    if image is not None and image.filename != '':
    
        ext = image.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{ext}"
    
        # save image to static folder
        file_location = f"static/images/{unique_filename}"
        with open(file_location, "wb") as f:
            f.write(image.file.read())
            
        image_filename = unique_filename

    # สร้าง object UserCreate แล้วส่งไป controller
    user_data = UserCreate(
        userName=userName,
        email=email,
        roleId=roleId,
        factId=factId,
    )
    print(user_data)
    return user_controller.create_user(db, user_data, image_filename)

@router.get("/getAll", response_model=List[UserOut])
def get_users(db: Session = Depends(get_db)):
    return user_controller.get_all_users(db)

@router.get("/get/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    return user_controller.get_user_by_id(db, user_id)

@router.put("/update/{userId}", response_model=UserOut)
def update_user(
    userId: int,
    userName: str = Form(...),
    email: str = Form(...),
    roleId: int = Form(...),
    factId: int = Form(...),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):  
    image_filename = user_controller.get_user_by_id(db, userId).image
    # ถ้ามีรูปใหม่ ให้บันทึกลงไฟล์ใหม่
    if image is not None and image.filename != "":
        ext = image.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{ext}"
        
        file_location = f"static/images/{unique_filename}"
        with open(file_location, "wb") as f:
            f.write(image.file.read())
        image_filename = unique_filename  # อัปเดตรูปใหม่
        
    user_update = UserUpdate(
        userId=userId,
        userName=userName,
        email=email,
        roleId=roleId,
        factId=factId
    )
    
    return user_controller.update_user(db, user_update, image_filename)

@router.delete("/del/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    return user_controller.delete_user(db, user_id)
