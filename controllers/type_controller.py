from sqlalchemy.orm import Session
from models import Type
from schemas.type import TypeCreate, TypeUpdate
from fastapi import HTTPException

def create_type(db: Session, type:TypeCreate):
    new_type = Type(**type.model_dump())
    db.add(new_type)
    db.commit()
    db.refresh(new_type)
    return new_type

def get_all_types(db: Session):
    return db.query(Type).all()

def get_type_by_id(db: Session, type_id: int):
    type = db.query(Type).filter(Type.typeId == type_id).first()
    if not type:
        raise HTTPException(status_code=404, detail="Type not found")
    return type

def update_type(db: Session, type_id: int, type_data: TypeUpdate):
    type = db.query(Type).filter(Type.typeId == type_id).first()
    if not type:
        raise HTTPException(status_code=404, detail="Type not found")
    for key, value in type_data.dict().items():
        setattr(type, key, value)
    db.commit()
    db.refresh(type)
    return type

def delete_type(db: Session, type_id: int):
    type = db.query(Type).filter(Type.typeId == type_id).first()
    if not type:
        raise HTTPException(status_code=404, detail="Type not found")
    db.delete(type)
    db.commit()
    return {"message": "Type deleted"}
