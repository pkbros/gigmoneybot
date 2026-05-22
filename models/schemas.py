from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class User(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    display_name: Optional[str] = None
    college: Optional[str] = None
    created_at: Optional[datetime] = None

class Listing(BaseModel):
    id: Optional[UUID] = None
    telegram_id: int
    skill_text: str
    fee_text: Optional[str] = None # Made optional
    college: Optional[str] = None
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None

class SearchResult(BaseModel):
    username: Optional[str] = None
    display_name: Optional[str] = None
    skill_text: str
    fee_text: str # Changed from fee_inr
    similarity: float
