from sqlalchemy.orm import Session
from models.user import User
from schemas.user import UserCreate, UserUpdate
from fastapi import HTTPException

def create_user(db: Session, user_data: UserCreate, image_filename: str):
    user = User(
        userName=user_data.userName,
        email=user_data.email,
        roleId=user_data.roleId,
        factId=user_data.factId,
        image=image_filename  # บันทึกชื่อไฟล์ลง DB
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_all_users(db: Session):
    return db.query(User).all()

def get_user_by_id(db: Session, user_id: int):
    user = db.query(User).filter(User.userId == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def update_user(db: Session, user_data: UserUpdate, image_filename:str):
    user = db.query(User).filter(User.userId == user_data.userId).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.userName = user_data.userName
    user.email = user_data.email
    user.roleId = user_data.roleId
    user.factId = user_data.factId
    user.image = image_filename
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user_id: int):
    user = db.query(User).filter(User.userId == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}