# database.py - FINAL CLEANED VERSION

from sqlmodel import SQLModel, Field, Session, create_engine
from datetime import datetime
from typing import Optional
from fastapi import Depends
from sqlalchemy.dialects.postgresql import JSONB 
from urllib.parse import quote_plus 
import os
from sqlalchemy.schema import PrimaryKeyConstraint

# --- Configuration (Read individual parameters from Cloud Run environment) ---
# NOTE: os.getenv will return None if the variable is NOT set.
DB_HOST = os.getenv("DB_HOST") 
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD") 
DB_PORT = os.getenv("DB_PORT")
DB_NAME = "postgres" 

# FALLBACK CHECK: If individual variables are not set, assume the full URL is used.
# This prevents the application from crashing in production.
FULL_DB_URL_FROM_ENV = os.getenv("DATABASE_URL")

# Build the connection string using the safest method
if FULL_DB_URL_FROM_ENV:
    # Use the full URL (assumes it's correctly formatted/encoded)
    DATABASE_URL = FULL_DB_URL_FROM_ENV
else:
    # Use the individual parameters and safely encode the password
    # This requires all individual DB_* variables to be set.
    if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_PORT]):
        # This should ONLY happen if you are testing locally without the .env file
        # We will use a default error message to prevent a crash
        raise ValueError("Database credentials are not fully set in the environment variables.")
        
    DATABASE_URL = f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}" 

# Setup the database engine
engine = create_engine(DATABASE_URL, echo=False) 

# --- 1. Database Model ---
class Artifact(SQLModel, table=True):
    __table_args__ = ({'schema': 'public'}, ) 
    
    id: Optional[int] = Field(default=None, primary_key=True)
    type: str = Field(index=True, max_length=50) 
    title: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    artifact_data: dict = Field(sa_type=JSONB)

# --- 2. Database Session Dependency ---
def create_db_and_tables():
    """Called to create tables in Supabase if they don't exist."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """FastAPI Dependency: Provides a database session for a single request."""
    with Session(engine) as session:
        yield session