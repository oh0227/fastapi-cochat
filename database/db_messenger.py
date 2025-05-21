from database.hash import Hash
from sqlalchemy.orm.session import Session
from schemas import MessengerAccountBase, MessengerAccountCreate, MessengerAccountDisplay
from database.models import DbMessengerAccount
from fastapi import HTTPException, status
import datetime

def get_all_accounts_by_cochat_id(cochat_id: str, db: Session):
  messengers = db.query(DbMessengerAccount).filter(DbMessengerAccount.user_id == cochat_id)
  if not messengers:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f'Messengers with cochat_id {cochat_id} not found')
  return db.query(DbMessengerAccount).filter(DbMessengerAccount.user_id == cochat_id)