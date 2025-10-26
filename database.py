# database.py

from sqlmodel import SQLModel, Field, Session, create_engine
from datetime import datetime
from typing import Optional
from fastapi import Depends
from sqlalchemy.schema import PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import JSONB 
from urllib.parse import quote_plus # <--- NEW IMPORT for clean encoding
from sqlalchemy.dialects.postgresql import JSONB

# --- REPLACE THIS LINE ---
# IMPORTANT: Replace the placeholder with your actual Supabase Connection String.
#DATABASE_URL = r"postgresql://postgres:Sw%40jith%4092@db.mxkgpfayipntrbfyqmdh.supabase.co:5432/postgres"

# --- Configuration (Read individual parameters from Render variables) ---
DB_HOST = os.getenv("DB_HOST", "localhost") 
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password") 
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = "postgres" # Supabase default

# Build the connection string using the SAFE quote_plus function
# The quote_plus function handles the encoding of the password correctly.
DATABASE_URL = f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}" 

# Setup the database engine
#engine = create_engine(DATABASE_URL, echo=False) 
# -------------------------

# Setup the database engine
# echo=True prints the SQL commands executed, helpful for debugging
engine = create_engine(DATABASE_URL, echo=False) 

# --- 1. Database Model ---
class Artifact(SQLModel, table=True):
    """Defines the structure of the table that will hold all generated artifacts."""
    
    # FIX: Move the dictionary to the end and make the whole thing a tuple.
    # The dictionary of arguments (like 'schema') must be the last element.
    __table_args__ = ({'schema': 'public'}, ) 
    
    id: Optional[int] = Field(default=None, primary_key=True)
    type: str = Field(index=True, max_length=50) 
    title: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    artifact_data: dict = Field(sa_type=JSONB)

# --- 2. Database Session Dependency ---
def create_db_and_tables():
    """Called at startup to create tables in Supabase if they don't exist."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """FastAPI Dependency: Provides a database session for a single request."""
    with Session(engine) as session:
        yield session