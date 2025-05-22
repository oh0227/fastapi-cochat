from database.hash import Hash
from sqlalchemy.orm.session import Session
from schemas import MessengerAccountBase, MessengerAccountCreate, MessengerAccountDisplay
from database.models import DbMessengerAccount
from fastapi import HTTPException, status
import datetime

# Create
def create_messenger(db: Session, request: MessengerAccountBase):
    new_messenger = DbMessengerAccount(
        user_id=request.user_id,
        messenger=request.messenger,
        messenger_user_id=request.messenger_user_id,
        access_token=request.access_token,
        refresh_token=request.refresh_token,  # refresh_token으로 수정 권장
        history_id=request.history_id,
        token_expiry=request.token_expiry,
        timestamp=datetime.datetime.now()
    )
    db.add(new_messenger)
    db.commit()
    db.refresh(new_messenger)
    return new_messenger

# Read (Single)
def get_account_by_id(id: int, db: Session):
    account = db.query(DbMessengerAccount).filter(DbMessengerAccount.id == id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Account with id {id} not found'
        )
    return account

# Read (Multiple)
def get_accounts_by_cochat_id(cochat_id: str, db: Session):
    accounts = db.query(DbMessengerAccount).filter(
        DbMessengerAccount.user_id == cochat_id
    ).all()
    
    if not accounts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Accounts with cochat_id {cochat_id} not found'
        )
    return accounts

# Update
def update_account(id: int, request: MessengerAccountBase, db: Session):
    account = db.query(DbMessengerAccount).filter(DbMessengerAccount.id == id)
    if not account.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Account with id {id} not found'
        )
    
    update_data = request.dict(exclude_unset=True)
    update_data['timestamp'] = datetime.datetime.now()  # 업데이트 시간 갱신
    
    account.update(update_data)
    db.commit()
    return account.first()

# Delete
def delete_account(id: int, db: Session):
    account = db.query(DbMessengerAccount).filter(DbMessengerAccount.id == id)
    if not account.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Account with id {id} not found'
        )
    
    account.delete(synchronize_session=False)
    db.commit()
    return {"status": "success", "message": "Account deleted"}
