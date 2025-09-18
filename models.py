from pydantic import BaseModel
from typing import Optional, List

class PlanRequest(BaseModel):
    user_id: str
    start_point:Optional[str] = None
    destination: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    preferences: Optional[str] = None
    budget: int
    num_of_members:int
<<<<<<< HEAD
=======
    start_point:Optional[str] = None
>>>>>>> a77d7f7c21daf073a98f31736dda19d3dc5cb611
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
<<<<<<< HEAD
    user_id: str
    destination: str
    dates: str
    transport_mode: str   # train / flight / bus
    members: int          # total number of members
    total_budget: int     # total budget for the trip
    travelers: List[Traveler]
=======
    trip_id: str
    destination: str
    start_date: str
    end_date: str
    travelers: List[Traveler]
    budget: int
    transport_mode: str   # train / flight / bus
>>>>>>> a77d7f7c21daf073a98f31736dda19d3dc5cb611

class BookingRequest(BaseModel):
    user_id: str
    destination: str
    budget: int
    transport_mode: str   # train / flight / bus


class SuggestionRequest(BaseModel):
    query: str

class SuggestionResponse(BaseModel):
    suggestions: list[str]
