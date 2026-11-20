from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.config import get_settings
from app import auth
from app.database import SessionLocal, init_db
from app.routes import analysis, model
from app.services.inference_service import ModelUnavailableError, model_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pneumoscope")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        auth.ensure_admin(db)
    try:
        model_service.bundle()  # load once at start-up
    except ModelUnavailableError as e:
        log.warning("%s", e)
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="PneumoScope API", version=__version__, lifespan=lifespan,
                  description="Pneumonia classification from chest X-rays. Educational research use only.")
    app.add_middleware(GZipMiddleware, minimum_size=2048)
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origin_list, allow_credentials=True,
                       allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type"])

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        return resp

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        msg = exc.errors()[0]["msg"] if exc.errors() else "Invalid request"
        return JSONResponse(status_code=422, content={"detail": msg})

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):
        log.exception("Unhandled error")
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    signed_in = [Depends(auth.current_user)]
    app.include_router(auth.router)
    app.include_router(analysis.router, dependencies=signed_in)
    app.include_router(model.router, dependencies=signed_in)

    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok", "model_available": model_service.status()["available"]}

    return app


app = create_app()
