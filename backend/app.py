"""Sprint 1A: deterministic text technical interpreter API."""

import re
from dataclasses import dataclass
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel, Field


app = FastAPI(title="Technical Interpreter", version="0.2.1")


@dataclass(frozen=True)
class FieldDefinition:
    key: str
    question: str


FIELDS = (
    FieldDefinition("issue", "What happened?"),
    FieldDefinition("cause", "What caused the issue?"),
    FieldDefinition("identification", "How was the issue detected or reported?"),
    FieldDefinition("people_involved", "Who was involved?"),
    FieldDefinition("resolution", "What was done to resolve the issue?"),
    FieldDefinition("verification", "How was the resolution verified?"),
)


class InterpretRequest(BaseModel):
    text: str = Field(min_length=1, description="Raw technical text")
    sections: List[str] | None = Field(default=None, description="Sections to document")


class InterpretResponse(BaseModel):
    source_text: str
    extracted_information: dict[str, str | None]
    missing_information: List[str]
    clarification_questions: List[str]


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]


def _clean(value: str) -> str:
    return value.strip(" \t\n,;:")


def _extract_issue(sentences: list[str]) -> str | None:
    for sentence in sentences:
        if re.search(r"\b(failed|failure|error|problem|issue)\b", sentence, re.I):
            return _clean(re.split(r"\s+(?:because|due to)\s+", sentence, maxsplit=1, flags=re.I)[0])
    return None


def _extract_cause(sentences: list[str]) -> str | None:
    for sentence in sentences:
        match = re.search(r"\b(?:because|due to)\s+(.+)$", sentence, re.I)
        if match:
            return _clean(match.group(1).rstrip("."))
        match = re.search(r"\broot cause(?: was| is)?\s+(.+)$", sentence, re.I)
        if match:
            return _clean(match.group(1).rstrip("."))
    return None


def _extract_identification(sentences: list[str]) -> str | None:
    for sentence in sentences:
        if any(re.search(pattern, sentence, re.I) for pattern in (r"\bdetected\b", r"\breported\b", r"\bmonitoring\b", r"\balert\b", r"\bobserved\b")):
            return sentence
    return None


def _extract_people(sentences: list[str]) -> str | None:
    roles = ("developer", "engineer", "dba", "administrator", "admin", "team", "owner", "user", "customer")
    found = []
    for sentence in sentences:
        for role in roles:
            if re.search(rf"\b{re.escape(role)}\b", sentence, re.I) and role not in found:
                found.append(role)
    return ", ".join(found) if found else None


def _extract_resolution(sentences: list[str]) -> str | None:
    for sentence in sentences:
        if re.search(r"\b(restarted|restart|fixed|fix|resolved|resolve|patched|patch)\b", sentence, re.I):
            value = re.split(r"\s+and\s+(?=(?:tested|verified|confirmed)\b)", sentence, maxsplit=1, flags=re.I)[0]
            return _clean(value)
    return None


def _extract_verification(sentences: list[str]) -> str | None:
    for sentence in sentences:
        match = re.search(r"\b(?:and\s+)?(tested|verified|confirmed)\s+(.+)$", sentence, re.I)
        if match:
            return _clean(f"{match.group(1)} {match.group(2)}")
        match = re.search(r"\b(validation)\b\s*(.*)$", sentence, re.I)
        if match:
            return _clean(f"{match.group(1)} {match.group(2)}")
    return None


EXTRACTORS = {
    "issue": _extract_issue,
    "cause": _extract_cause,
    "identification": _extract_identification,
    "people_involved": _extract_people,
    "resolution": _extract_resolution,
    "verification": _extract_verification,
}


def interpret_text(text: str, sections: List[str] | None = None) -> InterpretResponse:
    requested = set(sections or [field.key for field in FIELDS])
    sentences = _sentences(text)
    extracted: dict[str, str | None] = {}
    missing: list[str] = []
    questions: list[str] = []

    for field in FIELDS:
        if field.key not in requested:
            continue
        value = EXTRACTORS[field.key](sentences)
        extracted[field.key] = value
        if value is None:
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
