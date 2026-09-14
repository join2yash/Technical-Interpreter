"""Sprint 1A: Text Technical Interpreter API.

The first implementation deliberately stays small: accept technical text,
extract the facts that are explicitly present, identify missing information,
and return targeted clarification questions. It does not invent facts.
"""

from dataclasses import dataclass
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel, Field


app = FastAPI(title="Technical Interpreter", version="0.1.0")


@dataclass(frozen=True)
class FieldDefinition:
    key: str
    question: str
    keywords: tuple[str, ...]


FIELDS = (
    FieldDefinition("issue", "What happened?", ("issue", "problem", "error", "failed", "failure")),
    FieldDefinition("cause", "What caused the issue?", ("because", "cause", "caused", "root cause", "due to")),
    FieldDefinition("identification", "How was the issue detected or reported?", ("detected", "reported", "alert", "monitoring", "observed")),
    FieldDefinition("people_involved", "Who was involved?", ("developer", "engineer", "team", "owner", "user", "customer")),
    FieldDefinition("resolution", "What was done to resolve the issue?", ("fixed", "fix", "resolved", "resolution", "patched", "restart")),
    FieldDefinition("verification", "How was the resolution verified?", ("verified", "verification", "tested", "confirmed", "validation")),
)


class InterpretRequest(BaseModel):
    text: str = Field(min_length=1, description="Raw technical text")
    sections: List[str] | None = Field(
        default=None,
        description="Sections to document. Defaults to all Sprint 1A sections.",
    )


class InterpretResponse(BaseModel):
    source_text: str
    extracted_information: dict[str, str | None]
    missing_information: List[str]
    clarification_questions: List[str]


def interpret_text(text: str, sections: List[str] | None = None) -> InterpretResponse:
    """Extract only evidence-supported information from text.

    This Sprint 1A implementation intentionally does not use an LLM. A later
    stage can replace the heuristic extraction while keeping this contract.
    """
    requested = set(sections or [field.key for field in FIELDS])
    normalized = text.lower()
    extracted: dict[str, str | None] = {}
    missing: list[str] = []
    questions: list[str] = []

    for field in FIELDS:
        if field.key not in requested:
            continue

        matched = [keyword for keyword in field.keywords if keyword in normalized]
        if matched:
            extracted[field.key] = text
        else:
            extracted[field.key] = None
            missing.append(field.key)
            questions.append(field.question)

    return InterpretResponse(
        source_text=text,
        extracted_information=extracted,
        missing_information=missing,
        clarification_questions=questions,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/interpret", response_model=InterpretResponse)
def interpret(request: InterpretRequest) -> InterpretResponse:
    return interpret_text(request.text, request.sections)
