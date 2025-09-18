from fastapi import APIRouter, HTTPException
from models import PlanRequest, PlanResponse, SuggestionRequest, GroupTripRequest, BookingRequest
from database import plans_collection, feedback_collection
from llm_client import generate_itinerary
from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel
from data import INDIA_CAPITALS, INDIA_STATES, WORLD_TOURISM

router = APIRouter(prefix="/api/v1", tags=["Travel Planner"])

class SuggestionRequest(BaseModel):
    query: str


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

# --------------------
# Available Locations Endpoint
# --------------------
@router.get("/locations")
async def get_locations():
    """
    Returns all available locations where user can plan trips.
    Includes Indian Capitals, States, and World Cities.
    """
    return {
        "indian_capitals": list(INDIA_CAPITALS.keys()),
        "indian_states": list(INDIA_STATES.keys()),
        "world_cities": list(WORLD_TOURISM.keys())
    }

#---------------------------------------------------------------------------------------------------------------
# --------------------
# Create Plan with Full Journey + Budget Split
# --------------------
@router.post("/plan", response_model=PlanResponse)
async def create_plan(req: PlanRequest):
    try:
        # Check if user_id already exists
        existing = await plans_collection.find_one({"user_id": req.user_id})
        if existing:
            raise HTTPException(status_code=400, detail="User ID already exists. Please choose a different ID.")
        
        if not req.start_point:
            raise HTTPException(status_code=400, detail="Start point (home city) is required")

        # Prepare trip duration
        dates = f"{req.start_date or 'NA'} to {req.end_date or 'NA'}"

        # ---------------------------
        # Generate AI itinerary (visiting places only)
        # ---------------------------
        core_itinerary = await generate_itinerary(
            req.destination, dates, req.travelers or 1, req.preferences or ""
        )

        # ---------------------------
        # Find transport (mock logic for demo)
        # ---------------------------
        transport = f"Train/Flight/Bus from {req.start_point} → {req.destination}"

        # ---------------------------
        # Suggest hotels & restaurants
        # ---------------------------
        hotels = []
        restaurants = []
        tourism_spots = []

        if req.destination.lower() in INDIA_CAPITALS:
            hotels = INDIA_CAPITALS[req.destination.lower()]["hotels"]
            restaurants = INDIA_CAPITALS[req.destination.lower()]["restaurants"]
            tourism_spots = INDIA_CAPITALS[req.destination.lower()]["tourism"]

        elif req.destination.lower() in INDIA_STATES:
            hotels = INDIA_STATES[req.destination.lower()]["hotels"]
            restaurants = INDIA_STATES[req.destination.lower()]["restaurants"]
            tourism_spots = INDIA_STATES[req.destination.lower()]["tourism"]

        elif req.destination.lower() in WORLD_TOURISM:
            hotels = WORLD_TOURISM[req.destination.lower()]["hotels"]
            restaurants = WORLD_TOURISM[req.destination.lower()]["restaurants"]
            tourism_spots = WORLD_TOURISM[req.destination.lower()]["tourism"]

        # ---------------------------
        # Budget calculation
        # ---------------------------
        total_budget = req.budget or 0
        members = req.num_of_members or 1
        per_person_budget = total_budget // members if members > 0 else total_budget

        # ---------------------------
        # Build final trip plan
        # ---------------------------
        plan_text = f"""
        🏁 Starting Point: {req.start_point}

        🚉 Travel: {transport}

        🏨 Stay: Recommended Hotels → {hotels}

        🍴 Food: Suggested Restaurants → {restaurants}

        🏝 Tourism: Must Visit Places → {tourism_spots}

        📅 Itinerary Plan:
        {core_itinerary}

        💰 Budget:
        Total Budget = ₹{total_budget}
        Members = {members}
        Per Person = ₹{per_person_budget}

        🔄 Return: {req.destination} → {req.start_point}
        """

        # ---------------------------
        # Save to DB
        # ---------------------------
        doc = {
            "user_id": req.user_id,
            "start_point": req.start_point,
            "destination": req.destination,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "preferences": req.preferences,
            "travelers": req.travelers,
            "budget": total_budget,
            "num_of_members": members,
            "plan_text": plan_text,
            "created_at": datetime.utcnow()
        }

        res = await plans_collection.insert_one(doc)
        doc["_id"] = res.inserted_id
        return _to_response(doc)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#------------------------------------------------------------------------------------------------------------


