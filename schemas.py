from pydantic import BaseModel
from typing import List

class UserBase(BaseModel):
  first_name: str
  last_name: str
  email: str
  password: str

class UserUpdate(BaseModel):
  first_name: str
  last_name: str
  email: str

class UserDisplay(BaseModel):
  id: int
  first_name: str
  last_name: str
  email: str
  class Config():
    orm_mode = True