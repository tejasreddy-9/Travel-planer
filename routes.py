from fastapi import APIRouter, HTTPException
from models import PlanRequest, PlanResponse, SuggestionRequest
from database import plans_collection, feedback_collection
from llm_client import generate_itinerary
from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel


router = APIRouter(prefix="/api/v1", tags=["Travel Planner"])

class SuggestionRequest(BaseModel):
    query: str


def _to_response(doc) -> PlanResponse:
    return PlanResponse(
        id=str(doc["_id"]),
        destination=doc["destination"],
        start_date=doc.get("start_date"),
        end_date=doc.get("end_date"),
        preferences=doc.get("preferences"),
        travelers=doc.get("travelers"),
        plan_text=doc["plan_text"],
        created_at=str(doc["created_at"])
    )


# --------------------
# Create Plan
# --------------------
@router.post("/plan", response_model=PlanResponse)
async def create_plan(req: PlanRequest):
    try:
        dates = f"{req.start_date or 'NA'} to {req.end_date or 'NA'}"
        plan_text = await generate_itinerary(
            req.destination, dates, req.travelers or 1, req.preferences or ""
        )

        doc = {
            "user_id": req.user_id,
            "destination": req.destination,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "preferences": req.preferences,
            "travelers": req.travelers,
            "plan_text": plan_text,
            "created_at": datetime.utcnow()
        }

        res = await plans_collection.insert_one(doc)
        doc["_id"] = res.inserted_id
        return _to_response(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------
# Get Plan
# --------------------
@router.get("/plan/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str):
    doc = await plans_collection.find_one({"_id": ObjectId(plan_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _to_response(doc)


# --------------------
# Suggestions
# --------------------




# --- Static Knowledge Base ---
INDIA_CAPITALS = {
    "delhi": ["India Gate", "Red Fort", "Qutub Minar", "Lotus Temple"],
    "mumbai": ["Gateway of India", "Marine Drive", "Elephanta Caves", "Juhu Beach"],
    "chennai": ["Marina Beach", "Kapaleeshwarar Temple", "Fort St. George", "Guindy National Park"],
    "kolkata": ["Victoria Memorial", "Howrah Bridge", "Dakshineswar Kali Temple", "Indian Museum"],
    "hyderabad": ["Charminar", "Golconda Fort", "Hussain Sagar Lake", "Ramoji Film City"],
    "bengaluru": ["Cubbon Park", "Bangalore Palace", "Lalbagh Botanical Garden", "ISKCON Temple"],
    "lucknow": ["Bara Imambara", "Chota Imambara", "Hazratganj Market", "Rumi Darwaza"]
}

INDIA_STATES = {
    "rajasthan": ["Jaipur (Pink City)", "Udaipur (City of Lakes)", "Jaisalmer Fort", "Mount Abu"],
    "kerala": ["Alleppey Backwaters", "Munnar", "Kochi", "Kovalam Beach"],
    "goa": ["Baga Beach", "Dudhsagar Waterfalls", "Fort Aguada", "Anjuna Beach"],
    "uttarakhand": ["Rishikesh", "Haridwar", "Nainital", "Jim Corbett National Park"],
    "tamil nadu": ["Madurai Meenakshi Temple", "Kanyakumari", "Ooty", "Rameswaram"],
    "karnataka": ["Mysore Palace", "Hampi", "Coorg", "Gokarna"],
    "punjab": ["Golden Temple", "Wagah Border", "Jallianwala Bagh", "Chandigarh Rock Garden"]
}

WORLD_TOURISM = {
    "paris": ["Eiffel Tower", "Louvre Museum", "Notre Dame Cathedral", "Seine River Cruise"],
    "new york": ["Statue of Liberty", "Times Square", "Central Park", "Empire State Building"],
    "london": ["Big Ben", "London Eye", "Tower of London", "Buckingham Palace"],
    "dubai": ["Burj Khalifa", "Palm Jumeirah", "Dubai Mall", "Desert Safari"],
    "rome": ["Colosseum", "Trevi Fountain", "Vatican City", "Pantheon"],
    "tokyo": ["Tokyo Tower", "Shinjuku", "Mount Fuji (day trip)", "Shibuya Crossing"],
    "sydney": ["Sydney Opera House", "Harbour Bridge", "Bondi Beach", "Blue Mountains"]
}


@router.post("/suggestions")
async def get_suggestions(request: SuggestionRequest):
    query = request.query.lower()

    # 1. Check in Indian Capitals
    for capital, places in INDIA_CAPITALS.items():
        if capital in query:
            return {"query": request.query, "suggestions": places}

    # 2. Check in Indian States
    for state, places in INDIA_STATES.items():
        if state in query:
            return {"query": request.query, "suggestions": places}

    # 3. Check in World Famous Tourist Spots
    for city, places in WORLD_TOURISM.items():
        if city in query:
            return {"query": request.query, "suggestions": places}

    # Default Response
    return {
        "query": request.query,
        "suggestions": [
            "Sorry, no direct match found.",
            "Try searching with a state, capital city, or world-famous destination."
        ]
    }


# --------------------
# Search Plans
# --------------------
@router.get("/search")
async def search(destination: str):
    cursor = plans_collection.find(
        {"destination": {"$regex": destination, "$options": "i"}}
    ).sort("created_at", -1).limit(20)

    results = []
    async for doc in cursor:
        results.append({
            "id": str(doc["_id"]),
            "destination": doc["destination"],
            "created_at": str(doc["created_at"]),
            "snippet": (doc["plan_text"][:250] + "...") if len(doc["plan_text"]) > 250 else doc["plan_text"]
        })
    return {"results": results}


# --------------------
# Feedback
# --------------------
@router.post("/feedback")
async def feedback(plan_id: str, rating: int = 5, comment: str = ""):
    doc = {
        "plan_id": plan_id,
        "rating": rating,
        "comment": comment,
        "created_at": datetime.utcnow()
    }
    await feedback_collection.insert_one(doc)
    return {"ok": True}
