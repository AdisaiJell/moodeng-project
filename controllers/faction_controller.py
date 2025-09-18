from sqlalchemy.orm import Session
from models import Faction
from schemas.faction import FactionCreate, FactionUpdate 
from fastapi import HTTPException

def create_faction(db: Session, faction: FactionCreate):
    print("DEBUG faction.factionName:", repr(faction.factionName))
    
    existing_faction = db.query(Faction).filter(Faction.factionName == faction.factionName).first()
    print("DEBUG existing_faction:", existing_faction)

    if existing_faction:
        raise HTTPException(
            status_code=400,
            detail=f"Faction '{faction.factionName}' already exists."
        )

    new_faction = Faction(**faction.model_dump())
    db.add(new_faction)
    db.commit()
    db.refresh(new_faction)
    return new_faction

def get_all_factions(db: Session):
    return db.query(Faction).all()

def get_faction_by_id(db: Session, fact_id: int):
    faction = db.query(Faction).filter(Faction.factId == fact_id).first()
    if not faction:
        raise HTTPException(status_code=404, detail="Faction not found")
    return faction

def update_faction(db: Session, fact_id: int, faction_data: FactionUpdate):
    faction = db.query(Faction).filter(Faction.factId == fact_id).first()
    if not faction:
        raise HTTPException(status_code=404, detail="Faction not found")

    updates = faction_data.model_dump(exclude_unset=True, exclude_none=True)
    updates.pop("factId", None)

    for key, value in updates.items():
        setattr(faction, key, value)

    db.commit()
    db.refresh(faction)
    return faction

def delete_faction(db: Session, fact_id: int):
    faction = db.query(Faction).filter(Faction.factId == fact_id).first()
    if not faction:
        raise HTTPException(status_code=404, detail="Faction not found")
    db.delete(faction)
    db.commit()
    return {"message": "Faction deleted"}
