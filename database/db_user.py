from database.hash import Hash
from typing import List
from sqlalchemy.orm.session import Session
from schemas import UserBase, UserUpdate
from database.models import DbUser
from fastapi import HTTPException, status
import datetime

def create_user(db: Session, request: UserBase):
  new_user = DbUser(
    first_last = f"{request.first_name} {request.last_name}",
    first_name = request.first_name,
    last_name = request.last_name,
    cochat_id = request.cochat_id,
    password = Hash.bcrypt(request.password),
    timestamp = datetime.datetime.now()
  )
  db.add(new_user)
  db.commit()
  db.refresh(new_user)
  return new_user

def get_all_users(db: Session):
  return db.query(DbUser).all()

def get_user(db: Session, id: int):
  user = db.query(DbUser).filter(DbUser.id == id).first()
  if not user:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f'User with id {id} not found')
  return user 

def get_user_by_username(db: Session, username: str):
  user = db.query(DbUser).filter(DbUser.cochat_id == username).first()
  if not user:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f'User with username {username} not found')
  return user 

def update_user(db: Session, id: int, request: UserUpdate):
  user = db.query(DbUser).filter(DbUser.id == id)
  if not user:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f'User with id {id} not found')
  user.update({
    DbUser.first_last: f"{request.first_name} {request.last_name}",
    DbUser.first_name: request.first_name,
    DbUser.last_name: request.last_name,
    DbUser.cochat_id: request.cochat_id,
  })
  db.commit()
  return 'ok'


def delete_user(db: Session, id: int):
  user = db.query(DbUser).filter(DbUser.id == id).first()
  if not user:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f'User with id {id} not found')
  db.delete(user)
  db.commit()
  return 'ok'