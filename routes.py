from fastapi import APIRouter, HTTPException
from models import PlanRequest, PlanResponse, SuggestionRequest, GroupTripRequest, BookingRequest
from database import plans_collection, feedback_collection
from llm_client import generate_itinerary
from datetime import datetime
from pydantic import BaseModel
from data import INDIA_CAPITALS, INDIA_STATES, WORLD_TOURISM

router = APIRouter(prefix="/api/v1", tags=["Travel Planner"])

# --------------------
# Helpers
# --------------------
def _to_response(doc) -> PlanResponse:
    return PlanResponse(
        id=doc["user_id"],
        destination=doc["destination"],
        start_date=doc.get("start_date"),
        end_date=doc.get("end_date"),
        preferences=doc.get("preferences"),
        travelers=doc.get("travelers"),
        plan_text=doc["plan_text"],
        created_at=str(doc["created_at"])
    )

def _find_destination(query: str):
    query = query.lower()
    if query in INDIA_CAPITALS:
        return INDIA_CAPITALS[query]
    if query in INDIA_STATES:
        return INDIA_STATES[query]
    if query in WORLD_TOURISM:
        return WORLD_TOURISM[query]
    return None

# --------------------
# Available Locations
# --------------------
@router.get("/locations")
async def get_locations():
    return {
        "indian_capitals": list(INDIA_CAPITALS.keys()),
        "indian_states": list(INDIA_STATES.keys()),
        "world_cities": list(WORLD_TOURISM.keys())
    }

# --------------------
# Create Plan
# --------------------
@router.post("/plan", response_model=PlanResponse)
async def create_plan(req: PlanRequest):
    if await plans_collection.find_one({"user_id": req.user_id}):
        raise HTTPException(status_code=400, detail="User ID already exists. Please choose a different ID.")
    if not req.start_point:
        raise HTTPException(status_code=400, detail="Start point (home city) is required")

    dates = f"{req.start_date or 'NA'} to {req.end_date or 'NA'}"
    core_itinerary = await generate_itinerary(req.destination, dates, req.travelers or 1, req.preferences or "")
    data = _find_destination(req.destination)
    if not data:
        raise HTTPException(status_code=404, detail="Destination not found")

    total_budget, members = req.budget or 0, req.num_of_members or 1
    per_person = total_budget // members if members > 0 else total_budget

    plan_text = f"""
    Starting Point: {req.start_point}
    Travel: Train/Flight/Bus from {req.start_point} → {req.destination}
    Stay: Recommended Hotels → {data['hotels']}
    Food: Suggested Restaurants → {data['restaurants']}
    Tourism: Must Visit Places → {data['tourism']}
    Itinerary Plan: {core_itinerary}
    Budget: Total = ₹{total_budget}, Members = {members}, Per Person = ₹{per_person}
    Return: {req.destination} → {req.start_point}
    """

    doc = {**req.dict(), "plan_text": plan_text, "created_at": datetime.utcnow()}
    res = await plans_collection.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _to_response(doc)

# --------------------
# Get Plan by user_id
# --------------------
@router.get("/plan/{user_id}", response_model=PlanResponse)
async def get_plan(user_id: str):
    doc = await plans_collection.find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _to_response(doc)

# --------------------
# Suggestions
# --------------------
@router.post("/suggestions")
async def get_suggestions(request: SuggestionRequest):
    data = _find_destination(request.query)
    if data:
        return {"query": request.query, "tourism_places": data["tourism"], "hotels": data["hotels"], "restaurants": data["restaurants"]}
    return {"query": request.query, "suggestions": ["Sorry, no direct match found.", "Try searching with a state, capital city, or world-famous destination."]}

