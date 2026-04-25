from fastapi import FastAPI

from landings.api import router as landings_router

app = FastAPI(title="Landings Service", version="1.0.0")
app.include_router(landings_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
