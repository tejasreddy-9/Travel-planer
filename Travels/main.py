from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def teja():
    return {"Welcome to fastAPI"}