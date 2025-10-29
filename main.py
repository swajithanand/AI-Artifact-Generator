# main.py

import os
import re
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from models import ArtifactRequest, ArtifactResponse, StructuredArtifact
from strategies import get_orchestrator, AIOrchestrator
from database import create_db_and_tables, get_session, Artifact

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Artifact Generator Backend")

# CORS Configuration
# NOTE: The list of allowed origins must include your new Vercel domain!
allowed_origins = [
    "https://ai-artifact-generator-swajiths-projects.vercel.app", # <--- THE LIVE FRONTEND
    "http://localhost:3000", # Still needed for local testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Event: Create DB Tables
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    logger.info("Database tables created successfully")

# Persistence Service
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

# Parsing Logic
def parse_raw_ai_output(artifact_type: str, raw_output: str) -> StructuredArtifact:
    """Parses raw text into a structured Pydantic model with safe checks."""
    
    def find_content(start_pattern, end_pattern=None):
        start_match = re.search(start_pattern, raw_output, re.DOTALL | re.IGNORECASE)
        if not start_match:
            return ""
        
        start_pos = start_match.end()
        
        if end_pattern:
            end_match = re.search(end_pattern, raw_output[start_pos:], re.DOTALL | re.IGNORECASE)
            end_pos = start_pos + end_match.start() if end_match else len(raw_output)
        else:
            end_pos = len(raw_output)
            
        return raw_output[start_pos:end_pos].strip()

    # Common Title Parsing
    title_match = re.search(r"#(.*?)(?=\n|$)", raw_output)
    title = title_match.group(1).strip() if title_match else raw_output.split('\n')[0].strip().replace('Title:', '')

    if artifact_type == "User Story":
        us_match = re.search(r"User Story: (.*?)(?=Acceptance Criteria:|Definition of Done:|$)", raw_output, re.DOTALL)
        ac_match = re.search(r"Acceptance Criteria: (.*?)(?=Definition of Done:|$)", raw_output, re.DOTALL)
        
        user_story_text = us_match.group(1).strip() if us_match else ""
        ac_text = ac_match.group(1).strip() if ac_match else ""
        acceptance_criteria = [line.strip().lstrip('-').strip() for line in ac_text.split('\n') if line.strip()]
        
        if not title_match:
            title = user_story_text.split('.')[0].split(':')[0].strip() if user_story_text else f"Generated {artifact_type}"
        
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

    elif artifact_type == "Bug":
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

    # Fallback
    return StructuredArtifact(
        title=title,
        raw_output=raw_output
    )

# Health check route
@app.get("/")
def health_check():
    return {"status": "ok", "message": "AI Artifact Generator API is running"}
@app.get("/history")
def get_artifact_history(persistence_service: PersistenceService = Depends()):
    try:
        history = persistence_service.get_history()
        return {"status": "success", "data": history}
    except Exception as e:
        logger.error(f"Error fetching artifact history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch artifact history")
    pass

# Main artifact generation route
#@app.post("/api/generate-artifact", response_model=ArtifactResponse)
# FIX: Remove the '/api' from the route path itself
@app.post("/generate-artifact", response_model=ArtifactResponse)
async def generate_artifact_route(
    request: ArtifactRequest,
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
    persistence_service: PersistenceService = Depends()
):
    try:
        logger.debug(f"Received request for type: {request.artifact_type}")
        
        # Call Strategy (AI Generation)
        raw_ai_output = orchestrator.generate_raw(request)
        
        # Parse Output
        structured_artifact = parse_raw_ai_output(request.artifact_type, raw_ai_output)
        
        # Save to DB
        persistence_service.save_artifact(request.artifact_type, structured_artifact)
        
        # Return Response
        return ArtifactResponse(
            status="success",
            artifact=structured_artifact
        )

    except Exception as e:
        logger.error(f"Critical Error in artifact generation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Backend processing failed: {str(e)}")
    pass