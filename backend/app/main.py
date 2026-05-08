from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, engine
from app.routers.ai_gateway import router as ai_gateway_router
from app.routers.auth import router as auth_router
from app.routers.billing import router as billing_router
from app.routers.models import router as models_router
from app.routers.monitor import router as monitor_router
from app.routers.nodes import router as nodes_router
from app.routers.resources import router as resources_router
from app.routers.tasks import router as tasks_router
from app.utils.exceptions import APIError, AppException
from app.utils.responses import error_response

@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(APIError)
async def api_error_handler(_: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.message, exc.code),
    )


@app.exception_handler(AppException)
async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.message, exc.code),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(detail, exc.status_code),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_response(str(exc), 500),
    )


@app.get("/health")
def health() -> dict:
    return {"code": 0, "data": {"status": "ok"}, "message": "ok"}


app.include_router(auth_router)
app.include_router(models_router)
app.include_router(ai_gateway_router)
app.include_router(tasks_router)
app.include_router(monitor_router)
app.include_router(billing_router)
app.include_router(nodes_router)
app.include_router(resources_router)
