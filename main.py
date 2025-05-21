from fastapi import FastAPI
from routers import user
from routers import gmail
from routers import messenger
from database import models
from auth import authentication
from database.database import engine
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
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