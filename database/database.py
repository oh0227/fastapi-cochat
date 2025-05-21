from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "postgresql://cochat:zMz6J5OAuYtExPJP71EFjtS1mJU7v1MM@dpg-d0mlg33e5dus738k8rq0-a.oregon-postgres.render.com/fastapi_cochat_db"

engine = create_engine(
  SQLALCHEMY_DATABASE_URL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()