import os
import requests
import base64
import json
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
PUBSUB_TOPIC_NAME = os.getenv("PUBSUB_TOPIC_NAME")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPE = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.email"

router = APIRouter()

# 메모리 저장소(실서비스는 DB 사용)
user_tokens = {}

@router.get("/auth/login")
def login():
    # Google OAuth2 로그인 페이지로 리다이렉트
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={SCOPE}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    return RedirectResponse(auth_url)

@router.get("/auth/callback")
def auth_callback(code: str):
    # Authorization Code로 Access Token 교환
    token_url = "https://oauth2.googleapis.com/token"
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

    # (예시) 토큰을 메모리에 저장
    user_tokens[email] = access_token

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

@router.get("/gmail/messages")
def get_gmail_messages(email: str):
    # 저장된 토큰으로 Gmail API 호출
    access_token = user_tokens.get(email)
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    gmail_api = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(gmail_api, headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch messages")
    return resp.json()

# 4. 본문 추출 함수
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

@router.get("/gmail/latest_messages")
def get_gmail_latest_messages(email: str):
    # 저장된 토큰으로 Gmail API 호출
    access_token = user_tokens.get(email)
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # 1. 최신 메시지 1개만 가져오기
    gmail_api = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "maxResults": 1,
        "labelIds": "INBOX",
        "q": "",  # 필요시 쿼리 추가
    }
    resp = requests.get(gmail_api, headers=headers, params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch messages")
    messages = resp.json().get("messages", [])
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found")

    message_id = messages[0]["id"]

    # 2. 해당 메시지 상세 정보 조회 (본문 포함)
    detail_api = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
    detail_params = {"format": "full"}
    detail_resp = requests.get(detail_api, headers=headers, params=detail_params)
    if detail_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch message detail")
    message_detail = detail_resp.json()

    # 3. 제목 추출
    subject = None
    for header in message_detail.get("payload", {}).get("headers", []):
        if header["name"].lower() == "subject":
            subject = header["value"]
            break

    body = extract_body(message_detail.get("payload", {}))

    # 5. snippet(미리보기)도 함께 반환
    snippet = message_detail.get("snippet", "")

    return {
        "id": message_id,
        "subject": subject,
        "snippet": snippet,
        "body": body,
    }

# =========================
# Gmail Push Notification Webhook (Pub/Sub)
# =========================

# historyId를 메모리에 저장 (실서비스는 DB 사용)
last_history_id = None

@router.post("/gmail/push")
async def gmail_push(request: Request):
    try:
        body = await request.json()
    except Exception:
        # 바디가 비었거나 JSON이 아닐 때
        return {"status": "empty or invalid body"}
    # Pub/Sub 메시지에서 data 추출 및 디코딩
    message_data = body.get("message", {}).get("data")
    if not message_data:
        return {"status": "no data"}
    decoded = base64.urlsafe_b64decode(message_data + '==').decode("utf-8")
    payload = json.loads(decoded)
    email_address = payload["emailAddress"]
    history_id = payload["historyId"]

    # 사용자 토큰 가져오기
    access_token = user_tokens.get(email_address)
    if not access_token:
        return {"status": "user not authenticated"}

    # history.list로 새 메시지 조회
    global last_history_id
    if last_history_id is None:
        last_history_id = history_id
        return {"status": "initialized"}
    gmail_api = "https://gmail.googleapis.com/gmail/v1/users/me/history"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "startHistoryId": last_history_id,
        "historyTypes": "messageAdded"
    }
    resp = requests.get(gmail_api, headers=headers, params=params)
    last_history_id = history_id

    if resp.status_code != 200:
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
            subject = None
            for header in message_detail.get("payload", {}).get("headers", []):
                if header["name"].lower() == "subject":
                    subject = header["value"]
                    break
            body_text = extract_body(message_detail.get("payload", {}))
            snippet = message_detail.get("snippet", "")
            messages.append({
                "id": msg_id,
                "subject": subject,
                "snippet": snippet,
                "body": body_text,
            })

    return {"new_messages": messages}
