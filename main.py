# main.py

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware 
from models import ArtifactRequest, ArtifactResponse, StructuredArtifact
from strategies import get_orchestrator, AIOrchestrator
from database import create_db_and_tables, get_session, Artifact
from sqlmodel import Session, select
from dotenv import load_dotenv # <--- NEW IMPORT
load_dotenv() # <--- NEW FUNCTION CALL: Load variables from .env
import os # <--- NEW IMPORT
from fastapi import FastAPI, Depends, HTTPException 
import re
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
from fastapi import FastAPI, Depends, HTTPException # <--- ADD HTTPException
from fastapi.middleware.cors import CORSMiddleware 

 Temporarily comment out all imports that rely on database/strategies
# from strategies import get_orchestrator, AIOrchestrator
# from database import create_db_and_tables, get_session, Artifact
# from models import ArtifactRequest, ArtifactResponse, StructuredArtifact

app = FastAPI(title="Health Check App")

# CORS is kept for network test
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- NO STARTUP EVENTS ---

# --- BARE MINIMUM HEALTH CHECK ROUTE ---
@app.get("/")
def health_check():
    return {"status": "ok", "message": "Server is running, but logic is disabled."}

# @app.post("/api/generate-artifact") # TEMPORARILY DISABLED
# async def generate_artifact_route():
#     pass
# ... other imports ...
import logging # <--- ADD LOGGING IMPORT

# main.py (TEMPORARY DEBUGGING VERSION)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Artifact Generator Backend")


# --- 1. CORS Middleware (FIXED) ---
# Allow the specific frontend port (3000) to communicate with the backend (8000)
origins = [
    "http://localhost:3000", # <--- YOUR FRONTEND PORT
    "http://192.168.178.30:3000/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 2. Startup Event: Create DB Tables ---
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    print("Database tables ensured to exist.")

# --- 3. Persistence Service (DB Logic) ---
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


# --- 4. Parsing Logic (Artifact Templater) ---
# main.py

# ... (lines above) ...

# --- 4. Parsing Logic (Artifact Templater) ---
# main.py

# ... (lines above) ...

# --- 4. Parsing Logic (Artifact Templater) ---
def parse_raw_ai_output(artifact_type: str, raw_output: str) -> StructuredArtifact:
    """Parses raw text into a structured Pydantic model with safe checks."""
    
    # --- Helper to safely find content between headers ---
    def find_content(start_pattern, end_pattern=None):
        start_match = re.search(start_pattern, raw_output, re.DOTALL | re.IGNORECASE)
        if not start_match: return ""
        
        start_pos = start_match.end()
        
        if end_pattern:
            end_match = re.search(end_pattern, raw_output[start_pos:], re.DOTALL | re.IGNORECASE)
            end_pos = start_pos + end_match.start() if end_match else len(raw_output)
        else:
            end_pos = len(raw_output)
            
        return raw_output[start_pos:end_pos].strip()

    # --- Common Title Parsing (made safer) ---
    title_match = re.search(r"#(.*?)(?=\n|$)", raw_output)
    # This is safe because it checks title_match first.
    title = title_match.group(1).strip() if title_match else raw_output.split('\n')[0].strip().replace('Title:', '')


    if artifact_type == "User Story":
        us_match = re.search(r"User Story: (.*?)(?=Acceptance Criteria:|Definition of Done:|$)", raw_output, re.DOTALL)
        ac_match = re.search(r"Acceptance Criteria: (.*?)(?=Definition of Done:|$)", raw_output, re.DOTALL)
        
        user_story_text = us_match.group(1).strip() if us_match else ""
        ac_text = ac_match.group(1).strip() if ac_match else ""
        acceptance_criteria = [line.strip().lstrip('-').strip() for line in ac_text.split('\n') if line.strip()]
        
        if not title_match: title = user_story_text.split('.')[0].split(':')[0].strip() if user_story_text else f"Generated {artifact_type}"
        
        return StructuredArtifact(
            title=title,
            userStoryText=user_story_text,
            acceptanceCriteria=acceptance_criteria,
            raw_output=raw_output
        )

    elif artifact_type == "Epic":
        description = find_content(r"## Description of the Epic:", r"## Elevator Pitch")
        pitch = find_content(r"## Elevator Pitch \(Epic Hypothesis Statement\):")
        full_description = f"## Description\n{description}\n\n## Elevator Pitch\n{pitch}"
        
        return StructuredArtifact(
            title=title,
            description=full_description,
            raw_output=raw_output
        )
        
    elif artifact_type == "Feature":
        problem = find_content(r"## Problem Statement:", r"## Feature Hypothesis")
        hypothesis = find_content(r"## Feature Hypothesis:", r"## Acceptance Criteria")
        ac_text = find_content(r"## Acceptance Criteria:")
        
        acceptance_criteria = [line.strip().lstrip('0123456789.- ').strip() for line in ac_text.split('\n') if line.strip()]
        full_description = f"## Problem Statement\n{problem}\n\n## Feature Hypothesis\n{hypothesis}"
        
        return StructuredArtifact(
            title=title,
            description=full_description,
            acceptanceCriteria=acceptance_criteria,
            raw_output=raw_output
        )

    # --- FINAL FIX FOR BUG/SIMPLE ARTIFACTS ---
    # Bug simulation starts with 'Title:' so we'll ensure we handle that case.
    if artifact_type == "Bug":
        title_bug_match = re.search(r"Title:(.*?)(?=\n|$)", raw_output)
        description_bug_match = re.search(r"Description:(.*?)(?=Steps to Reproduce:|$)", raw_output, re.DOTALL)
        steps_bug_match = re.search(r"Steps to Reproduce:(.*?)(?=Expected Result:|$)", raw_output, re.DOTALL)

        bug_title = title_bug_match.group(1).strip() if title_bug_match else title
        bug_description = description_bug_match.group(1).strip() if description_bug_match else ""
        bug_steps = steps_bug_match.group(1).strip() if steps_bug_match else ""

        full_bug_description = f"## Description\n{bug_description}\n\n## Steps to Reproduce\n{bug_steps}"

        return StructuredArtifact(
            title=bug_title,
            description=full_bug_description,
            raw_output=raw_output
        )

    # Fallback for unexpected types
    return StructuredArtifact(
        title=title,
        raw_output=raw_output
    )

# ... (rest of the file remains the same)

# ... (rest of the file remains the same)


# --- 5. FastAPI Routes ---

@app.post("/api/generate-artifact", response_model=ArtifactResponse)
async def generate_artifact_route(
    request: ArtifactRequest,
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
    persistence_service: PersistenceService = Depends()
):
    try:
        logger.debug(f"Received request for type: {request.artifact_type}")
        
        # a. Call Strategy (AI Generation)
        raw_ai_output = orchestrator.generate_raw(request)
        
        # b. Parse Output
        structured_artifact = parse_raw_ai_output(request.artifact_type, raw_ai_output)
        
        # c. Save to DB
        persistence_service.save_artifact(request.artifact_type, structured_artifact)
        
        # d. Return Response
        return ArtifactResponse(
            status="success",
            artifact=structured_artifact
        )

    except Exception as e:
        # THIS LOGS THE FULL PYTHON TRACEBACK FOR DEBUGGING!
        logger.error(f"Critical Error in artifact generation: {str(e)}", exc_info=True)
        # Sends a clean JSON 500 response to the frontend
        raise HTTPException(status_code=500, detail=f"Backend processing failed: {str(e)}")