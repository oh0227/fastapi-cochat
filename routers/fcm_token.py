from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import DbUser

router = APIRouter(tags=['fcm'])

class FCMTokenRegister(BaseModel):
    cochat_id: str
    fcm_token: str

@router.post("/register-fcm-token")
def register_fcm_token(data: FCMTokenRegister, db: Session = Depends(get_db)):
    user = db.query(DbUser).filter(DbUser.cochat_id == data.cochat_id).first()
    if not user:
        return {"success": False, "message": "User not found"}
    user.fcm_token = data.fcm_token
    db.commit()
    return {"success": True}


