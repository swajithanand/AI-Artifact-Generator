# prompts.py — artifact-specific prompt templates.
#
# Each artifact type has its OWN prompt with its own purpose, writing
# instructions, structure, required fields and output format. There is
# deliberately no single generic template with the artifact type substituted
# in: Epic, Feature and User Story sit at different levels of abstraction and
# must not bleed into one another.

from typing import Callable, Dict, Optional


class UnsupportedArtifactTypeError(ValueError):
    """Raised when no dedicated prompt exists for the requested artifact type."""


class MissingArtifactInputError(ValueError):
    """Raised when required user input is missing, so we never send an empty prompt."""


# Rules that apply to every artifact type. These constrain *quality*; the
# structure of each artifact lives in its own template below.
QUALITY_RULES = """
QUALITY RULES

- Avoid hallucination. Do not invent specific business numbers, customer names,
  systems, regulations, KPIs or technologies unless they are provided in the
  inputs or can be reasonably inferred from the technical context.
- Lead with business value: Problem -> User/Customer -> Capability -> Outcome.
  Do not jump straight to technical implementation.
- Use professional Agile/Product terminology in clear, plain language.
- Avoid vague statements. Instead of "Improve the user experience", write
  "Enable users to submit and track service requests from a single interface".
- Anything testable must describe observable behaviour and outcomes.
- Where the inputs are thin, stay general rather than fabricating detail.
"""


def _clean(value: Optional[str], fallback: str = "Not specified") -> str:
    """Normalises optional free-text input so prompts never contain empty slots."""
    if value is None:
        return fallback
    stripped = value.strip()
    return stripped if stripped else fallback


def _require_business_case(business_use_case: Optional[str]) -> str:
    if business_use_case is None or not business_use_case.strip():
        raise MissingArtifactInputError(
            "A business case / scenario is required to generate an artifact."
        )
    return business_use_case.strip()


def generate_epic_prompt(
    business_use_case: str,
    persona: Optional[str] = None,
    technical_info: Optional[str] = None,
) -> str:
    """Prompt for an EPIC: a large business problem spanning multiple Features."""
    business_use_case = _require_business_case(business_use_case)
    persona = _clean(persona)
    technical_info = _clean(technical_info)

    return f"""You are an expert Agile Product Manager / Product Owner experienced in SAFe and enterprise product development.

Your task is to create a high-quality EPIC based on the information provided.

The Epic should describe a significant business or customer problem/opportunity that may require multiple Features and potentially multiple teams or Program Increments to deliver.

Do NOT write this as a Feature or User Story.

EPIC INPUTS

Business Case:
{business_use_case}

Persona / Customer:
{persona}

Technical Context:
{technical_info}

EPIC REQUIREMENTS

Create the Epic using the following structure.

# Epic Title: <concise and descriptive title>

## Elevator Pitch

Use this structure:

"For <customers/personas> who <need/problem/opportunity>, the <solution> is a <solution category/how> that <provides the key value>. Unlike <current solution/alternative/non-existing solution>, our solution <key differentiator or improvement>."

Make the statement clear, concise and outcome-oriented.

## Business Outcomes

Describe the measurable business outcomes expected from this Epic.

Include 2-5 outcomes where possible.

Focus on measurable value such as revenue, cost reduction, efficiency, customer satisfaction, risk reduction, compliance, time savings, productivity, adoption or operational improvements.

Do not invent unrealistic numerical targets unless the input provides them.

## Leading Indicators

Identify early signals that show whether the Epic is moving toward the expected outcome.

Include 2-5 relevant indicators, such as adoption rate, usage, completion rate, cycle time, conversion rate, error reduction, engagement or number of active users.

## Nonfunctional Requirements (NFRs)

Identify relevant NFRs for this Epic - for example performance, availability, scalability, security, reliability, accessibility, maintainability, observability, compliance or data privacy.

Only include NFRs that are genuinely relevant to the use case. Do not force one into the output.

## Epic Summary

Provide a short summary explaining the problem/opportunity, who benefits, the expected value, and why this Epic matters.

{QUALITY_RULES}
IMPORTANT

- Do not generate Features, User Stories, sprint tasks or technical subtasks.
- Stay at Epic level of abstraction.
- The output must contain ONLY the Epic artifact.
- Begin the response with the line "# Epic Title: ..." and nothing before it.
"""


def generate_feature_prompt(
    business_use_case: str,
    persona: Optional[str] = None,
    technical_info: Optional[str] = None,
) -> str:
    """Prompt for a FEATURE: one solution capability delivering clear value."""
    business_use_case = _require_business_case(business_use_case)
    persona = _clean(persona)
    technical_info = _clean(technical_info)

    return f"""You are an expert Agile Product Manager / Product Owner experienced in SAFe and enterprise product development.

Your task is to create a high-quality FEATURE based on the information provided.

A Feature should represent a specific solution capability that provides clear value and can normally be delivered within a relatively short timeframe.

Do NOT write this as an Epic or User Story.

FEATURE INPUTS

Business Case:
{business_use_case}

Persona:
{persona}

Technical Context:
{technical_info}

FEATURE REQUIREMENTS

Create the Feature using the following structure.

# Feature Title: <concise and descriptive title>

## Feature Benefit Statement

Use this structure:

"We will achieve <business outcome>
if <persona>
can achieve <user outcome>
with <feature/capability>."

Make the statement measurable and outcome-oriented where possible.

## Description

Describe what the Feature provides, who benefits from it, what capability is being introduced or improved, and what business/user problem it addresses.

Keep the description focused on the Feature. Do not describe detailed implementation steps unless they are necessary to explain the capability.

## Business / User Outcome

Clearly describe the expected outcome or benefit, and the value delivered to end users, internal users, customers, the business or the system.

## Acceptance Criteria

Create clear, testable Acceptance Criteria using Given / When / Then format where appropriate:

Given <initial condition>
When <user/system action>
Then <expected result>

Create 4-7 Acceptance Criteria where sufficient information is available.

Acceptance Criteria must be specific, testable, unambiguous, relevant to the Feature, and focused on observable outcomes. Include positive, negative and important edge cases where appropriate.

## Nonfunctional Considerations

Include relevant NFR considerations only when applicable - for example performance, security, availability, accessibility, compliance or scalability.

{QUALITY_RULES}
IMPORTANT

- Do not generate an Epic, User Stories or sprint tasks.
- Stay at Feature level of abstraction.
- The output must contain ONLY the Feature artifact.
- Begin the response with the line "# Feature Title: ..." and nothing before it.
"""


