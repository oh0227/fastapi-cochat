from fastapi import FastAPI
from routers import user
from routers import gmail
from routers import messenger
from routers import message
from routers import fcm_token
from database import models
from auth import authentication
from database.database import engine
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()
app.state.llm_url = ""

app.include_router(fcm_token.router)
app.include_router(message.router)
app.include_router(messenger.router)
app.include_router(gmail.router)
app.include_router(authentication.router)
app.include_router(user.router)


models.Base.metadata.create_all(engine)

origins = [
  'http://localhost:3000',
  'https://fastapi-cochat.onrender.com'
]

app.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*']
)

@app.get("/get_llm_url")
def get_llm_url():
    return {"llm_url": app.state.llm_url}

@app.post("/set_llm_url")
def set_llm_url(data: dict):
    app.state.llm_url = data["url"]
    print(app.state.llm_url)
    return {"status": "ok"}

@app.post("/llm")
def call_llm(prompt: str):
    # llm_url을 사용해 Colab의 LLM에 요청
    import requests
    resp = requests.post(f"{app.state.llm_url}/generate", json={"prompt": prompt})
    return resp.json()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
