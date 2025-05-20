import os
import requests
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("https://fastapi-cochat.onrender.com/auth/callback")
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
