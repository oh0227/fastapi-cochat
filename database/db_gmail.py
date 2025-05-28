import os
import requests
import base64
import json
from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import DbUser, DbMessengerAccount, DbMessage
from datetime import datetime
from fcm.fcm import send_fcm_push

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
PUBSUB_TOPIC_NAME = os.getenv("PUBSUB_TOPIC_NAME")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPE = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.email"

def extract_body(payload):
    if "body" in payload and "data" in payload["body"]:
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8")
    elif "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                data = part["body"]["data"]
                return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8")
            elif "parts" in part:
                result = extract_body(part)
                if result:
                    return result
    return None

def login(cochat_id: str):
    # Google OAuth2 로그인 페이지로 리다이렉트
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={SCOPE}"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={cochat_id}"   # ← CoChat User 식별자 전달
    )
    return RedirectResponse(auth_url)


def auth_callback(code: str, state: str, db: Session = Depends(get_db)):
    # Authorization Code로 Access Token 교환
    token_url = "https://oauth2.googleapis.com/token"
    cochat_id = state  # state에서 cochat_id 추출
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get token")
    tokens = response.json()
    access_token = tokens["access_token"]

    # 사용자 이메일 정보 가져오기
    userinfo_resp = requests.get(
        "https://www.googleapis.com/oauth2/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if userinfo_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get user info")
    userinfo = userinfo_resp.json()
    email = userinfo["email"]

    # DbUser에서 사용자 조회 user가 없을 시 예외 처리
    user = db.query(DbUser).filter(DbUser.cochat_id == cochat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Falied to find user")
    
    # DbMessengerAccount에 연동 정보 저장/업데이트
    messenger_account = db.query(DbMessengerAccount).filter(
        DbMessengerAccount.user_id == user.cochat_id,
        DbMessengerAccount.messenger == "gmail",
        DbMessengerAccount.messenger_user_id == email
    ).first()
    if not messenger_account:
        messenger_account = DbMessengerAccount(
            user_id=user.cochat_id,
            messenger="gmail",
            messenger_user_id=email,
            access_token=access_token,
            refresh_token=tokens.get("refresh_token"),
            token_expiry=datetime.utcfromtimestamp(tokens.get("expires_in", 0)) if tokens.get("expires_in") else None,
            timestamp=datetime.utcnow()
        )
        db.add(messenger_account)
    else:
        messenger_account.access_token = access_token
        messenger_account.refresh_token = tokens.get("refresh_token") or messenger_account.refresh_token
        messenger_account.token_expiry = datetime.utcfromtimestamp(tokens.get("expires_in", 0)) if tokens.get("expires_in") else messenger_account.token_expiry
        messenger_account.timestamp = datetime.utcnow()
    db.commit()
    db.refresh(messenger_account)


    try:
        # Credentials 객체 생성
        credentials = Credentials(
            token=access_token,
            scopes=['https://www.googleapis.com/auth/gmail.readonly']
        )
        
        # Gmail 서비스 초기화
        service = build('gmail', 'v1', credentials=credentials)
        
        # Watch 등록 요청
        watch_request = {
            'labelIds': ['INBOX'],
            'topicName': f'projects/{GOOGLE_PROJECT_ID}/topics/{PUBSUB_TOPIC_NAME}'
        }
        service.users().watch(userId='me', body=watch_request).execute()
        
    except Exception as e:
        print(f"Watch 등록 실패: {str(e)}")

    return JSONResponse({"msg": "Login successful", "email": email})


def get_gmail_messages(cochat_id: str, db: Session = Depends(get_db)):
    """
    DB에서 해당 email(수신자)의 모든 메시지 목록을 반환
    """
    messages = db.query(DbMessage)\
        .filter(DbMessage.receiver_id == cochat_id)\
        .order_by(DbMessage.timestamp.desc())\
        .all()
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found")
    # 필요한 필드만 반환
    return [
        {
            "id": msg.id,
            "messenger": msg.messenger,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "content": msg.content,
            "category": msg.category,
            "timestamp": msg.timestamp,
        }
        for msg in messages
    ]



def get_gmail_latest_messages(cochat_id: str, db: Session = Depends(get_db)):
    """
    DB에서 해당 email(수신자)의 가장 최근 메시지 1개를 반환
    """
    msg = db.query(DbMessage)\
        .filter(DbMessage.receiver_id == cochat_id)\
        .order_by(DbMessage.timestamp.desc())\
        .first()
    if not msg:
        raise HTTPException(status_code=404, detail="No messages found")
    return {
        "id": msg.id,
        "messenger": msg.messenger,
        "sender_id": msg.sender_id,
        "receiver_id": msg.receiver_id,
        "content": msg.content,
        "category": msg.category,
        "timestamp": msg.timestamp,
    }



def refresh_access_token(refresh_token: str):
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=401, detail="Failed to refresh token")
    