# --------------------
# Get Plan by user_id (no ObjectId)
# --------------------
@router.get("/plan/{user_id}", response_model=PlanResponse)
async def get_plan(user_id: str):
    doc = await plans_collection.find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Plan not found for this user_id")
    return _to_response(doc)




#------------------------------------------------------------------------------------------------------------

@router.post("/suggestions")
async def get_suggestions(request: SuggestionRequest):
    query = request.query.lower()

    # 1. Check Indian Capitals
    for capital, data in INDIA_CAPITALS.items():
        if capital in query:
            return {"query": request.query, "tourism_places": data["tourism"], "hotels": data["hotels"], "restaurants":data["restaurants"]}

    # 2. Check Indian States
    for state, data in INDIA_STATES.items():
        if state in query:
            return {"query": request.query, "tourism_places": data["tourism"], "hotels": data["hotels"], "restaurants":data["restaurants"]}

    # 3. Check World Cities
    for city, data in WORLD_TOURISM.items():
        if city in query:
            return {"query": request.query, "tourism_places": data["tourism"], "hotels": data["hotels"], "restaurants":data["restaurants"]}

    # Default Response
    return {
        "query": request.query,
        "suggestions": [
            "Sorry, no direct match found.",
            "Try searching with a state, capital city, or world-famous destination."
        ]
    }

#------------------------------------------------------------------------------------------------------------

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
            "destination": doc.get("destination", "Unknown"),
            "created_at": str(doc.get("created_at", "")),
            "snippet": (doc.get("plan_text", "")[:250] + "...") if len(doc.get("plan_text", "")) > 250 else doc.get("plan_text", "")
        })

    if results:
        return {"results": results, "source": "mongodb"}

    # fallback: search in static datasets
    dest = destination.lower()
    if dest in INDIA_STATES:
        return {"destination": destination, "tourism": INDIA_STATES[dest]["tourism"], "hotels": INDIA_STATES[dest]["hotels"], "source": "static:INDIA_STATES"}
    elif dest in WORLD_TOURISM:
        return {"destination": destination, "tourism": WORLD_TOURISM[dest]["tourism"], "hotels": WORLD_TOURISM[dest]["hotels"], "source": "static:WORLD_TOURISM"}

    raise HTTPException(status_code=404, detail="Destination not found")


#------------------------------------------------------------------------------------------------------------

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

#------------------------------------------------------------------------------------------------------------

# --------------------
# Group Trip Planner
# --------------------

@router.post("/group_trip")
async def group_trip(req: GroupTripRequest):
    query = req.destination.lower()
    per_person_budget = req.total_budget // req.members

    # Auto-generate travelers if not passed
    travelers = []
    for i in range(req.members):
        travelers.append({
            "name": f"Traveler {i+1}",
            "age": None,
            "gender": "",
            "contact": "",
            "role": "Leader" if i == 0 else "Member"
        })

    # Search in Capitals
    for capital, data in INDIA_CAPITALS.items():
        if capital in query:
            return {
                "destination": capital.title(),
                "total_budget": req.total_budget,
                "members": req.members,
                "per_person_budget": per_person_budget,
                "tourism_places": data["tourism"],
                "recommended_hotel": data["hotels"]["low_budget_hotels"][0],
                "recommended_restaurant": data["restaurants"]["restaurant_1"]["name"],
                "travelers": travelers
            }

    # Search in States
    for state, data in INDIA_STATES.items():
        if state in query:
            return {
                "destination": state.title(),
                "total_budget": req.total_budget,
                "members": req.members,
                "per_person_budget": per_person_budget,
                "tourism_places": data["tourism"],
                "recommended_hotel": data["hotels"]["low_budget_hotels"][0],
                "recommended_restaurant": data["restaurants"]["restaurant_1"]["name"],
                "travelers": travelers
            }

    # Search in World Tourism
    for city, data in WORLD_TOURISM.items():
        if city in query:
            return {
                "destination": city.title(),
                "total_budget": req.total_budget,
                "members": req.members,
                "per_person_budget": per_person_budget,
                "tourism_places": data["tourism"],
                "recommended_hotel": data["hotels"]["low_budget_hotels"][0],
                "recommended_restaurant": data["restaurants"]["restaurant_1"]["name"],
                "travelers": travelers
            }

    return {"error": "Destination not found in our database."}


