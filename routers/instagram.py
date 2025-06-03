# instagram_routes.py
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from database.database import get_db
from database.db_instagram import (
    generate_instagram_login_redirect,
    handle_instagram_auth_callback,
    process_instagram_webhook
)

router = APIRouter(
    prefix="/instagram",
    tags=["instagram"]
)


@router.get("/login")
def instagram_login(cochat_id: str):
    return generate_instagram_login_redirect(cochat_id)


@router.get("/callback")
def instagram_auth_callback(code: str, state: str, db: Session = Depends(get_db)):
    return handle_instagram_auth_callback(code, state, db)


@router.post("/webhook")
async def instagram_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    return process_instagram_webhook(body, db)