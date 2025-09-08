from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = "mongodb+srv://tejasreddyis9999:lVZEvYKJNmlZ5NMy@cluster0.gsgmxva.mongodb.net/?retryWrites=true&w=majority"
client = AsyncIOMotorClient(MONGO_URI)

db = client["travel_planner"]
plans_collection = db["plans"]
feedback_collection = db["feedback"]