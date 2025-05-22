from sqlalchemy.orm.session import Session
from schemas import MessageBase
from database.models import DbMessage
from fastapi import HTTPException, status
import datetime

# Create
def create_message(db: Session, request: MessageBase):
    new_message = DbMessage(
        user_id=request.user_id,
        messenger=request.messenger,
        sender_id=request.sender_id,
        receiver_id=request.receiver_id,
        content=request.content,
        category=request.category,
        timestamp=datetime.datetime.now()
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return new_message

# Read (Single)
def get_message_by_id(id: int, db: Session):
    message = db.query(DbMessage).filter(DbMessage.id == id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Message with id {id} not found'
        )
    return message

# Read (Multiple by User)
def get_messages_by_user(cochat_id: str, db: Session):
    messages = db.query(DbMessage).filter(
        DbMessage.user_id == cochat_id
    ).all()
    
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Messages for user {cochat_id} not found'
        )
    return messages

# Update
def update_message(id: int, request: MessageBase, db: Session):
    message = db.query(DbMessage).filter(DbMessage.id == id)
    if not message.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Message with id {id} not found'
        )
    
    update_data = request.dict(exclude_unset=True)
    update_data['timestamp'] = datetime.datetime.now()
    
    message.update(update_data)
    db.commit()
    return message.first()

# Delete
def delete_message(id: int, db: Session):
    message = db.query(DbMessage).filter(DbMessage.id == id)
    if not message.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Message with id {id} not found'
        )
    
    message.delete(synchronize_session=False)
    db.commit()
    return {"status": "success", "message": "Message deleted"}
