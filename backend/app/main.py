from fastapi import FastAPI

app = FastAPI(
    title="KubePilot API",
    description="The Developer Platform for Automated Deployments",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "Welcome to KubePilot 🚀"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "KubePilot API",
        "version": "1.0.0"
    }