from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.datasets import router as datasets_router
from app.api.v1.imports import router as imports_router
from app.api.v1.overlap import router as overlap_router
from app.config.settings import settings

app = FastAPI(title="FinOps AI — F1 (fundação e importação)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(imports_router)
app.include_router(datasets_router)
app.include_router(overlap_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "phase": "F1"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
