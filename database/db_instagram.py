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
from dotenv import load_dotenv

load_dotenv()

LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "https://fastapi-cochat-1.onrender.com")
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
        if change.get("field") != "messages":
            continue

        value = change.get("value", {})
        sender_id = value.get("sender", {}).get("id")
        receiver_id = value.get("recipient", {}).get("id")
        timestamp = value.get("timestamp")
        message_text = value.get("message", {}).get("text", "")

        print(f"📩 Instagram 메시지 수신:\nFrom: {sender_id}\nTo: {receiver_id}\nText: {message_text}\nTimestamp: {timestamp}")

        messenger_account = db.query(DbMessengerAccount).filter(
            DbMessengerAccount.messenger_user_id == receiver_id,
            DbMessengerAccount.messenger == "instagram"
        ).first()
        if not messenger_account:
            print(f"❗ Messenger account not found for receiver_id={receiver_id}")
            continue

        user = db.query(DbUser).filter(
            DbUser.cochat_id == messenger_account.user_id
        ).first()
        if not user:
            print(f"❗ User not found for cochat_id={messenger_account.user_id}")
            continue

        # 기본값 초기화
        summary = ""
        recommended = True
        category = "others"
        embedding_vector = []

        try:
            message_payload = {
                "cochat_id": user.cochat_id,
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "subject": None,
                "content": message_text,
                "preference_vector": user.preference_vector or []
            }

            # ✅ 요청 요약 출력
            try:
                preview_payload = dict(message_payload)
                pv = preview_payload.get("preference_vector")
                if isinstance(pv, list) and pv:
                    preview_payload["preference_vector"] = pv[:10] + (["..."] if len(pv) > 10 else [])
                else:
                    preview_payload["preference_vector"] = []

                print("📤 analyze_and_filter 요청 (요약):", json.dumps(preview_payload, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"요청 요약 출력 실패: {e}")

            api_url = f"{LLM_SERVER_URL}/analyze_and_filter"
            resp = requests.post(
                api_url,
                json=message_payload,
                headers={"Content-Type": "application/json"},
                timeout=(10, 120)
            )

            if resp.status_code == 200:
                try:
                    response_data = resp.json()

                    # ✅ 응답 요약 출력
                    try:
                        short_response_data = dict(response_data)
                        ev = short_response_data.get("embedding_vector")
                        if isinstance(ev, list) and ev:
                            short_response_data["embedding_vector"] = ev[:10] + (["..."] if len(ev) > 10 else [])
                        else:
                            short_response_data["embedding_vector"] = []
                        print("📥 analyze_and_filter 응답 (요약):", json.dumps(short_response_data, indent=2, ensure_ascii=False))
                    except Exception as e:
                        print(f"응답 요약 출력 실패: {e}")

                    recommended = response_data.get("recommended", True)
                    category = response_data.get("category", "others")
                    embedding_vector = response_data.get("embedding_vector", [])
                    summary = response_data.get("summary", "")
                except json.JSONDecodeError as e:
                    print("❗ JSON 파싱 실패:", e)
            else:
                print(f"analyze_and_filter API 호출 실패: {resp.status_code} - {resp.text}")

        except Exception as e:
            print(f"❗ analyze_and_filter 호출 중 에러: {e}")

        # DB 저장
        db_message = DbMessage(
            messenger="instagram",
            user_id=user.cochat_id,
            messenger_account_id=messenger_account.id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            subject=None,
            content=message_text,
            category=category,
            embedding_vector=embedding_vector,
            timestamp=datetime.utcnow()
        )
        db.add(db_message)

        # FCM 푸시 전송
        if user.fcm_token:
            try:
                send_fcm_push(
                    user.fcm_token,
                    title="인스타그램 메시지 도착",
                    body=summary or message_text[:50],
                    data={
                        "sender_id": sender_id,
                        "receiver_id": receiver_id,
                        "content": message_text,
                        "category": category,
                        "recommended": json.dumps(recommended),
                        "timestamp": datetime.utcnow().isoformat(),
                        "messenger": "instagram",
                    }
                )
            except Exception as e:
                print(f"⚠️ FCM 푸시 실패: {e}")

    db.commit()
    return {"status": "ok"}