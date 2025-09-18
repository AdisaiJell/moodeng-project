from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from controllers import faction_controller
from models.faction import Faction
from schemas.faction import FactionOut, FactionUpdate

from schemas.faction import FactionCreate

router = APIRouter(prefix="/faction", tags=["Faction"])

@router.post("/create")
async def create_faction_api(faction:FactionCreate, db: Session = Depends(get_db)):
    return faction_controller.create_faction(db, faction)

@router.get("/all")
async def get_factions_api(db: Session = Depends(get_db)):
    return faction_controller.get_all_factions(db)

@router.get("/factName")
def get_all_faction_names(db: Session = Depends(get_db)):
    results = db.query(Faction.factionName).distinct().all()
    return [row[0] for row in results if row[0] is not None]

@router.get("/get/{fact_id}", response_model=FactionOut)
def get_faction(fact_id: int, db: Session = Depends(get_db)):
    return faction_controller.get_faction_by_id(db, fact_id)

@router.put("/update/{fact_id}", response_model=FactionOut)
def update_faction_endpoint(
    fact_id: int,
    faction: FactionUpdate,
    db: Session = Depends(get_db),
):
    return faction_controller.update_faction(db, fact_id, faction)

@router.delete("/delete/{fact_id}")
def delete_faction(fact_id: int, db: Session = Depends(get_db)):
    return faction_controller.delete_faction(db, fact_id)
