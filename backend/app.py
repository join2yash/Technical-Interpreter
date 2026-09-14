"""Sprint 1A: deterministic text technical interpreter API."""

import re
from dataclasses import dataclass
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(title="Technical Interpreter", version="0.5.0")


@dataclass(frozen=True)
class FieldDefinition:
    key: str
    question: str
    title: str


FIELDS = (
    FieldDefinition("issue", "What happened?", "Issue"),
    FieldDefinition("cause", "What caused the issue?", "Cause"),
    FieldDefinition("identification", "How was the issue detected or reported?", "Identification"),
    FieldDefinition("people_involved", "Who was involved?", "People Involved"),
    FieldDefinition("resolution", "What was done to resolve the issue?", "Resolution"),
    FieldDefinition("verification", "How was the resolution verified?", "Verification"),
)


class InterpretRequest(BaseModel):
    text: str = Field(min_length=1, description="Raw technical text")
    sections: List[str] | None = Field(default=None, description="Sections to document")


class InterpretResponse(BaseModel):
    source_text: str
    extracted_information: dict[str, str | None]
    evidence_origin: dict[str, str]
    missing_information: List[str]
    clarification_questions: List[str]


class ClarifyRequest(BaseModel):
    source_text: str = Field(min_length=1, description="Original technical text")
    extracted_information: dict[str, str | None]
    answer: str = Field(min_length=1, description="Answer to the current clarification question")
    sections: List[str] | None = Field(default=None, description="Sections to document")


class ClarifyResponse(BaseModel):
    source_text: str
    extracted_information: dict[str, str | None]
    evidence_origin: dict[str, str]
    missing_information: List[str]
    next_question: str | None
    completed: bool


class DocumentRequest(BaseModel):
    extracted_information: dict[str, str | None]
    sections: List[str] | None = Field(default=None, description="Sections to include")


class DocumentResponse(BaseModel):
    title: str
    document_text: str


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
        if re.search(r"\b(restarted|restart|fixed|fix|resolved|resolve|patched|patch|corrected)\b", sentence, re.I):
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


def _requested_fields(sections: List[str] | None) -> list[FieldDefinition]:
    requested = set(sections or [field.key for field in FIELDS])
    return [field for field in FIELDS if field.key in requested]


def _evidence_origin(extracted: dict[str, str | None]) -> dict[str, str]:
    return {key: "current_case" for key, value in extracted.items() if value}


def interpret_text(text: str, sections: List[str] | None = None) -> InterpretResponse:
    fields = _requested_fields(sections)
    sentences = _sentences(text)
    extracted: dict[str, str | None] = {}
    missing: list[str] = []
    questions: list[str] = []

    for field in fields:
        value = EXTRACTORS[field.key](sentences)
        extracted[field.key] = value
        if value is None:
            missing.append(field.key)
            questions.append(field.question)

    return InterpretResponse(
        source_text=text,
        extracted_information=extracted,
        evidence_origin=_evidence_origin(extracted),
        missing_information=missing,
        clarification_questions=questions,
    )


def _next_missing_field(extracted: dict[str, str | None], sections: List[str] | None) -> FieldDefinition | None:
    for field in _requested_fields(sections):
        if not extracted.get(field.key):
            return field
    return None


def clarify_text(
    source_text: str,
    extracted_information: dict[str, str | None],
    answer: str,
    sections: List[str] | None = None,
) -> ClarifyResponse:
    extracted = dict(extracted_information)
    field = _next_missing_field(extracted, sections)

    if field is None:
        return ClarifyResponse(
            source_text=source_text,
            extracted_information=extracted,
            evidence_origin=_evidence_origin(extracted),
            missing_information=[],
            next_question=None,
            completed=True,
        )

    extracted[field.key] = _clean(answer)
    next_field = _next_missing_field(extracted, sections)
    missing = [item.key for item in _requested_fields(sections) if not extracted.get(item.key)]

    return ClarifyResponse(
        source_text=source_text,
        extracted_information=extracted,
        evidence_origin=_evidence_origin(extracted),
        missing_information=missing,
        next_question=next_field.question if next_field else None,
        completed=next_field is None,
    )


def _summary(extracted: dict[str, str | None], sections: List[str] | None) -> str:
    keys = {field.key for field in _requested_fields(sections)}
    parts = []
    if extracted.get("issue"):
        parts.append(f"The issue was {extracted['issue'].rstrip('.')}." )
    if extracted.get("cause"):
        parts.append(f"The identified cause was {extracted['cause'].rstrip('.')}." )
    if extracted.get("identification"):
        parts.append(f"The issue was identified as follows: {extracted['identification'].rstrip('.')}." )
    if extracted.get("people_involved") and "people_involved" in keys:
        parts.append(f"The people involved were {extracted['people_involved']}." )
    if extracted.get("resolution"):
        parts.append(f"The resolution involved {extracted['resolution'].rstrip('.')}." )
    if extracted.get("verification"):
        parts.append(f"The resolution was verified by {extracted['verification'].rstrip('.')}." )
    return " ".join(parts)


def create_documentation(
    extracted_information: dict[str, str | None],
    sections: List[str] | None = None,
) -> str:
    fields = _requested_fields(sections)
    missing = [field.title for field in fields if not extracted_information.get(field.key)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot generate documentation. Missing information: {', '.join(missing)}",
        )

    lines = ["# General Technical Documentation", ""]
    summary = _summary(extracted_information, sections)
    if summary:
        lines.extend(["## Technical Summary", "", summary, ""])

    for field in fields:
        lines.extend([f"## {field.title}", "", extracted_information[field.key], ""])
    return "\n".join(lines).rstrip()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/interpret", response_model=InterpretResponse)
def interpret(request: InterpretRequest) -> InterpretResponse:
    return interpret_text(request.text, request.sections)


@app.post("/clarify", response_model=ClarifyResponse)
def clarify(request: ClarifyRequest) -> ClarifyResponse:
    return clarify_text(
        request.source_text,
        request.extracted_information,
        request.answer,
        request.sections,
    )


@app.post("/document", response_model=DocumentResponse)
def document(request: DocumentRequest) -> DocumentResponse:
    document_text = create_documentation(request.extracted_information, request.sections)
    return DocumentResponse(title="General Technical Documentation", document_text=document_text)