async def gmail_push(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        raw_body = await request.body()
    except Exception:
        return {"status": "empty or invalid body"}

    message_data = body.get("message", {}).get("data")
    if not message_data:
        print("No data field in Pub/Sub message")
        return {"status": "no data"}

    decoded = base64.b64decode(message_data + '==').decode("utf-8")
    payload = json.loads(decoded)

    email_address = payload["emailAddress"]
    history_id = payload["historyId"]

    messenger_account = db.query(DbMessengerAccount).filter(
        DbMessengerAccount.messenger == "gmail",
        DbMessengerAccount.messenger_user_id == email_address
    ).first()
    if not messenger_account:
        print(f"No messenger account for {email_address}")
        return {"status": "messenger account not found"}

    user = db.query(DbUser).filter(
        DbUser.cochat_id == messenger_account.user_id,
    ).first()
    if not user:
        print(f"No user for {messenger_account.messenger_user_id}")
        return {"status": "user account not found"}

    access_token = messenger_account.access_token

    # 토큰 유효성 검사
    token_check = requests.get(
        "https://www.googleapis.com/oauth2/v1/tokeninfo",
        params={"access_token": access_token}
    )

    if token_check.status_code != 200:
        print(f"Access token expired for {email_address}, refreshing...")
        try:
            token_data = refresh_access_token(messenger_account.refresh_token)
            access_token = token_data["access_token"]
            messenger_account.access_token = access_token
            if "expires_in" in token_data:
                messenger_account.token_expiry = datetime.utcnow()
            messenger_account.timestamp = datetime.utcnow()
            db.commit()
            print(f"Access token refreshed for {email_address}")
        except Exception as e:
            print(f"Token refresh failed: {e}")
            return {"status": "token refresh failed"}

    if not messenger_account.history_id:
        messenger_account.history_id = str(history_id)
        messenger_account.timestamp = datetime.utcnow()
        db.commit()
        print(f"Initialized history_id for {email_address}: {history_id}")
        return {"status": "initialized"}

    gmail_api = "https://gmail.googleapis.com/gmail/v1/users/me/history"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "startHistoryId": messenger_account.history_id,
        "historyTypes": "messageAdded"
    }
    resp = requests.get(gmail_api, headers=headers, params=params)
    messenger_account.history_id = str(history_id)
    db.commit()

    if resp.status_code != 200:
        print(f"Failed to fetch history for {email_address}: {resp.text}")
        return {"status": "failed to fetch history"}

    results = resp.json()
    messages = []
    for history in results.get('history', []):
        for msg in history.get('messagesAdded', []):
            msg_id = msg['message']['id']
            detail_api = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
            detail_params = {"format": "full"}
            detail_resp = requests.get(detail_api, headers=headers, params=detail_params)
            if detail_resp.status_code != 200:
                continue
            message_detail = detail_resp.json()

            label_ids = message_detail.get("labelIds", [])

            # 🔍 문제 1: DRAFT 필터링
            if "DRAFT" in label_ids:
                print("DRAFT 메시지는 무시")
                continue

            if "SENT" in label_ids and "INBOX" not in label_ids:
                print("내가 보낸 메일입니다 — 푸시 생략")
                continue

            # 🔍 문제 2: 중복 체크 by Gmail message_id
            existing = db.query(DbMessage).filter(
                DbMessage.gmail_message_id == msg_id
            ).first()
            if existing:
                print("이미 저장된 메일입니다, 중복 제거")
                continue

            headers_list = message_detail.get("payload", {}).get("headers", [])
            subject = sender = receiver = None
            for header in headers_list:
                name = header["name"].lower()
                if name == "subject":
                    subject = header["value"]
                elif name == "from":
                    sender = header["value"]
                elif name == "to":
                    receiver = header["value"]
            if receiver is None:
                receiver = email_address

            # 본문 파싱
            body_text = extract_body(message_detail.get("payload", {}))

            try:
                clean_json_content = json.dumps({"content": body_text}, ensure_ascii=False, indent=2)
            except TypeError as e:
                print(f"❗ JSON 직렬화 실패: {e}")

            # 🧠 RAG 처리 (외부 Colab API 호출)
            llm_url = request.app.state.llm_url  # 최신 ngrok URL
            print("현재 LLM URL:", llm_url)

            # 기본값 초기화
            summary = ""
            recommended = True  # 기본값은 true
            category = None
            embedding_vector = []

            if llm_url:
                try:
                    message_payload = {
                        "cochat_id": user.cochat_id,
                        "sender_id": sender,
                        "receiver_id": receiver,
                        "subject": subject,
                        "content": body_text,
                    }
                    print("Colab API 요청 데이터:", json.dumps(message_payload, indent=2, ensure_ascii=False))

                    api_url = f"{llm_url}/analyze_and_filter"
                    resp = requests.post(
                        api_url,
                        json=message_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=(10, 120)
                    )

                    if resp.status_code == 200:
                        try:
                            response_data = resp.json()
                            print("Colab API 응답 성공:", json.dumps(response_data, indent=2, ensure_ascii=False))
                            # 📌 Colab 응답에서 필드 추출
                            result = response_data.get("result", {})
                            recommended = result.get("recommended", True)  # 기본값은 True
                            category = result.get("category", "others")
                            embedding_vector = result.get("embedding_vector", [])
                            summary = result.get("summary", "")


                            if not recommended:
                                print("❌ Colab이 이 메시지를 추천하지 않았으므로 저장/푸시 생략")
                                continue

                        except json.JSONDecodeError as e:
                            print("❗ JSON 파싱 실패:", e)
                    else:
                        print(f"Colab LLM API 호출 실패: {resp.status_code} - {resp.text}")
                except Exception as e:
                    print(f"Colab LLM API 호출 중 에러: {str(e)}")
            else:
                print("⚠️ LLM(Colab) URL이 등록되어 있지 않습니다. 기본값 사용")

            # ✅ 추천된 경우에만 DB 저장 및 FCM 푸시
            db_message = DbMessage(
                gmail_message_id=msg_id,
                messenger="gmail",
                user_id=user.cochat_id,
                messenger_account_id=messenger_account.id,
                sender_id=sender,
                receiver_id=receiver,
                subject=subject,
                content=body_text,
                category=category,  # 현재 카테고리 없음
                embedding_vector=embedding_vector,  # 현재 벡터 없음
                timestamp=datetime.utcnow()
            )
            db.add(db_message)

            if user.fcm_token:
                try:
                    send_fcm_push(
                        user.fcm_token,
                        title=f"새 메일: {subject or '(제목 없음)'}",
                        body=summary or body_text[:50] or "새 메일이 도착했습니다."
                    )
                except Exception as e:
                    print(f"FCM 알림 전송 실패: {e}")
            else:
                print(f"User {user.cochat_id} has no FCM token.")


    db.commit()
    return {"new_messages": messages}