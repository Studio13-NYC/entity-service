from fastapi import FastAPI
from app.routes import health, extract

app = FastAPI(title="NER Services")

app.include_router(health.router)
app.include_router(extract.router)
