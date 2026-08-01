from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.kubernetes import router as kubernetes_router

app = FastAPI(title="KubePilot API")

app.include_router(auth_router)
app.include_router(kubernetes_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to KubePilot 🚀"
    }