#------------------------------------------------------------------------------------------------------------

# --------------------
# Create Group Trip
# --------------------
@router.post("/group-trip")
async def create_group_trip(req: GroupTripRequest):
    try:
        # Check if trip already exists
        existing = await plans_collection.find_one({"trip_id": req.trip_id})
        if existing:
            raise HTTPException(status_code=400, detail="Trip ID already exists. Please choose another.")

        doc = {
            "trip_id": req.trip_id,
            "destination": req.destination,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "budget": req.budget,
            "transport_mode": req.transport_mode,
            "travelers": [traveler.dict() for traveler in req.travelers],
            "created_at": datetime.utcnow()
        }

        await plans_collection.insert_one(doc)
        return {"message": "Group trip created successfully ✅", "trip": doc}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#------------------------------------------------------------------------------------------------------------

# --------------------
# Booking Trip
# --------------------
@router.post("/book")
async def book_trip(req: BookingRequest):
    booking_summary = {
        "user_id": req.user_id,
        "destination": req.destination,
        "budget": req.budget,
        "transport_mode": req.transport_mode,
        "status": "Booking Confirmed ✅",
        "details": []
    }

    # --------------------------
    # Find hotels & restaurants for destination
    # --------------------------
    destination = req.destination.lower()
    hotels = {}
    restaurants = {}

    if destination in INDIA_CAPITALS:
        hotels = INDIA_CAPITALS[destination]["hotels"]
        restaurants = INDIA_CAPITALS[destination]["restaurants"]
    elif destination in INDIA_STATES:
        hotels = INDIA_STATES[destination]["hotels"]
        restaurants = INDIA_STATES[destination]["restaurants"]
    elif destination in WORLD_TOURISM:
        hotels = WORLD_TOURISM[destination]["hotels"]
        restaurants = WORLD_TOURISM[destination]["restaurants"]

    # --------------------------
    # Auto-select hotel & restaurant based on budget
    # --------------------------
    if req.budget <= 15000:  # low budget trip
        selected_hotel = hotels.get("low_budget_hotels", ["Default Budget Hotel"])[0]
        selected_restaurant = list(restaurants.values())[0]["name"] if restaurants else "Default Budget Restaurant"
    else:  # high budget trip
        selected_hotel = hotels.get("high_budget_hotels", ["Default Luxury Hotel"])[0]
        selected_restaurant = list(restaurants.values())[1]["name"] if restaurants else "Default Luxury Restaurant"

    booking_summary["hotel"] = selected_hotel
    booking_summary["restaurant"] = selected_restaurant

    # --------------------------
    # Transport booking with vehicle details
    # --------------------------
    if req.transport_mode == "train":
        booking_summary["details"].append("Train tickets booked: Rajdhani Express 🚆")
    elif req.transport_mode == "flight":
        booking_summary["details"].append("Flight booked: Air India AI-202 ✈️")
    elif req.transport_mode == "bus":
        booking_summary["details"].append("Bus booked: VRL Volvo AC Sleeper 🚌")
    else:
        booking_summary["details"].append("Invalid transport mode. Please choose train, flight, or bus.")

    # --------------------------
    # Add hotel & restaurant booking details
    # --------------------------
    booking_summary["details"].append(f"Hotel booked: {selected_hotel}")
    booking_summary["details"].append(f"Restaurant reserved: {selected_restaurant}")

    # --------------------------
    # Expense breakdown (50% transport, 30% hotel, 20% food)
    # --------------------------
    booking_summary["expense_breakdown"] = {
        "transport": f"₹{int(req.budget * 0.5)}",
        "hotel": f"₹{int(req.budget * 0.3)}",
        "food": f"₹{int(req.budget * 0.2)}"
    }

    return booking_summary