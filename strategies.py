# strategies.py

from abc import ABC, abstractmethod
from models import ArtifactRequest
from typing import Dict
from fastapi import Depends
import os
from google import genai
from google.genai.errors import APIError # Import for error handling

# --- Configuration (Model and API Key) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # Read the new key
GEMINI_MODEL = "gemini-2.5-flash" # Fast, powerful model

if not GEMINI_API_KEY:
    print("\n--- WARNING: GEMINI_API_KEY environment variable is NOT SET! ---")
    print("--- Using SIMULATED responses until the key is configured. ---")


# --- 1. The Strategy Interface (No change needed) ---
class AIProviderStrategy(ABC):
    @abstractmethod
    def generate(self, inputs: ArtifactRequest) -> str:
        pass
        
    def _construct_prompt(self, inputs: ArtifactRequest) -> str:
        """Constructs the detailed prompt for the Gemini model."""
        prompt = f"""
        You are an expert Agile Product Owner. Your task is to generate a comprehensive {inputs.artifact_type} 
        based on the provided details. Output the artifact in a format that is easy to parse.

        [INSTRUCTIONS]
        - Title: Be concise and descriptive.
        - For a User Story: Use the format "As a... I want... so that..." and separate Acceptance Criteria (AC).
        - The response MUST start with a line containing the artifact's Title (e.g., "# Epic Title: ...")
        
        [USER INPUTS]
        - ARTIFACT TYPE: {inputs.artifact_type}
        - BUSINESS CASE: {inputs.business_use_case}
        - PERSONA: {inputs.persona}
        - TECHNICAL CONTEXT: {inputs.technical_info}
        """
        return prompt

# --- 2. Concrete Strategy (LIVE GEMINI IMPLEMENTATION) ---
class GeminiStrategy(AIProviderStrategy):
    """
    Live implementation for the Google Gemini API.
    """
    def __init__(self):
        # Initialize client here. It will automatically use the GEMINI_API_KEY.
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def generate(self, inputs: ArtifactRequest) -> str:
        prompt = self._construct_prompt(inputs)

        if not GEMINI_API_KEY:
            # Fallback to a simple simulation if key is missing
            return f"# Title: Simulated {inputs.artifact_type} - Key Missing\nUser Story: As a developer, I want to use a simulated response so that the application doesn't crash."

        try:
            # REAL API CALL
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            # Gemini's response is in response.text
            return response.text

        except APIError as e:
            # Catch API-specific errors (400 invalid request, etc.)
            raise Exception(f"Gemini API Error: Details: {str(e)}")
        except Exception as e:
            # Catch network or other errors
            raise Exception(f"Gemini Network/Client Error: {str(e)}")


# --- 3. The Orchestrator Class and Dependency (SWITCHED) ---
class AIOrchestrator:
    """Manages which AI Strategy is active."""
    def __init__(self):
        # *** SWITCHED TO GEMINI STRATEGY ***
        self._strategy = GeminiStrategy()
        print("--- Backend Initialized with LIVE GeminiStrategy ---")

    def generate_raw(self, inputs: ArtifactRequest) -> str:
        return self._strategy.generate(inputs)

# Dependency to provide the orchestrator instance
def get_orchestrator() -> AIOrchestrator:
    return AIOrchestrator()