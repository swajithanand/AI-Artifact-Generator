# main.py - FINAL, CLEAN, PRODUCTION-READY VERSION

import os
import re
import logging
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from contextlib import asynccontextmanager

from models import ArtifactRequest, ArtifactResponse, StructuredArtifact
from strategies import build_provider, ProviderAuthError, ProviderRateLimitError
from prompts import build_prompt, UnsupportedArtifactTypeError, MissingArtifactInputError
from database import create_db_and_tables, get_session, Artifact

# --- INITIALIZATION AND CONFIGURATION ---

# Load environment variables (will load local .env or cloud vars)
load_dotenv()

# Setup logging. INFO level on purpose: request headers (which can carry user
# API keys) must never end up in logs.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- LIFESPAN EVENT HANDLER (Modern FastAPI Startup) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    The database table creation is handled here to ensure it runs only ONCE.
    """
    # 1. CREATE DB TABLES on startup
    try:
        # NOTE: This is the ONLY place create_db_and_tables() is called.
        create_db_and_tables() 
        logger.info("Database tables ensured to exist (via lifespan event).")
    except Exception as e:
        logger.error(f"FATAL DB ERROR: Could not ensure DB tables exist on startup: {str(e)}", exc_info=True)
        
    yield
    # 2. SHUTDOWN LOGIC
    logger.info("Application shutdown complete.")

# --- FASTAPI APPLICATION DEFINITION ---
# The application object is defined ONCE with the lifespan handler.
app = FastAPI(title="AI Artifact Generator Backend", lifespan=lifespan) 

# CORS Configuration
origins = [
    "https://ai-artifact-generator.vercel.app", # Vercel public production domain
    "https://ai-artifact-generator-swajiths-projects.vercel.app", # Vercel team alias
    "http://localhost:3000",   # Local Frontend
    "http://127.0.0.1:3000",   # Local Frontend (Alternate)
    #"http://localhost:8000",   # Local Backend
    #"http://127.0.0.1:8000",   # Local Backend (Alternate)
    #"*" # Final fallback for Cloud Run ingress testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- VALIDATION ERROR HANDLING ---
# An artifact_type outside the schema is rejected by pydantic before reaching
# the route, so translate that specific case into the friendly message rather
# than leaking a raw schema error to the UI.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    for error in exc.errors():
        if "artifact_type" in error.get("loc", ()):
            return JSONResponse(
                status_code=400,
                content={"detail": "Unsupported artifact type. Please select Epic, Feature, or User Story."},
            )
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})


# --- PERSISTENCE SERVICE (NO CHANGE) ---
class PersistenceService:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session

    def save_artifact(self, artifact_type: str, structured_artifact: StructuredArtifact) -> Artifact:
        db_artifact = Artifact(
            type=artifact_type,
            title=structured_artifact.title,
            artifact_data=structured_artifact.model_dump(),
        )
        self.session.add(db_artifact)
        self.session.commit()
        self.session.refresh(db_artifact)
        return db_artifact
    
    def get_history(self, limit: int = 5):
        statement = select(Artifact).order_by(Artifact.created_at.desc()).limit(limit)
        results = self.session.exec(statement).all()
        return results

# --- PARSING LOGIC ---
# Kept in sync with the templates in prompts.py: each artifact type emits its
# own set of "## " sections, so parsing is section-driven rather than one big
# regex per artifact.

_SECTION_RE = re.compile(r"^##+\s*(.+?)\s*:?\s*$", re.MULTILINE)
_TITLE_RE = re.compile(r"^#(?!#)\s*(.+?)\s*$", re.MULTILINE)
_TITLE_PREFIX_RE = re.compile(r"^(?:epic|feature|user\s*story|bug)?\s*title\s*:\s*", re.IGNORECASE)
_BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")


def _normalise_heading(heading: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", heading.lower()).strip()


def _split_sections(raw_output: str) -> dict:
    """Splits markdown '## Heading' blocks into {normalised heading: body}."""
    sections = {}
    matches = list(_SECTION_RE.finditer(raw_output))
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw_output)
        sections[_normalise_heading(match.group(1))] = raw_output[start:end].strip()
    return sections


def _section(sections: dict, *candidates: str) -> str:
    """Looks up a section by any of several heading spellings, exact then partial."""
    keys = [_normalise_heading(c) for c in candidates]
    for key in keys:
        if key in sections:
            return sections[key]
    for key in keys:
        for heading, body in sections.items():
            if key and key in heading:
                return body
    return ""


def _bullets(text: str) -> list:
    """
    Extracts list items. Handles '-', '*' and numbered bullets, and falls back to
    blank-line separated blocks so multi-line Given/When/Then criteria survive.
    """
    if not text.strip():
        return []

    items, current = [], []
    for line in text.splitlines():
        if _BULLET_RE.match(line):
            if current:
                items.append("\n".join(current).strip())
            current = [_BULLET_RE.sub("", line).strip()]
        elif current and line.strip():
            current.append(line.strip())
        elif current:
            items.append("\n".join(current).strip())
            current = []
    if current:
        items.append("\n".join(current).strip())

    if not items:
        items = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]

    return [item for item in items if item]


def _extract_title(raw_output: str, artifact_type: str) -> str:
    match = _TITLE_RE.search(raw_output)
    title = match.group(1).strip() if match else raw_output.strip().split("\n")[0].strip()
    title = _TITLE_PREFIX_RE.sub("", title).strip().strip("#").strip()
    return title or f"Generated {artifact_type}"


def parse_raw_ai_output(artifact_type: str, raw_output: str) -> StructuredArtifact:
    """Parses raw text into a structured Pydantic model with safe checks."""

    title = _extract_title(raw_output, artifact_type)
    sections = _split_sections(raw_output)

    if artifact_type == "User Story":
        user_story_text = _section(sections, "User Story")
        description = _section(sections, "Description")
        acceptance_criteria = _bullets(_section(sections, "Acceptance Criteria"))
        return StructuredArtifact(
            title=title,
            description=description or None,
            userStoryText=user_story_text,
            acceptanceCriteria=acceptance_criteria,
            raw_output=raw_output,
        )

    elif artifact_type == "Epic":
        pitch = _section(sections, "Elevator Pitch")
        outcomes = _section(sections, "Business Outcomes")
        indicators = _section(sections, "Leading Indicators")
        summary = _section(sections, "Epic Summary")
        full_description = (
            f"## Elevator Pitch\n{pitch}\n\n"
            f"## Business Outcomes\n{outcomes}\n\n"
            f"## Epic Summary\n{summary}"
        )
        return StructuredArtifact(
            title=title,
            description=full_description,
            keyFeatures=_bullets(indicators) or None,
            raw_output=raw_output,
        )

    elif artifact_type == "Feature":
        benefit = _section(sections, "Feature Benefit Statement")
        description = _section(sections, "Description")
        outcome = _section(sections, "Business User Outcome", "Business Outcome", "User Outcome")
        acceptance_criteria = _bullets(_section(sections, "Acceptance Criteria"))
        full_description = (
            f"## Feature Benefit Statement\n{benefit}\n\n"
            f"## Description\n{description}\n\n"
            f"## Business / User Outcome\n{outcome}"
        )
        return StructuredArtifact(
            title=title,
            description=full_description,
            acceptanceCriteria=acceptance_criteria,
            raw_output=raw_output,
        )

    elif artifact_type == "Bug":
        title_bug_match = re.search(r"Title:(.*?)(?=\n|$)", raw_output)
        description_bug_match = re.search(r"Description:(.*?)(?=Steps to Reproduce:|$)", raw_output, re.DOTALL)
        steps_bug_match = re.search(r"Steps to Reproduce:(.*?)(?=Expected Result:|$)", raw_output, re.DOTALL)
        bug_title = title_bug_match.group(1).strip() if title_bug_match else title
        bug_description = description_bug_match.group(1).strip() if description_bug_match else ""
        bug_steps = steps_bug_match.group(1).strip() if steps_bug_match else ""
        full_bug_description = f"## Description\n{bug_description}\n\n## Steps to Reproduce\n{bug_steps}"
        return StructuredArtifact(title=bug_title, description=full_bug_description, raw_output=raw_output)

    return StructuredArtifact(title=title, raw_output=raw_output)


# --- ROUTES ---
# Health check route. Deliberately does NOT touch the database: this is the
# platform health check, and a paused database must not cause restart loops.
@app.get("/")
def health_check():
    return {"status": "ok", "message": "AI Artifact Generator API is running"}


# Diagnostic endpoint: reports whether the database is actually reachable.
@app.get("/health/db")
def health_db(session: Session = Depends(get_session)):
    from sqlalchemy import text
    try:
        session.exec(text("SELECT 1"))
        return {"database": "ok"}
    except Exception as e:
        logger.error("Database health check failed", exc_info=True)
        return {
            "database": "unreachable",
            "hint": "If this is a free Supabase project it may be paused after inactivity — restore it in the Supabase dashboard.",
            "error_type": type(e).__name__,
        }

# History endpoint
@app.get("/history")
def get_artifact_history(persistence_service: PersistenceService = Depends()):
    try:
        history = persistence_service.get_history()
        return {"status": "success", "data": history}
    except Exception as e:
        logger.error(f"Error fetching artifact history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch artifact history")

# Key validation route — lets the frontend "Test connection" button verify a
# user-supplied key with a cheap provider call. The key is used in memory only.
@app.post("/validate-key")
def validate_key_route(
    x_llm_provider: Optional[str] = Header(default=None),
    x_llm_model: Optional[str] = Header(default=None),
    x_llm_key: Optional[str] = Header(default=None),
):
    if not x_llm_key:
        raise HTTPException(status_code=400, detail="No API key provided.")
    provider = build_provider(x_llm_provider, x_llm_model, x_llm_key)
    try:
        provider.validate()
    except ProviderAuthError:
        raise HTTPException(status_code=401, detail="The provider rejected this API key.")
    except ProviderRateLimitError:
        raise HTTPException(status_code=429, detail="This key is currently rate-limited by the provider.")
    except Exception:
        logger.error("Key validation failed for provider %s", provider.provider_id, exc_info=True)
        raise HTTPException(status_code=502, detail="Could not reach the provider to test the key. Check the model name and try again.")
    return {"status": "ok", "provider": provider.provider_id, "model": provider.model}


# Main artifact generation route
@app.post("/generate-artifact", response_model=ArtifactResponse)
async def generate_artifact_route(
    request: ArtifactRequest,
    persistence_service: PersistenceService = Depends(),
    x_llm_provider: Optional[str] = Header(default=None),
    x_llm_model: Optional[str] = Header(default=None),
    x_llm_key: Optional[str] = Header(default=None),
):
    provider = build_provider(x_llm_provider, x_llm_model, x_llm_key)

    # Validate inputs and prompt routing BEFORE calling the LLM, so a bad
    # request fails fast with a clear message instead of burning a paid call.
    try:
        build_prompt(
            artifact_type=request.artifact_type,
            business_use_case=request.business_use_case,
            persona=request.persona,
            technical_info=request.technical_info,
        )
    except (UnsupportedArtifactTypeError, MissingArtifactInputError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    logger.info("Generating %s via %s", request.artifact_type, provider.provider_id)

    try:
        raw_ai_output = provider.generate(request)
    except (UnsupportedArtifactTypeError, MissingArtifactInputError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ProviderAuthError:
        raise HTTPException(status_code=401, detail="Your API key was rejected by the provider. Check it in Settings (gear icon).")
    except ProviderRateLimitError:
        raise HTTPException(status_code=429, detail="Your API key hit the provider's rate limit. Try again in a moment.")
    except Exception:
        # Never echo provider exception text to the client — it can contain
        # request details. Log server-side, return a generic message.
        logger.error("Artifact generation failed (provider %s)", provider.provider_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Artifact generation failed. Please try again.")

    # From here on the user's artifact exists and their LLM call is already paid
    # for, so nothing below is allowed to throw it away. Parsing and persistence
    # degrade gracefully instead.
    try:
        structured_artifact = parse_raw_ai_output(request.artifact_type, raw_ai_output)
    except Exception:
        logger.error("Failed to parse AI output; returning raw text", exc_info=True)
        first_line = raw_ai_output.strip().split("\n")[0].lstrip("# ").strip()
        structured_artifact = StructuredArtifact(
            title=first_line[:120] or f"Generated {request.artifact_type}",
            raw_output=raw_ai_output,
        )

    warning = None
    try:
        persistence_service.save_artifact(request.artifact_type, structured_artifact)
    except Exception:
        logger.error("Could not save artifact to history; returning it anyway", exc_info=True)
        warning = "Your artifact was generated, but history is unavailable right now so it was not saved."

    return ArtifactResponse(status="success", artifact=structured_artifact, warning=warning)
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
    