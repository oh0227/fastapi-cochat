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
def login(cochat_id: str):
    # Google OAuth2 로그인 페이지로 리다이렉트
    return db_gmail.login(cochat_id)

@router.get("/auth/callback")
def auth_callback(code: str, state: str, db: Session = Depends(get_db)):
    return db_gmail.auth_callback(code, state, db)

# =========================
# Gmail Push Notification Webhook (Pub/Sub)
# =========================

@router.post("/push")
async def gmail_push(request: Request, db: Session = Depends(get_db)):
    return await db_gmail.gmail_push(request, db)