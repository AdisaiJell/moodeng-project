from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from controllers import type_controller 
from schemas.type import TypeCreate, TypeOut, TypeUpdate

router = APIRouter(prefix="/type", tags=["Type"])

@router.post("/create")
async def create_type_api(type:TypeCreate, db: Session = Depends(get_db)):
    return type_controller.create_type(db, type)

@router.get("/all")
async def get_types_api(db: Session = Depends(get_db)):
    return type_controller.get_all_types(db)

@router.get("/get/{type_id}", response_model=TypeOut)
def get_type(type_id: int, db: Session = Depends(get_db)):
    return type_controller.get_type_by_id(db, type_id)

@router.put("/update/{type_id}", response_model=TypeOut)
def update_type(type_id: int, type: TypeUpdate, db: Session = Depends(get_db)):
    return type_controller.update_type(db, type_id, type)

@router.delete("/del/{type_id}")
def delete_type(type_id: int, db: Session = Depends(get_db)):
    return type_controller.delete_type(db, type_id)