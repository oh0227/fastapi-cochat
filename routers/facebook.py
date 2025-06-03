from fastapi import APIRouter, Request, Response, status
import httpx
import os

router = APIRouter(
    prefix="/instagram",
    tags=['instagram']
)

VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN", "your_verify_token")  # 환경변수로 관리 추천

# =========================
# Instagram Webhook (GET: 검증, POST: 메시지 수신)
# =========================

# 테스트용 인메모리 저장소
instagram_messages = []


@router.get("/login")
async def instagram_login():
    INSTAGRAM_CLIENT_ID = os.getenv("INSTAGRAM_CLIENT_ID", "your_client_id")
    REDIRECT_URI = os.getenv("INSTAGRAM_REDIRECT_URI", "https://yourdomain.com/instagram/callback")
    INSTAGRAM_SCOPE = "user_profile,user_media"
    
    auth_url = (
        f"https://api.instagram.com/oauth/authorize"
        f"?client_id={INSTAGRAM_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={INSTAGRAM_SCOPE}"
        f"&response_type=code"
    )
    return {"login_url": auth_url}



@router.get("/callback")
async def instagram_callback(code: str):
    INSTAGRAM_CLIENT_ID = os.getenv("INSTAGRAM_CLIENT_ID", "your_client_id")
    INSTAGRAM_CLIENT_SECRET = os.getenv("INSTAGRAM_CLIENT_SECRET", "your_client_secret")
    REDIRECT_URI = os.getenv("INSTAGRAM_REDIRECT_URI", "https://yourdomain.com/instagram/callback")

    token_url = "https://api.instagram.com/oauth/access_token"
    payload = {
        "client_id": INSTAGRAM_CLIENT_ID,
        "client_secret": INSTAGRAM_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code": code
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=payload)
        if response.status_code == 200:
            token_data = response.json()
            print("Access Token Response:", token_data)
            return token_data
        else:
            print("Failed to get access token:", response.text)
            return Response(content="Token exchange failed", status_code=500)

@router.get("/webhook")
async def verify_webhook(request: Request):
    params = dict(request.query_params)
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return Response(content=params.get("hub.challenge"), media_type="text/plain")
    return Response(content="Verification failed", status_code=status.HTTP_403_FORBIDDEN)

@router.post("/webhook")
async def instagram_webhook(request: Request):
    data = await request.json()
    instagram_messages.append(data)  # DB 대신 임시 저장
    print("Received Instagram webhook event:", data)
    return {"status": "received"}

@router.get("/messages")
async def get_instagram_messages():
    return instagram_messages

@router.get("/latest_message")
async def get_latest_instagram_message():
    if instagram_messages:
        return instagram_messages[-1]
    return {"message": "No messages received yet."}
