# models.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class PlanRequest(BaseModel):
    user_id: Optional[str]
    destination: str = Field(..., example="Paris, France")
    start_date: Optional[str] = Field(None, example="2025-09-10")
    end_date: Optional[str] = Field(None, example="2025-09-13")
    preferences: Optional[str] = Field("sightseeing, budget-friendly, food", example="beaches, budget, family-friendly")
    travelers: Optional[int] = Field(1, example=2)

class PlanDB(PlanRequest):
    plan_text: str
    created_at: datetime

class PlanResponse(BaseModel):
    id: str
    destination: str
    start_date: Optional[str]
    end_date: Optional[str]
    preferences: Optional[str]
    travelers: Optional[int]
    plan_text: str
    created_at: datetime
