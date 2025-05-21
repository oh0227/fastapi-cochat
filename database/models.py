from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database.database import Base

class DbUser(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    cochat_id = Column(String, unique=True, index=True)  # CoChat 가입 ID
    first_last = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    password = Column(String)
    timestamp = Column(DateTime)
    # 여러 메신저 계정과 연결
    messengers = relationship("DbMessengerAccount", back_populates="user")
    messages = relationship("DbMessage", back_populates="user")

class DbMessengerAccount(Base):
    __tablename__ = 'messenger_accounts'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey('users.cochat_id'))  # CoChat 사용자와 연결
    messenger = Column(String, index=True)  # 예: 'gmail', 'kakao', 'slack'
    messenger_user_id = Column(String)      # 메신저 내 계정 식별자(예: Gmail 주소)
    access_token = Column(String)
    refresh_token = Column(String)
    history_id = Column(String)
    token_expiry = Column(DateTime)
    timestamp = Column(DateTime)
    user = relationship("DbUser", back_populates="messengers")
    messages = relationship("DbMessage", back_populates="messengers")
    __table_args__ = (UniqueConstraint('user_id', 'messenger', 'messenger_user_id', name='_user_messenger_uc'),)


class DbMessage(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey('users.cochat_id'))  # CoChat 사용자와 연결
    messenger = Column(String)
    sender_id = Column(String)
    receiver_id = Column(String, ForeignKey('messenger_accounts.messenger_user_id'))
    content = Column(String)
    category = Column(String)
    timestamp = Column(DateTime)
    user = relationship("DbUser", back_populates="messages")
    messengers = relationship("DbMessengerAccount", back_populates="messages")
