from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.sql.sqltypes import Integer, String, Boolean 
from database.database import Base
from sqlalchemy import Column, DateTime

class DbUser(Base):
  __tablename__ = 'users'
  id = Column(Integer, primary_key=True, index=True)
  first_last = Column(String)
  first_name = Column(String)
  last_name = Column(String)
  email = Column(String)
  password = Column(String)
  timestamp = Column(DateTime)
