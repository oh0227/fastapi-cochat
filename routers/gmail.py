from fastapi import APIRouter, Request, Depends

from googleapiclient.discovery import build
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database.database import get_db
from database import db_gmail
from schemas import UserDisplay
from auth.oauth2 import get_current_user

load_dotenv()

router = APIRouter(
    prefix="/gmail",
    tags=['gmail']
)

@router.get("/auth/login")
def login(current_user: UserDisplay = Depends(get_current_user)):
    # Google OAuth2 로그인 페이지로 리다이렉트
    return db_gmail.login()

@router.get("/auth/callback")
def auth_callback(code: str, db: Session = Depends(get_db)):
    return db_gmail.auth_callback(code, db)

@router.get("/messages")
def get_gmail_messages(email: str, db: Session = Depends(get_db), current_user: UserDisplay = Depends(get_current_user)):
    """
    DB에서 해당 email(수신자)의 모든 메시지 목록을 반환
    """
    return db_gmail.get_gmail_messages(email, db)

@router.get("/latest_messages")
def get_gmail_latest_messages(email: str, db: Session = Depends(get_db), current_user: UserDisplay = Depends(get_current_user)):
    """
    DB에서 해당 email(수신자)의 가장 최근 메시지 1개를 반환
    """
    db_gmail.get_gmail_latest_messages(email, db)

# =========================
# Gmail Push Notification Webhook (Pub/Sub)
# =========================

@router.post("/push")
async def gmail_push(request: Request, db: Session = Depends(get_db)):
    db_gmail.gmail_push(request, db)