# --------------------
# Search
# --------------------
@router.get("/search")
async def search(destination: str):
    cursor = plans_collection.find({"destination": {"$regex": destination, "$options": "i"}}).sort("created_at", -1).limit(20)
    results = [{"id": str(doc["_id"]), "destination": doc.get("destination", "Unknown"), "created_at": str(doc.get("created_at", "")), "snippet": (doc.get("plan_text", "")[:250] + "...") if len(doc.get("plan_text", "")) > 250 else doc.get("plan_text", "")} async for doc in cursor]

    if results:
        return {"results": results, "source": "mongodb"}

    data = _find_destination(destination)
    if data:
        return {"destination": destination, "tourism": data["tourism"], "hotels": data["hotels"], "source": "static"}
    raise HTTPException(status_code=404, detail="Destination not found")

# --------------------
# Feedback
# --------------------
@router.post("/feedback")
async def feedback(plan_id: str, rating: int = 5, comment: str = ""):
    await feedback_collection.insert_one({"plan_id": plan_id, "rating": rating, "comment": comment, "created_at": datetime.utcnow()})
    return {"ok": True}

# --------------------
# Group Trip Planner
# --------------------
@router.post("/group_trip")
async def group_trip(req: GroupTripRequest):
    data = _find_destination(req.destination)
    if not data:
        return {"error": "Destination not found"}

    per_person = req.total_budget // req.members
    travelers = [{"name": f"Traveler {i+1}", "age": None, "gender": "", "contact": "", "role": "Leader" if i == 0 else "Member"} for i in range(req.members)]

    return {
        "destination": req.destination.title(),
        "total_budget": req.total_budget,
        "members": req.members,
        "per_person_budget": per_person,
        "tourism_places": data["tourism"],
        "recommended_hotel": data["hotels"]["low_budget_hotels"][0],
        "recommended_restaurant": data["restaurants"]["restaurant_1"]["name"],
        "travelers": travelers
    }

# --------------------
# Create Group Trip
# --------------------
@router.post("/group-trip")
async def create_group_trip(req: GroupTripRequest):
    if await plans_collection.find_one({"trip_id": req.trip_id}):
        raise HTTPException(status_code=400, detail="Trip ID already exists. Please choose another.")

    doc = {**req.dict(), "created_at": datetime.utcnow()}
    await plans_collection.insert_one(doc)
    return {"message": "Group trip created successfully", "trip": doc}

# --------------------
# Book Trip
# --------------------
@router.post("/book")
async def book_trip(req: BookingRequest):
    data = _find_destination(req.destination)
    if not data:
        raise HTTPException(status_code=404, detail="Destination not found")

    if req.budget <= 15000:
        hotel = data["hotels"].get("low_budget_hotels", ["Default Budget Hotel"])[0]
        restaurant = list(data["restaurants"].values())[0]["name"]
    else:
        hotel = data["hotels"].get("high_budget_hotels", ["Default Luxury Hotel"])[0]
        restaurant = list(data["restaurants"].values())[1]["name"]

    details = {
        "train": "Train tickets booked: Rajdhani Express",
        "flight": "Flight booked: Air India AI-202",
        "bus": "Bus booked: VRL Volvo AC Sleeper"
    }

    return {
        "user_id": req.user_id,
        "destination": req.destination,
        "budget": req.budget,
        "transport_mode": req.transport_mode,
        "status": "Booking Confirmed",
        "hotel": hotel,
        "restaurant": restaurant,
        "details": [details.get(req.transport_mode, "Invalid transport mode"), f"Hotel booked: {hotel}", f"Restaurant reserved: {restaurant}"],
        "expense_breakdown": {"transport": f"₹{int(req.budget * 0.5)}", "hotel": f"₹{int(req.budget * 0.3)}", "food": f"₹{int(req.budget * 0.2)}"}
    }

# --------------------
# Update Booking
# --------------------
@router.put("/update_details")
async def update_details(req: BookingRequest):
    if not await plans_collection.find_one({"user_id": req.user_id}):
        raise HTTPException(status_code=404, detail="Booking not found")
    update_doc = {"destination": req.destination, "budget": req.budget, "transport_mode": req.transport_mode, "updated_at": datetime.utcnow()}
    await plans_collection.update_one({"user_id": req.user_id}, {"$set": update_doc})
    return {"message": "Booking details updated successfully", "updated_details": update_doc}
