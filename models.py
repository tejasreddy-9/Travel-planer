from pydantic import BaseModel
from typing import Optional, List

class PlanRequest(BaseModel):
    user_id: str
    destination: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    preferences: Optional[str] = None
    budget: int
    num_of_members:int
    start_point:Optional[str] = None
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
    
class Traveler(BaseModel):
    name: str
    age: int
    gender: str
    contact: str
    role: str = "member"   # "leader" or "member"

class GroupTripRequest(BaseModel):
    trip_id: str
    destination: str
    start_date: str
    end_date: str
    travelers: List[Traveler]
    budget: int
    transport_mode: str   # train / flight / bus

class BookingRequest(BaseModel):
    user_id: str
    destination: str
    budget: int
    transport_mode: str   # train / flight / bus


class SuggestionRequest(BaseModel):
    query: str

class SuggestionResponse(BaseModel):
    suggestions: list[str]
