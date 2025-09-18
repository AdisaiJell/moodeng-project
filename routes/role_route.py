from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas.role import RoleCreate, RoleUpdate, RoleOut
from typing import List
import controllers.role_controller as role_controller

router = APIRouter(prefix="/role", tags=["Role"])

@router.post("/creat", response_model=RoleOut)
def create_role(role: RoleCreate, db: Session = Depends(get_db)):
    return role_controller.create_role(db, role)

@router.get("/get", response_model=List[RoleOut])
def get_roles(db: Session = Depends(get_db)):
    return role_controller.get_all_roles(db)

@router.get("/get/{role_id}", response_model=RoleOut)
def get_role(role_id: int, db: Session = Depends(get_db)):
    return role_controller.get_role_by_id(db, role_id)

@router.put("/update/{role_id}", response_model=RoleOut)
def update_role(role_id: int, role: RoleUpdate, db: Session = Depends(get_db)):
    return role_controller.update_role(db, role_id, role)

@router.delete("/del/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db)):
    return role_controller.delete_role(db, role_id)
