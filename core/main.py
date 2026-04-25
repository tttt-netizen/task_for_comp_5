from fastapi import FastAPI

from core.api import router as core_router

app = FastAPI(title="Core Service", version="1.0.0")
app.include_router(core_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
