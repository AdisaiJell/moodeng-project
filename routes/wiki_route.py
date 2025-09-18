from typing import List
from fastapi import APIRouter, Depends
from requests import Session
from controllers.wiki_controller import delete_wiki, get_all_wiki, get_wiki_by_id, update_wiki
from database import get_db
from schemas.wiki import  WikiOut, WikiUpdate



router = APIRouter(prefix="/wiki", tags=["Wiki"])

@router.get("/all", response_model=List[WikiOut])
def list_wiki(db: Session = Depends(get_db)):
    return get_all_wiki(db)

@router.get("/byId/{wiki_id}", response_model=WikiOut, response_model_exclude_none=False)
def get_wiki(wiki_id: int, db: Session = Depends(get_db)):
    return get_wiki_by_id(db, wiki_id)


@router.put("/update/{wiki_id}", response_model=WikiOut)       
def update_wiki_endpoint(
    wiki_id: int,
    payload: WikiUpdate,
    db: Session = Depends(get_db)
):
    return update_wiki(db, wiki_id, payload)

@router.delete("/del/{wiki_id}")
def remove_wiki(wiki_id: int, db: Session = Depends(get_db)):
    return delete_wiki(db, wiki_id)