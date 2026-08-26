# app/main.py
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes import (
    auth,
    file_system,
    form_builder,
    project_questions,
    project_sections,
    projects,
    question_groups,
)
from app.routes.project_question_dependencies import (
    router as project_question_dependencies_router,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Événements de démarrage et d'arrêt."""
    print(f"🚀 {settings.APP_NAME} démarré")
    yield
    print("👋 Arrêt du serveur")


app = FastAPI(
    title=settings.APP_NAME,
    description="API de gestion de formulaires et collecte de données sur le terrain.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ─── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Exception handlers : uniformise toutes les réponses d'erreur ─────────────
# Tout le monde retourne { success, message, data } — même les erreurs.


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail, "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    first = errors[0] if errors else {}
    field = " → ".join(str(l) for l in first.get("loc", []) if l != "body")
    msg = first.get("msg", "Données invalides")
    detail = f"{field} : {msg}" if field else msg

    return JSONResponse(
        status_code=422,
        content={"success": False, "message": detail, "data": None},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Erreur non gérée : %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Une erreur interne est survenue.",
            "data": None,
        },
    )


# ─── ROUTES DE BASE ───────────────────────────────────────────────────────────


@app.get("/", tags=["Health"])
async def root() -> dict:
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "healthy"}


# ─── ROUTES D'AUTHENTIFICATION ───────────────────────────────────────────────────────────
app.include_router(auth.router)


# ─── ROUTES DU FILE SYSTEM ───────────────────────────────────────────────────────────
app.include_router(file_system.router)


# ─── ROUTES DU FILE SYSTEM ───────────────────────────────────────────────────────────
app.include_router(file_system.router)


# ─── ROUTES DU FORM BUILDER ───────────────────────────────────────────────────────────
app.include_router(form_builder.router)


# ─── ROUTES DU QUESTION GROUPS ───────────────────────────────────────────────────────────
app.include_router(question_groups.router)


# ─── ROUTES DU PROJECT ───────────────────────────────────────────────────────────
app.include_router(projects.router)


# ─── ROUTES DU PROJECT SECTION ───────────────────────────────────────────────────────────
app.include_router(project_sections.router)


# ─── ROUTES DU PROJECT QUESTION ───────────────────────────────────────────────────────────
app.include_router(
    project_questions.router,
)


app.include_router(project_question_dependencies_router)
