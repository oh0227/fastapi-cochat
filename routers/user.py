from typing import List
from schemas import UserBase, UserCreate, UserUpdate, UserDisplay, UserPreference
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from database import db_user
from auth.oauth2 import get_current_user

router = APIRouter(
    prefix='/user',
    tags=['user']
)

# Create user
@router.post('/', response_model=UserDisplay)
def create_user(request: UserCreate, db: Session = Depends(get_db)):
    return db_user.create_user(db, request)

# Read all users
@router.get('/', response_model=List[UserDisplay])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: UserDisplay = Depends(get_current_user)
):
    return db_user.get_all_users(db)

# Read one user
@router.get('/{id}', response_model=UserDisplay)
def get_user(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserDisplay = Depends(get_current_user)
):
    return db_user.get_user(db, id)

# Update user
@router.put('/{id}', response_model=UserDisplay)
def update_user(
    id: int,
    request: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserDisplay = Depends(get_current_user)
):
    return db_user.update_user(db, id, request)


@router.post('/preferences')
def save_user_preferences(
    request: UserPreference,
    db: Session = Depends(get_db)
):
    return db_user.set_user_preferences(db, request.cochat_id, request.preferences)

# Delete user
@router.delete('/{id}', response_model=dict)
def delete_user(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserDisplay = Depends(get_current_user)
):
    return db_user.delete_user(db, id)
