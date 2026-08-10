# models.py

from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# The four artifact types the UI can send
ArtifactTypeLiteral = Literal["User Story", "Bug", "Feature", "Epic"]

# --- Input/Request Model ---
class ArtifactRequest(BaseModel):
    artifact_type: ArtifactTypeLiteral = Field(..., description="The type of artifact to generate.")
    business_use_case: str = Field(..., description="The core business scenario or user goal.")
    persona: str = Field(..., description="The user role and key characteristics.")
    technical_info: str = Field(..., description="Relevant APIs, frameworks, and technical context.")

# --- Internal/Output Model (The Structured Artifact) ---
class StructuredArtifact(BaseModel):
    title: str
    description: Optional[str] = None
    userStoryText: Optional[str] = None
    acceptanceCriteria: Optional[List[str]] = None
    keyFeatures: Optional[List[str]] = None
    raw_output: str # The full, unparsed text from the AI

# --- Final API Response Model ---
class ArtifactResponse(BaseModel):
    status: str
    artifact: StructuredArtifact
    # Set when the artifact was generated but something non-fatal went wrong
    # (e.g. history could not be saved). The artifact is still valid.
    warning: Optional[str] = None