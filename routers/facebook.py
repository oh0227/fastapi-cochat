from fastapi import APIRouter, Request, Response, status
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
