from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.database import get_db
from schemas import MessengerAccountBase, MessengerAccountCreate, MessengerAccountDisplay
from database import db_messenger

router = APIRouter(
    prefix='/messenger',
    tags=['messenger']
)

# Create
@router.post(
    '/create',
    response_model=MessengerAccountDisplay,
    status_code=status.HTTP_201_CREATED
)
def create_messenger_account(
    request: MessengerAccountCreate,  # Create 스키마 사용
    db: Session = Depends(get_db)
):
    return db_messenger.create_messenger(db, request)

# Read (Single)
@router.get(
    '/id/{id}',
    response_model=MessengerAccountDisplay,
    responses={404: {"description": "Not found"}}
)
def get_account_by_id(id: int, db: Session = Depends(get_db)):
    return db_messenger.get_account_by_id(id, db)

# Read (Multiple)
@router.get(
    '/cochat_id/{cochat_id}',
    response_model=List[MessengerAccountDisplay],
    responses={404: {"description": "Not found"}}
)
def get_accounts_by_cochat_id(cochat_id: str, db: Session = Depends(get_db)):
    return db_messenger.get_accounts_by_cochat_id(cochat_id, db)

# Update
@router.put(
    '/update/{id}',
    response_model=MessengerAccountDisplay,
    responses={404: {"description": "Not found"}}
)
def update_messenger_account(
    id: int,
    request: MessengerAccountBase,  # Base 스키마 사용
    db: Session = Depends(get_db)
):
    return db_messenger.update_account(id, request, db)

# Delete
@router.delete(
    '/delete/{id}',
    responses={
        200: {"description": "Successfully deleted"},
        404: {"description": "Not found"}
    }
)
def delete_messenger_account(id: int, db: Session = Depends(get_db)):
    return db_messenger.delete_account(id, db)
