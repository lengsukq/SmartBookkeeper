from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class TransactionBase(BaseModel):
    amount: float
    vendor: str
    category: str
    transaction_date: datetime
    description: Optional[str] = None
    image_url: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    vendor: Optional[str] = None
    category: Optional[str] = None
    transaction_date: Optional[datetime] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

class TransactionInDB(TransactionBase):
    id: int
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[str] = None