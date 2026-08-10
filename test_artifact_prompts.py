"""
Tests for artifact-specific prompt routing and response parsing.

Run directly (no extra dependencies):  python test_artifact_prompts.py
Or with pytest if installed:           python -m pytest test_artifact_prompts.py

An in-memory sqlite DATABASE_URL is set before importing main.py because
database.py deliberately fails fast when credentials are absent. SQLAlchemy does
not connect at import time and these tests never touch the database, so no
Postgres server or driver is required.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

from prompts import (  # noqa: E402
    build_prompt,
    generate_epic_prompt,
    generate_feature_prompt,
    generate_user_story_prompt,
    MissingArtifactInputError,
    UnsupportedArtifactTypeError,
)
from main import parse_raw_ai_output  # noqa: E402

# Shared inputs from the specification's test cases
BUSINESS_CASE = "Employees need a centralized way to request cloud services."
PERSONA = "Internal employees"
TECH = "AWS Cloud Platform"

# Sections that uniquely identify each artifact type
EPIC_SECTIONS = ["## Elevator Pitch", "## Business Outcomes", "## Leading Indicators",
                 "## Nonfunctional Requirements (NFRs)", "## Epic Summary"]
FEATURE_SECTIONS = ["## Feature Benefit Statement", "## Description",
                    "## Business / User Outcome", "## Acceptance Criteria",
                    "## Nonfunctional Considerations"]
STORY_SECTIONS = ["## User Story", "## Description", "## Acceptance Criteria",
                  "## Definition of Done Considerations"]


def test_epic_prompt_is_epic_specific():
    prompt = build_prompt("Epic", BUSINESS_CASE, PERSONA, TECH)

    assert prompt == generate_epic_prompt(BUSINESS_CASE, PERSONA, TECH)
    for section in EPIC_SECTIONS:
        assert section in prompt, f"Epic prompt missing {section}"
    assert '"# Epic Title: ..."' in prompt
    assert BUSINESS_CASE in prompt and PERSONA in prompt and TECH in prompt
    # No cross-artifact contamination
    assert "Do not generate Features, User Stories" in prompt
    assert "## Feature Benefit Statement" not in prompt
    assert "## Definition of Done Considerations" not in prompt


def test_feature_prompt_is_feature_specific():
    prompt = build_prompt("Feature", BUSINESS_CASE, PERSONA, TECH)

    assert prompt == generate_feature_prompt(BUSINESS_CASE, PERSONA, TECH)
    for section in FEATURE_SECTIONS:
        assert section in prompt, f"Feature prompt missing {section}"
    assert '"# Feature Title: ..."' in prompt
    assert "Given / When / Then" in prompt
    assert "Do not generate an Epic, User Stories or sprint tasks." in prompt
    assert "## Elevator Pitch" not in prompt
    assert "## Epic Summary" not in prompt


def test_user_story_prompt_is_story_specific():
    prompt = build_prompt("User Story", BUSINESS_CASE, PERSONA, TECH)

    assert prompt == generate_user_story_prompt(BUSINESS_CASE, PERSONA, TECH)
    for section in STORY_SECTIONS:
        assert section in prompt, f"User Story prompt missing {section}"
    assert '"# User Story Title: ..."' in prompt
    assert "As a <persona>," in prompt
    assert "Do not generate an Epic, a Feature" in prompt
    assert "## Elevator Pitch" not in prompt
    assert "## Feature Benefit Statement" not in prompt


def test_three_prompts_are_distinct():
    epic = build_prompt("Epic", BUSINESS_CASE, PERSONA, TECH)
    feature = build_prompt("Feature", BUSINESS_CASE, PERSONA, TECH)
    story = build_prompt("User Story", BUSINESS_CASE, PERSONA, TECH)
    assert len({epic, feature, story}) == 3, "Prompts must not be identical"


def test_bug_still_supported_via_legacy_prompt():
    """Bug exists in the UI, so it must keep working rather than erroring."""
    prompt = build_prompt("Bug", BUSINESS_CASE, PERSONA, TECH)
    assert "ARTIFACT TYPE: Bug" in prompt


def test_unsupported_artifact_type_raises_clear_error():
    for bad in ["Task", "", "epic", "Spike"]:
        try:
            build_prompt(bad, BUSINESS_CASE, PERSONA, TECH)
        except UnsupportedArtifactTypeError as e:
            assert "Please select Epic, Feature, or User Story" in str(e)
        else:
            raise AssertionError(f"Expected error for artifact type {bad!r}")


def test_missing_business_case_raises_rather_than_sending_empty_prompt():
    for empty in [None, "", "   "]:
        for artifact_type in ["Epic", "Feature", "User Story"]:
            try:
                build_prompt(artifact_type, empty, PERSONA, TECH)
            except MissingArtifactInputError:
                pass
            else:
                raise AssertionError(f"Expected error for empty business case ({artifact_type})")


def test_optional_inputs_degrade_gracefully():
    prompt = build_prompt("Epic", BUSINESS_CASE, "", None)
    assert "Not specified" in prompt
    assert "Persona / Customer:\nNot specified" in prompt


# --- Parsing: the templates changed, so parsing must track them ---

EPIC_OUTPUT = """# Epic Title: Centralized Cloud Service Request Management

## Elevator Pitch

For internal employees who need cloud resources quickly, the Cloud Service Portal is a self-service platform that provides governed, one-stop provisioning. Unlike email-based requests, our solution offers transparency and automated approvals.

## Business Outcomes

- Reduce average provisioning time
- Lower operational overhead for platform teams
- Improve compliance with cloud governance policy

## Leading Indicators

- Portal adoption rate
- Percentage of requests submitted via portal
- Average approval cycle time

