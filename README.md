# AI Artifact Generator

Turn a plain-language business requirement into a ready-to-use Agile artifact — User Story, Epic, Feature, or Bug — using the LLM of your choice. Users bring their own API key (Gemini, OpenAI, or Anthropic) via the in-app Settings; keys are stored only in the browser and never persisted server-side.

**Live app:** https://ai-artifact-generator.vercel.app

**Stack:** React + Vite + Tailwind (frontend, Vercel) · FastAPI (backend, Render) · Postgres (Supabase)

## Architecture

### System overview

```mermaid
flowchart TD
    subgraph Browser["User's browser"]
        UI["React SPA<br/>(Vercel static hosting)"]
        LS[("Browser storage<br/>user's API key")]
        UI <--> LS
    end

    subgraph Backend["FastAPI backend (Render)"]
        API["Routes — main.py<br/>/generate-artifact · /history · /validate-key"]
        REG["Provider registry — strategies.py<br/>key used in memory only"]
        PARSE["Artifact parser<br/>raw text → structured"]
        PERS["Persistence service"]
        API --> REG
        API --> PARSE
        API --> PERS
    end

    G["Google Gemini"]
    O["OpenAI"]
    A["Anthropic Claude"]
    DB[("Supabase Postgres<br/>artifact history")]

    UI -- "HTTPS<br/>X-LLM-Provider / X-LLM-Model / X-LLM-Key headers" --> API
    REG --> G
    REG --> O
    REG --> A
    PERS --> DB
```

### Bring-your-own-key (BYOK) request flow

```mermaid
sequenceDiagram
    actor U as User
    participant F as Frontend (Vercel)
    participant B as Backend (Render)
    participant P as LLM provider
    participant D as Supabase

    U->>F: Save provider + API key in Settings
    Note over F: Key stored in localStorage /<br/>sessionStorage only
    U->>F: Describe use case, click Generate
    F->>B: POST /generate-artifact<br/>+ X-LLM-* headers over HTTPS
    B->>B: build_provider() — pick strategy,<br/>key held in memory only
    B->>P: generate(prompt) with user's key
    P-->>B: raw artifact text
    B->>B: parse into StructuredArtifact
    B->>D: save artifact (never the key)
    B-->>F: JSON artifact
    F-->>U: rendered markdown + history entry
```

### Provider layer (UML)

The backend uses a strategy pattern: one abstract interface, one concrete class per LLM vendor, and a per-request factory that never persists the user's key.

```mermaid
classDiagram
    class AIProviderStrategy {
        <<abstract>>
        +provider_id: str
        +api_key: str
        +model: str
        +generate(inputs) str*
        +validate() None*
        #_construct_prompt(inputs) str
    }
    class GeminiProvider {
        +generate(inputs) str
        +validate() None
    }
    class OpenAIProvider {
        +generate(inputs) str
        +validate() None
    }
    class AnthropicProvider {
        +generate(inputs) str
        +validate() None
    }
    class build_provider {
        <<factory function>>
        picks strategy from X-LLM-Provider header
        validates key + model format
        falls back to server GEMINI_API_KEY if set
    }
    AIProviderStrategy <|-- GeminiProvider
    AIProviderStrategy <|-- OpenAIProvider
    AIProviderStrategy <|-- AnthropicProvider
    build_provider ..> AIProviderStrategy : creates per request
```

### Artifact-specific prompts

Each artifact type has its own dedicated prompt template in [prompts.py](prompts.py) — there is no single generic prompt with the type substituted in, because Epic, Feature and User Story sit at different levels of abstraction.

```mermaid
flowchart LR
    S["Artifact type<br/>selected in UI"] --> R{"build_prompt()<br/>router"}
    R -- Epic --> E["generate_epic_prompt<br/>Elevator Pitch · Business Outcomes<br/>Leading Indicators · NFRs · Summary"]
    R -- Feature --> F["generate_feature_prompt<br/>Benefit Statement · Description<br/>Outcome · Acceptance Criteria · NFRs"]
    R -- User Story --> U["generate_user_story_prompt<br/>As a/I want/so that · Description<br/>Acceptance Criteria · DoD"]
    R -- unknown --> X["400 Unsupported artifact type"]
```

Every template carries explicit anti-contamination rules (an Epic must not contain Features or User Stories, and so on) and a shared set of quality rules. The response parser in `main.py` is section-driven and kept in sync with these templates.

Run the prompt/parser tests with:

```bash
python test_artifact_prompts.py
```

### Security model

- The user's API key lives only in their browser (`localStorage`, or `sessionStorage` when "remember" is off) and travels only as an HTTPS request header — never in a URL, never in the database, never in logs.
- The backend instantiates a provider with the key for a single request, then discards it. Logging runs at INFO level so headers can't leak through debug output.
- Provider errors are translated: invalid key → 401 with a friendly message, rate limit → 429. Raw provider exception text is never echoed to the client.
- Adding a new LLM vendor = one new subclass of `AIProviderStrategy` plus a registry entry.

## Run locally

Prerequisites: Node.js, Python 3.13

**Backend**
```bash
pip install -r requirements.txt
# set DATABASE_URL (Supabase connection string) in a .env file
uvicorn main:app --reload --port 8000
```

**Frontend**
```bash
npm install
echo VITE_API_BASE_URL=http://localhost:8000 > .env.local
npm run dev
```

## Deploy the backend to Render (free)

The repo contains a [render.yaml](render.yaml) blueprint, so Render configures itself:

1. Sign up at [render.com](https://render.com) with your GitHub account (free, no card needed).
2. Click **New + → Blueprint** and select the `AI-Artifact-Generator` repo.
3. Render reads `render.yaml` and prompts for one value: `DATABASE_URL`.
   Paste your Supabase connection string — in Supabase go to **Connect → Transaction pooler** and copy the URI (port `6543`; replace `[YOUR-PASSWORD]` with your real database password).
4. Click **Apply**. First build takes a few minutes; when it turns "Live", copy the service URL.
5. Point the frontend at it: in Vercel go to **Settings → Environment Variables**, add `VITE_API_BASE_URL` = the Render URL, then **Deployments → Redeploy**.

Optional but recommended on the free plan: create a free [UptimeRobot](https://uptimerobot.com) HTTP monitor pinging the Render URL every 5 minutes. This keeps the instance warm — otherwise it spins down after 15 idle minutes and the next user waits ~40 s.

Optional: add a `GEMINI_API_KEY` environment variable on the Render service to enable keyless demo mode; without it, users must add their own key in Settings (gear icon).

## Environment variables

| Where | Variable | Purpose |
|---|---|---|
| Backend (Render) | `DATABASE_URL` | Supabase Postgres connection string (required) |
| Backend (Render) | `GEMINI_API_KEY` | Optional server fallback key for keyless demo mode |
| Frontend (Vercel) | `VITE_API_BASE_URL` | Backend base URL, no trailing slash |
