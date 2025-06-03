import os
import json
import requests
from datetime import datetime

from fastapi.responses import RedirectResponse, JSONResponse, PlainTextResponse
from fastapi import HTTPException, Query
from sqlalchemy.orm import Session

from database.models import DbUser, DbMessengerAccount, DbMessage
from database.database import get_db
from fcm.fcm import send_fcm_push


LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "https://your-colab-server.com")
INSTAGRAM_VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN", "default_verify_token")


def generate_instagram_login_redirect(cochat_id: str):
    auth_url = (
        "https://www.instagram.com/oauth/authorize"
        "?enable_fb_login=0"
        "&force_authentication=1"
        "&client_id=1060904925933643"
        "&redirect_uri=https://fastapi-cochat.onrender.com/instagram/callback"
        "&response_type=code"
        "&scope=instagram_business_basic,instagram_business_manage_messages,"
        "instagram_business_manage_comments,instagram_business_content_publish,"
        "instagram_business_manage_insights"
        f"&state={cochat_id}"
    )
    return RedirectResponse(auth_url)


def handle_instagram_auth_callback(code: str, state: str, db: Session):
    cochat_id = state
    token_url = "https://api.instagram.com/oauth/access_token"

    data = {
        "client_id": "1060904925933643",
        "client_secret": os.getenv("INSTAGRAM_CLIENT_SECRET"),
        "grant_type": "authorization_code",
        "redirect_uri": "https://fastapi-cochat.onrender.com/instagram/callback",
        "code": code
    }

    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get access token")

    tokens = response.json()
    print("Instagram auth response:", tokens)  # 🔍 전체 응답 출력

    access_token = tokens["access_token"]
    user_id = tokens.get("user_id")

    user = db.query(DbUser).filter(DbUser.cochat_id == cochat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    messenger_account = db.query(DbMessengerAccount).filter(
        DbMessengerAccount.user_id == user.cochat_id,
        DbMessengerAccount.messenger == "instagram",
        DbMessengerAccount.messenger_user_id == str(user_id)
    ).first()

    if not messenger_account:
        messenger_account = DbMessengerAccount(
            user_id=user.cochat_id,
            messenger="instagram",
            messenger_user_id=str(user_id),
            access_token=access_token,
            timestamp=datetime.utcnow()
        )
        db.add(messenger_account)
    else:
        messenger_account.access_token = access_token
        messenger_account.timestamp = datetime.utcnow()

    db.commit()
    return JSONResponse({"msg": "Instagram login successful", "instagram_user_id": user_id})

def verify_instagram_webhook_token(
    hub_mode: str,
    hub_challenge: str,
    hub_verify_token: str
):
    if hub_mode == "subscribe" and hub_verify_token == INSTAGRAM_VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status_code=403, detail="Webhook verification failed")

def process_instagram_webhook(body: dict, db: Session):
    entry = body.get("entry", [])[0]
    changes = entry.get("changes", [])

    for change in changes:
        if change.get("field") == "conversations":
            message_data = change.get("value", {})
            sender_id = message_data.get("from")
            recipient_id = message_data.get("to")
            message_text = message_data.get("message", "")

            # 🔍 수신 메시지 출력
            print(f"📩 Instagram 메시지 수신:\nFrom: {sender_id}\nTo: {recipient_id}\nMessage: {message_text}")

            messenger_account = db.query(DbMessengerAccount).filter(
                DbMessengerAccount.messenger_user_id == recipient_id,
                DbMessengerAccount.messenger == "instagram"
            ).first()

            if not messenger_account:
                continue

            user = db.query(DbUser).filter(DbUser.cochat_id == messenger_account.user_id).first()
            if not user:
                continue

            category, summary, embedding_vector, recommended = "others", "", [], True
            try:
                resp = requests.post(
                    f"{LLM_SERVER_URL}/analyze_and_filter",
                    json={
                        "cochat_id": user.cochat_id,
                        "sender_id": sender_id,
                        "receiver_id": recipient_id,
                        "subject": None,
                        "content": message_text,
                        "preference_vector": user.preference_vector,
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    summary = data.get("summary", "")
                    category = data.get("category", "others")
                    embedding_vector = data.get("embedding_vector", [])
                    recommended = data.get("recommended", True)
            except Exception as e:
                print(f"⚠️ RAG 처리 실패: {e}")

            db_message = DbMessage(
                messenger="instagram",
                user_id=user.cochat_id,
                messenger_account_id=messenger_account.id,
                sender_id=sender_id,
                receiver_id=recipient_id,
                subject=None,
                content=message_text,
                category=category,
                embedding_vector=embedding_vector,
                timestamp=datetime.utcnow(),
            )
            db.add(db_message)

            if user.fcm_token:
                try:
                    send_fcm_push(
                        user.fcm_token,
                        title="인스타그램 메시지 도착",
                        body=summary or message_text[:50],
                        data={
                            "sender_id": sender_id,
                            "receiver_id": recipient_id,
                            "content": message_text,
                            "category": category,
                            "timestamp": datetime.utcnow().isoformat(),
                            "messenger": "instagram",
                            "recommended": json.dumps(recommended),
                        }
                    )
                except Exception as e:
                    print(f"⚠️ FCM 전송 실패: {e}")

    db.commit()
    return {"status": "ok"}