## Nonfunctional Requirements (NFRs)

- Security: role-based access control
- Availability: business-hours availability target

## Epic Summary

Employees lack a single place to request cloud services, causing delays and inconsistent governance. A centralized portal benefits employees and platform teams.
"""

FEATURE_OUTPUT = """# Feature Title: Automated Service Request Approval

## Feature Benefit Statement

We will achieve faster cloud provisioning
if internal employees
can achieve automated approval of standard requests
with a rules-based approval engine.

## Description

Provides automated approval routing for standard, low-risk cloud service requests.

## Business / User Outcome

Employees receive standard resources without manual review, reducing wait time.

## Acceptance Criteria

- Given a standard request within policy limits, When the employee submits it, Then the request is auto-approved.
- Given a request exceeding cost thresholds, When submitted, Then it is routed for manual approval.
- Given an auto-approved request, When approval completes, Then the requester is notified.
- Given the approval engine is unavailable, When a request is submitted, Then it queues without data loss.

## Nonfunctional Considerations

- Security: approval decisions must be auditable
"""

STORY_OUTPUT = """# User Story Title: Submit a Cloud Service Request

## User Story

As an internal employee,
I want to submit a cloud service request through a single portal,
so that I can get the resources I need without chasing approvals by email.

## Description

Enables employees to submit a structured cloud service request from one interface.

## Acceptance Criteria

Given I am an authenticated employee
When I open the service request form
Then I can select a cloud service and submit a request

Given required fields are incomplete
When I submit the form
Then I see validation messages identifying the missing fields

Given I have submitted a request
When submission succeeds
Then I receive a confirmation with a tracking reference

Given the backend is unavailable
When I submit the form
Then my input is preserved and I am told to retry

## Definition of Done Considerations

- Functionality implemented and tests completed
- Acceptance Criteria satisfied
"""


def test_parses_epic_output():
    artifact = parse_raw_ai_output("Epic", EPIC_OUTPUT)
    assert artifact.title == "Centralized Cloud Service Request Management", artifact.title
    assert "Cloud Service Portal is a self-service platform" in artifact.description
    assert "Reduce average provisioning time" in artifact.description
    assert artifact.keyFeatures and "Portal adoption rate" in artifact.keyFeatures
    assert artifact.raw_output == EPIC_OUTPUT


def test_parses_feature_output():
    artifact = parse_raw_ai_output("Feature", FEATURE_OUTPUT)
    assert artifact.title == "Automated Service Request Approval", artifact.title
    assert "We will achieve faster cloud provisioning" in artifact.description
    assert "automated approval routing" in artifact.description.lower()
    assert len(artifact.acceptanceCriteria) == 4, artifact.acceptanceCriteria
    assert artifact.acceptanceCriteria[0].startswith("Given a standard request")


def test_parses_user_story_output():
    artifact = parse_raw_ai_output("User Story", STORY_OUTPUT)
    assert artifact.title == "Submit a Cloud Service Request", artifact.title
    assert artifact.userStoryText.startswith("As an internal employee,")
    assert "one interface" in artifact.description
    # Multi-line Given/When/Then blocks without bullets must survive
    assert len(artifact.acceptanceCriteria) == 4, artifact.acceptanceCriteria
    assert "validation messages" in artifact.acceptanceCriteria[1]


def test_title_prefix_variants_are_stripped():
    cases = {
        "# Epic Title: Alpha": "Alpha",
        "# Feature Title: Beta": "Beta",
        "# User Story Title: Gamma": "Gamma",
        "# Title: Delta": "Delta",
        "# Plain Heading": "Plain Heading",
    }
    for raw, expected in cases.items():
        assert parse_raw_ai_output("Epic", raw + "\n").title == expected


def test_parser_never_crashes_on_unexpected_shapes():
    for junk in ["", "no headings at all", "## Only a section\nbody", "#\n"]:
        for artifact_type in ["Epic", "Feature", "User Story", "Bug"]:
            artifact = parse_raw_ai_output(artifact_type, junk)
            assert artifact.raw_output == junk
            assert artifact.title


def test_api_error_responses():
    """
    End-to-end error handling through the API. Skipped when httpx (required by
    FastAPI's TestClient) is not installed, since it is not a runtime dependency.
    """
    try:
        from fastapi.testclient import TestClient
    except Exception:
        print("      (skipped: httpx/TestClient unavailable)")
        return

    import logging
    logging.disable(logging.CRITICAL)
    from main import app

    client = TestClient(app, raise_server_exceptions=False)
    headers = {"X-LLM-Provider": "gemini", "X-LLM-Key": "dummy-key"}
    base = {"business_use_case": BUSINESS_CASE, "persona": PERSONA, "technical_info": TECH}

    unsupported = client.post("/generate-artifact", json={**base, "artifact_type": "Task"}, headers=headers)
    assert unsupported.status_code == 400, unsupported.status_code
    assert "Please select Epic, Feature, or User Story" in unsupported.json()["detail"]

    for blank in ["", "   "]:
        empty = client.post(
            "/generate-artifact",
            json={**base, "business_use_case": blank, "artifact_type": "Epic"},
            headers=headers,
        )
        assert empty.status_code == 400, empty.status_code
        assert "business case" in empty.json()["detail"].lower()

    # BYOK behaviour must be unchanged
    no_key = client.post("/generate-artifact", json={**base, "artifact_type": "Epic"}, headers={})
    assert no_key.status_code == 401, no_key.status_code

    logging.disable(logging.NOTSET)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except Exception as e:
            failures += 1
            print(f"FAIL  {test.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    raise SystemExit(1 if failures else 0)
