
from fastapi import FastAPI
from routes import router
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Travel Planner")

app.include_router(router)

@app.get("/")
async def root():
    return {"message": "AI Travel Planner — POST /api/v1/plan to create a plan (use Postman)"}

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host=host, port=port, reload=True)