def generate_user_story_prompt(
    business_use_case: str,
    persona: Optional[str] = None,
    technical_info: Optional[str] = None,
) -> str:
    """Prompt for a USER STORY: one user need, action and expected benefit."""
    business_use_case = _require_business_case(business_use_case)
    persona = _clean(persona)
    technical_info = _clean(technical_info)

    return f"""You are an expert Agile Product Owner / Scrum Product Owner experienced in writing high-quality User Stories.

Your task is to create a clear, valuable and testable USER STORY based on the information provided.

The User Story should describe a specific user need, action and expected benefit.

Do NOT write this as an Epic or Feature.

USER STORY INPUTS

Business Case:
{business_use_case}

Persona:
{persona}

Technical Context:
{technical_info}

USER STORY REQUIREMENTS

Create the User Story using the following structure.

# User Story Title: <short, action-oriented title>

## User Story

Use exactly this structure:

As a <persona>,
I want <action/goal>,
so that <benefit/outcome>.

The story should describe who is performing the action, what the user wants to accomplish, and why.

Avoid technical implementation language unless the story is specifically for a technical user.

## Description

Provide a short explanation of the User Story and its intended outcome.

## Acceptance Criteria

Create 4-7 clear and testable Acceptance Criteria, preferring Given / When / Then format:

Given <initial condition>
When <action>
Then <expected outcome>

Acceptance Criteria should be specific, independently testable, describe observable behaviour, cover the happy path, cover important validation/error scenarios, cover relevant edge cases, and avoid implementation details.

## Definition of Done Considerations

Provide a concise list of relevant completion considerations where appropriate - for example functionality implemented, tests completed, Acceptance Criteria satisfied, documentation updated where required, and security/compliance checks completed where applicable.

{QUALITY_RULES}
IMPORTANT

- Do not generate an Epic, a Feature, multiple unrelated stories or sprint tasks.
- Stay at User Story level of abstraction.
- The output must contain ONLY the User Story artifact.
- Begin the response with the line "# User Story Title: ..." and nothing before it.
"""


def generate_legacy_prompt(
    artifact_type: str,
    business_use_case: str,
    persona: Optional[str] = None,
    technical_info: Optional[str] = None,
) -> str:
    """
    Original generic prompt, retained ONLY for artifact types that do not yet
    have a dedicated template (currently "Bug"). Keeping this preserves existing
    behaviour for those types instead of breaking them.
    """
    business_use_case = _require_business_case(business_use_case)
    persona = _clean(persona)
    technical_info = _clean(technical_info)

    return f"""You are an expert Agile Product Owner. Your task is to generate a comprehensive {artifact_type}
based on the provided details. Output the artifact in a format that is easy to parse.

[INSTRUCTIONS]
- Title: Be concise and descriptive.
- The response MUST start with a line containing the artifact's Title (e.g., "# Bug Title: ...")

[USER INPUTS]
- ARTIFACT TYPE: {artifact_type}
- BUSINESS CASE: {business_use_case}
- PERSONA: {persona}
- TECHNICAL CONTEXT: {technical_info}
"""


# --- ROUTING -------------------------------------------------------------
# Map strategy: artifact type -> dedicated prompt builder.
PROMPT_BUILDERS: Dict[str, Callable[..., str]] = {
    "Epic": generate_epic_prompt,
    "Feature": generate_feature_prompt,
    "User Story": generate_user_story_prompt,
}

# Types that intentionally still use the original generic prompt.
LEGACY_TYPES = {"Bug"}

SUPPORTED_ARTIFACT_TYPES = sorted(PROMPT_BUILDERS) + sorted(LEGACY_TYPES)


def build_prompt(
    artifact_type: str,
    business_use_case: str,
    persona: Optional[str] = None,
    technical_info: Optional[str] = None,
) -> str:
    """
    Routes the selected artifact type to its dedicated prompt builder.

    Raises MissingArtifactInputError when the business case is empty and
    UnsupportedArtifactTypeError for an unknown artifact type.
    """
    builder = PROMPT_BUILDERS.get(artifact_type)
    if builder is not None:
        return builder(business_use_case, persona, technical_info)

    if artifact_type in LEGACY_TYPES:
        return generate_legacy_prompt(
            artifact_type, business_use_case, persona, technical_info
        )

    raise UnsupportedArtifactTypeError(
        "Unsupported artifact type. Please select Epic, Feature, or User Story."
    )
