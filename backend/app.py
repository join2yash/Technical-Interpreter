"""Sprint 1A: Text Technical Interpreter API.

The first implementation is intentionally deterministic. It extracts
sentence-level evidence from raw technical text, identifies missing sections,
and asks targeted clarification questions. It never invents facts.
"""

import re
from dataclasses import dataclass
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel, Field


app = FastAPI(title="Technical Interpreter", version="0.1.1")


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


def _sentences(text: str) -> list[str]:
    """Split text into simple sentence-level evidence units."""
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]


def interpret_text(text: str, sections: List[str] | None = None) -> InterpretResponse:
    """Extract evidence-supported sentences without generating new facts."""
    requested = set(sections or [field.key for field in FIELDS])
    sentences = _sentences(text)
    extracted: dict[str, str | None] = {}
    missing: list[str] = []
    questions: list[str] = []

    for field in FIELDS:
        if field.key not in requested:
            continue

        matches = [
            sentence
            for sentence in sentences
            if any(keyword in sentence.lower() for keyword in field.keywords)
        ]

        if matches:
            extracted[field.key] = " ".join(matches)
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
