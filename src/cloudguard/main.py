from fastapi import FastAPI

app = FastAPI(
    title="CloudGuard API",
    description="Cloud infrastructure compliance and remediation platform",
    version="0.1.0",
)


@app.get("/api/v1/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "cloudguard-api",
        "version": "0.1.0",
    }