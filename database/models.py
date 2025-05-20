from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database.database import Base

class DbUser(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    first_last = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    timestamp = Column(DateTime)
    # 사용자와 연동된 메신저 계정들
    messengers = relationship("DbMessengerAccount", back_populates="user")

class DbMessengerAccount(Base):
    __tablename__ = 'messenger_accounts'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    messenger = Column(String, index=True)  # 예: 'gmail', 'kakao', 'slack'
    messenger_user_id = Column(String)      # 메신저 내 계정 식별자(예: gmail 주소)
    access_token = Column(String)
    refresh_token = Column(String)
    history_id = Column(String)
    token_expiry = Column(DateTime)
    # 추가로 필요하면 토큰 타입, scope 등도 저장 가능
    timestamp = Column(DateTime)
    # 사용자와의 관계
    user = relationship("DbUser", back_populates="messengers")
    # 한 사용자의 한 메신저 계정은 유일해야 함
    __table_args__ = (UniqueConstraint('user_id', 'messenger', 'messenger_user_id', name='_user_messenger_uc'),)

class DbMessage(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True, index=True)
    messenger = Column(String)
    sender_id = Column(String)
    receiver_id = Column(String)
    content = Column(String)
    category = Column(String)
    timestamp = Column(DateTime)
    # 필요하다면 메시지와 메신저 계정 연결도 가능
    # messenger_account_id = Column(Integer, ForeignKey('messenger_accounts.id'))
