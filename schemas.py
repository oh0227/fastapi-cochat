from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# ===== 사용자 관련 =====

class UserBase(BaseModel):
    first_name: str
    last_name: str
    cochat_id: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    cochat_id: Optional[str] = None

class UserDisplay(UserBase):
    id: int
    class Config:
        orm_mode = True

class UserPreference(BaseModel):
    cochat_id: str
    preferences: List[str]

# ===== 메신저 연동 계정 관련 =====

class MessengerAccountBase(BaseModel):
    messenger: str                  # 예: 'gmail', 'kakao'
    messenger_user_id: str          # 예: gmail 주소
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    history_id: Optional[str] = None
    token_expiry: Optional[datetime] = None

class MessengerAccountCreate(MessengerAccountBase):
    pass

class MessengerAccountDisplay(MessengerAccountBase):
    id: int
    user_id: str
    timestamp: Optional[datetime] = None
    class Config:
        orm_mode = True

# ===== 메시지 관련 =====

class MessageBase(BaseModel):
    messenger: str
    sender_id: str
    receiver_id: str
    subject: str
    content: str
    embedding_vector: Optional[List[float]] = None  
    category: Optional[str] = None

class MessageCreate(MessageBase):
    pass

class MessageDisplay(MessageBase):
    id: int
    timestamp: Optional[datetime] = None
    class Config:
        orm_mode = True

# ===== 중첩 예시 (사용자 + 연동 계정) =====

class UserWithMessengerAccounts(UserDisplay):
    messengers: List[MessengerAccountDisplay] = []

# ===== FCM Token =====

class FCMTokenRegister(BaseModel):
    cochat_id: str
    fcm_token: str