from typing import List
from schemas import MessengerAccountBase, MessengerAccountCreate, MessengerAccountDisplay
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from database import db_messenger

router = APIRouter(
    prefix='/messenger',
    tags=['messenger']
)

# Read all users
@router.get('/{cochat_id}', response_model=List[MessengerAccountDisplay])
def get_all_accounts_by_cochat_id(cochat_id: str, db: Session = Depends(get_db)):
    return db_messenger.get_all_accounts_by_cochat_id(cochat_id, db)