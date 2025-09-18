from sqlalchemy.orm import Session
from models.role import Role
from schemas.role import RoleCreate, RoleUpdate
from fastapi import HTTPException

def create_role(db: Session, role_data: RoleCreate):
    role = Role(**role_data.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role

def get_all_roles(db: Session):
    return db.query(Role).all()

def get_role_by_id(db: Session, role_id: int):
    role = db.query(Role).filter(Role.roleId == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role

def update_role(db: Session, role_id: int, role_data: RoleUpdate):
    role = db.query(Role).filter(Role.roleId == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    for key, value in role_data.dict().items():
        setattr(role, key, value)
    db.commit()
    db.refresh(role)
    return role

def delete_role(db: Session, role_id: int):
    role = db.query(Role).filter(Role.roleId == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    db.delete(role)
    db.commit()
    return {"message": "Role deleted"}
