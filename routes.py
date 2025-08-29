
from fastapi import APIRouter, HTTPException
from models import PlanRequest, PlanResponse
from database import plans_collection, feedback_collection
from llm_client import generate_itinerary
from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1")

class TravelPlanRequest(BaseModel):
    location: str
    days: int
    preferences: str


def _to_response(doc) -> PlanResponse:
    return PlanResponse(
        id=str(doc["_id"]),
        destination=doc["destination"],
        start_date=doc.get("start_date"),
        end_date=doc.get("end_date"),
        preferences=doc.get("preferences"),
        travelers=doc.get("travelers"),
        plan_text=doc["plan_text"],
        created_at=doc["created_at"]
    )

@router.post("/plan", response_model=PlanResponse)
async def create_plan(req: PlanRequest):
    try:
        
        dates = f"{req.start_date or 'NA'} to {req.end_date or 'NA'}"
        plan_text = await generate_itinerary(req.destination, dates, req.travelers or 1, req.preferences or "")

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

@router.get("/plan/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str):
    doc = await plans_collection.find_one({"_id": ObjectId(plan_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _to_response(doc)

@router.get("/search")
async def search(destination: str):
    cursor = plans_collection.find({"destination": {"$regex": destination, "$options": "i"}}).sort("created_at", -1).limit(20)
    results = []
    async for doc in cursor:
        results.append({
            "id": str(doc["_id"]),
            "destination": doc["destination"],
            "created_at": doc["created_at"],
            "snippet": (doc["plan_text"][:250] + "...") if len(doc["plan_text"]) > 250 else doc["plan_text"]
        })
    return {"results": results}

@router.post("/feedback")
async def feedback(plan_id: str, rating: int = 5, comment: str = ""):
    doc = {"plan_id": plan_id, "rating": rating, "comment": comment, "created_at": datetime.utcnow()}
    await feedback_collection.insert_one(doc)
    return {"ok": True}


@router.post("/api/v1/plan")
async def plan_trip(request: TravelPlanRequest):
    return {
        "message": f"Planning {request.days} days trip in {request.location} with preferences {request.preferences}"
    }
