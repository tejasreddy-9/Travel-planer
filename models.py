from pydantic import BaseModel
from typing import Optional

class PlanRequest(BaseModel):
    user_id: str
    destination: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    preferences: Optional[str] = None
    travelers: Optional[int] = 1

class PlanResponse(BaseModel):
    id: str
    destination: str
    start_date: Optional[str]
    end_date: Optional[str]
    preferences: Optional[str]
    travelers: Optional[int]
    plan_text: str
    created_at: str

class SuggestionRequest(BaseModel):
    query: str

class SuggestionResponse(BaseModel):
    suggestions: list[str]
