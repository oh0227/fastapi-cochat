from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.database import get_db
from schemas import MessageBase, MessageCreate, MessageDisplay
from database import db_message

router = APIRouter(
    prefix='/message',
    tags=['message']
)

# Create
@router.post(
    '/create',
    response_model=MessageDisplay,
    status_code=status.HTTP_201_CREATED
)
def create_message(
    request: MessageCreate,  # 생성 전용 스키마 사용
    db: Session = Depends(get_db)
):
    return db_message.create_message(db, request)

# Read (Single)
@router.get(
    '/id/{id}',
    response_model=MessageDisplay,
    responses={404: {"description": "Message not found"}}
)
def get_message_by_id(
    id: int,
    db: Session = Depends(get_db)
):
    message = db_message.get_message_by_id(id, db)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message ID {id} not found"
        )
    return message

# Read (Multiple)
@router.get(
    '/{cochat_id}',
    response_model=List[MessageDisplay],
    responses={404: {"description": "No messages found"}}
)
def get_messages_by_user(
    cochat_id: str,
    db: Session = Depends(get_db)
):
    messages = db_message.get_messages_by_user(cochat_id, db)
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No messages for user {cochat_id}"
        )
    return messages

# Update
@router.put(
    '/update/{id}',
    response_model=MessageDisplay,
    responses={404: {"description": "Message not found"}}
)
def update_message(
    id: int,
    request: MessageBase,  # 업데이트용 기본 스키마
    db: Session = Depends(get_db)
):
    updated_message = db_message.update_message(id, request, db)
    if not updated_message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message ID {id} not found"
        )
    return updated_message

# Delete
@router.delete(
    '/delete/{id}',
    responses={
        200: {"description": "Successfully deleted"},
        404: {"description": "Message not found"}
    }
)
def delete_message(
    id: int,
    db: Session = Depends(get_db)
):
    result = db_message.delete_message(id, db)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message ID {id} not found"
        )
    return {"status": "success", "message": f"Message ID {id} deleted"}
