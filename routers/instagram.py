# instagram_routes.py
import os
from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy.orm import Session

from database.database import get_db
from database.db_instagram import (
    generate_instagram_login_redirect,
    handle_instagram_auth_callback,
    verify_instagram_webhook_token,
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


@router.get("/webhook")
async def instagram_webhook_verify(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token")
):
    return verify_instagram_webhook_token(hub_mode, hub_challenge, hub_verify_token)

@router.post("/webhook")
async def instagram_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    return process_instagram_webhook(body, db)