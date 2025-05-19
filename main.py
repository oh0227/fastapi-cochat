from fastapi import FastAPI
from routers import user
from auth import authentication
from database import models
from database.database import engine
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.include_router(authentication.router)
app.include_router(user.router)

models.Base.metadata.create_all(engine)

origins = [
  'http://localhost:3000'
]

app.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*']
)