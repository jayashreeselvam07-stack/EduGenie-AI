from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import logging

from app.config import config
from app.schemas import (
    AskRequest, AskResponse,
    ExplainRequest, ExplainResponse,
    QuizRequest, QuizResponse,
    SummarizeRequest, SummarizeResponse,
    LearningPathRequest, LearningPathResponse,
    APIErrorResponse
)
from app.services.gemini_service import (
    gemini_service,
    GeminiNotConfiguredError,
    GeminiAuthError,
    GeminiQuotaError,
    GeminiModelNotFoundError,
    GeminiCapacityError,
    GeminiNetworkError,
    GeminiServiceError
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edugenie.main")

app = FastAPI(
    title="EduGenie API",
    description="AI Learning Assistant for Students and Self-Learners",
    version="1.0.0"
)

# CORS middleware for development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR.parent / "templates"

# Ensure directories exist
STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# --- Global Exception Handlers for Accurate Error Reporting ---

@app.exception_handler(GeminiNotConfiguredError)
async def gemini_not_configured_handler(request: Request, exc: GeminiNotConfiguredError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": str(exc),
            "error_code": "GEMINI_KEY_MISSING",
            "configurable_help": "Please set GEMINI_API_KEY in your .env file."
        }
    )

@app.exception_handler(GeminiAuthError)
async def gemini_auth_error_handler(request: Request, exc: GeminiAuthError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "detail": str(exc),
            "error_code": "GEMINI_AUTH_FAILED",
            "configurable_help": "Check your GEMINI_API_KEY in .env. Get a valid key from https://aistudio.google.com/"
        }
    )

@app.exception_handler(GeminiQuotaError)
async def gemini_quota_error_handler(request: Request, exc: GeminiQuotaError):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": str(exc),
            "error_code": "GEMINI_QUOTA_EXCEEDED",
            "configurable_help": "Rate limit or quota exceeded. Please wait a moment before trying again."
        }
    )

@app.exception_handler(GeminiModelNotFoundError)
async def gemini_model_not_found_handler(request: Request, exc: GeminiModelNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": str(exc),
            "error_code": "GEMINI_MODEL_NOT_FOUND",
            "configurable_help": "Set GEMINI_MODEL=gemini-3.8-flash in your .env file."
        }
    )

@app.exception_handler(GeminiCapacityError)
async def gemini_capacity_error_handler(request: Request, exc: GeminiCapacityError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": str(exc),
            "error_code": "GEMINI_SERVER_HIGH_DEMAND",
            "configurable_help": "The Gemini model server is experiencing temporary high demand. Please retry your request in a few seconds."
        }
    )

@app.exception_handler(GeminiNetworkError)
async def gemini_network_error_handler(request: Request, exc: GeminiNetworkError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": str(exc),
            "error_code": "GEMINI_NETWORK_ERROR",
            "configurable_help": "Unable to reach Gemini API servers. Please check your internet connection."
        }
    )

@app.exception_handler(GeminiServiceError)
async def gemini_service_error_handler(request: Request, exc: GeminiServiceError):
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "detail": str(exc),
            "error_code": "GEMINI_SERVICE_ERROR",
            "configurable_help": "Ensure your API key and model parameters in .env are valid."
        }
    )

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def render_home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "gemini_configured": config.is_gemini_configured(),
            "model_name": config.GEMINI_MODEL
        }
    )

@app.get("/api/health")
@app.get("/api/config-check")
async def config_check():
    """Report configuration status without exposing sensitive key values or performing paid network calls."""
    is_conf = config.is_gemini_configured()
    return {
        "status": "healthy",
        "gemini_configured": is_conf,
        "key_present": bool(config.GEMINI_API_KEY),
        "key_status": config.get_key_mask(),
        "model": config.GEMINI_MODEL
    }

@app.post("/api/ask", response_model=AskResponse)
async def ask_edugenie_endpoint(payload: AskRequest):
    if len(payload.question.strip()) > config.MAX_INPUT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Input text exceeds maximum allowed limit of {config.MAX_INPUT_LENGTH} characters."
        )
    return gemini_service.ask_edugenie(question=payload.question.strip(), language=payload.language)

@app.post("/api/explain", response_model=ExplainResponse)
async def explain_concept_endpoint(payload: ExplainRequest):
    if len(payload.concept.strip()) > config.MAX_INPUT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Input text exceeds maximum allowed limit of {config.MAX_INPUT_LENGTH} characters."
        )
    return gemini_service.explain_concept(
        concept=payload.concept.strip(),
        level=payload.level,
        language=payload.language
    )

@app.post("/api/quiz", response_model=QuizResponse)
async def generate_quiz_endpoint(payload: QuizRequest):
    if len(payload.topic.strip()) > config.MAX_INPUT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Input text exceeds maximum allowed limit of {config.MAX_INPUT_LENGTH} characters."
        )
    return gemini_service.generate_quiz(topic=payload.topic.strip(), language=payload.language)

@app.post("/api/summarize", response_model=SummarizeResponse)
async def summarize_notes_endpoint(payload: SummarizeRequest):
    if len(payload.text.strip()) > config.MAX_INPUT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Input text exceeds maximum allowed limit of {config.MAX_INPUT_LENGTH} characters."
        )
    return gemini_service.summarize_notes(text=payload.text.strip(), language=payload.language)

@app.post("/api/learning-path", response_model=LearningPathResponse)
async def create_learning_path_endpoint(payload: LearningPathRequest):
    if len(payload.topic.strip()) > config.MAX_INPUT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Input text exceeds maximum allowed limit of {config.MAX_INPUT_LENGTH} characters."
        )
    return gemini_service.create_learning_path(topic=payload.topic.strip(), language=payload.language)
