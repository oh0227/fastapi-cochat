from database.hash import Hash
from typing import List
from sqlalchemy.orm.session import Session
from schemas import UserBase, UserUpdate
from database.models import DbUser
from fastapi import HTTPException, status, Request
import datetime
import requests
import os

NGROK_URL = os.getenv("NGROK_URL")

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


def set_user_preferences(request: Request, db: Session, cochat_id: str, preferences: List[str]):
    user = db.query(DbUser).filter(DbUser.cochat_id == cochat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 선호 항목을 문자열로 결합
    joined = ", ".join(preferences)

    # 외부 LLM API 호출 준비
    api_url = f"{NGROK_URL}/preference/create"  # 적절한 엔드포인트로 수정하세요
    message_payload = {"text": joined}

    try:
        resp = requests.post(
            api_url,
            json=message_payload,
            headers={"Content-Type": "application/json"},
            timeout=(10, 120)
        )
        resp.raise_for_status()
        data = resp.json()
        embedding = data.get("embedding")
        if not embedding:
            raise HTTPException(status_code=500, detail="No embedding returned from LLM")
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Embedding server error: {str(e)}")

    # DB에 벡터 저장
    user.preference_vector = embedding
    db.commit()

    return {"status": "success", "vector_length": len(embedding)}


def delete_user(db: Session, id: int):
  user = db.query(DbUser).filter(DbUser.id == id).first()
  if not user:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f'User with id {id} not found')
  db.delete(user)
  db.commit()
  return 'ok'