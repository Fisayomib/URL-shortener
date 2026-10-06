from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def home():
    return {"message": "URL shortener is running"}