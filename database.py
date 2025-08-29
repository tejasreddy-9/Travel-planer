import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()  # 👈 this loads .env file

MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise RuntimeError("Set MONGODB_URI in .env")


client = MongoClient(MONGODB_URI)
db = client["travel_planner"]
plans_collection = db["plans"]
feedback_collection = db["feedback"]
