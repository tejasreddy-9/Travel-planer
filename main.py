from fastapi import FastAPI
from routes import router  # ✅ import router from routes.py

app = FastAPI(title="Travel Planner API")

# ✅ include the router
app.include_router(router)

@app.get("/")
async def root():
    return {"message": "Travel Planner API is running!"}
