#!/usr/bin/env python3
"""
security_guardrails.py — Security & Anti-Hallucination Guardrails for RAG Retrieval.

Copied from role1/security_guardrails.py into the role3_backend package.
Imports updated to use app.schemas (Role 3's unified contract).

Protects the subsystem against:
1. Anti-Hallucination: Grounding score thresholds and citation provenance tracking.
2. SQL Injection: Input sanitization, keyword stripping.
3. Prompt Injection / XSS: Control character stripping, system prompt override protection.
4. Path Traversal: Path normalization and strict boundary verification.
"""

import os
import re
import unicodedata
from pathlib import Path
from typing import Any, List, Optional, Dict

from app.schemas import DocumentChunk, RetrievalError

# Maximum allowed query length to prevent DoS memory amplification
MAX_QUERY_LENGTH = 1000

# SQL Injection threat patterns
_SQL_INJECTION_RE = re.compile(
    r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC|EXECUTE|TRUNCATE|GRANT|REVOKE)\b)|(--|/\*|\*/|;|@@|char|nchar|varchar|nvarchar|cast|convert)",
    re.IGNORECASE,
)

# Prompt Injection threat patterns
_PROMPT_INJECTION_RE = re.compile(
    r"(\[SYSTEM\s*PROMPT\]|IGNORE\s+PREVIOUS\s+INSTRUCTIONS|DISREGARD\s+ALL\s+PRIOR|YOU\s+ARE\nNOW|DAN\s+MODE|ACT\s+AS\s+AN\s+UNRESTRICTED)",
    re.IGNORECASE,
)

# Script & HTML Injection patterns
_HTML_TAG_RE = re.compile(r"<[^>]*?>")
_SCRIPT_PRIMITIVES_RE = re.compile(
    r"\b(alert|eval|prompt|confirm|document\.cookie|window\.location)\s*\(",
    re.IGNORECASE,
)


def sanitize_input_text(text: str, max_length: int = MAX_QUERY_LENGTH) -> str:
    """
    Sanitizes user input queries to prevent SQL injection, prompt injection,
    HTML/XSS injection, and DoS buffer overflow.
    """
    if not text:
        return ""

    # 1. Normalize Unicode (NFC)
    text = unicodedata.normalize("NFC", str(text))

    # 2. Hard length truncation to prevent DoS
    text = text[:max_length]

    # 3. Strip null bytes and non-printable control characters (except space)
    text = "".join(ch for ch in text if ch == " " or not unicodedata.category(ch).startswith("C"))

    # 4. Strip HTML/Script tags & script primitives
    text = _HTML_TAG_RE.sub("", text)
    text = _SCRIPT_PRIMITIVES_RE.sub("[SANITIZED_SCRIPT](", text)

    # 5. Sanitize prompt injection override attempts
    text = _PROMPT_INJECTION_RE.sub("[SANITIZED_INSTRUCTION]", text)

    # 6. Strip raw SQL control syntax
    text = _SQL_INJECTION_RE.sub("", text)

    # 7. Normalize redundant whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def sanitize_file_path(base_dir: str | Path, user_path: str | Path) -> Path:
    """
    Protects against Path Traversal attacks (e.g. ../../../etc/passwd).
    Ensures target_path stays strictly within base_dir.
    """
    base = Path(base_dir).resolve()
    target = (base / user_path).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise RetrievalError(
            f"Path traversal security violation: path '{user_path}' "
            f"escapes base directory '{base}'"
        )
    return target


def filter_anti_hallucination(
    chunks: List[DocumentChunk],
    min_similarity_score: float = 0.15,
) -> List[DocumentChunk]:
    """
    Anti-Hallucination Filter: removes low-confidence vector noise matches.
    Uses effective_score so it works with both Role 1 and Role 3 chunk formats.
    """
    return [c for c in chunks if c.effective_score >= min_similarity_score]


def generate_provenance_citations(chunks: List[DocumentChunk]) -> List[Dict[str, Any]]:
    """
    Generates strict provenance metadata (citation links) for each retrieved chunk
    so downstream LLM responses can cite exact source documents.
    """
    citations = []
    for idx, c in enumerate(chunks, 1):
        citations.append({
            "citation_id": f"[{idx}]",
            "doc_id": c.doc_id,
            "chunk_id": c.chunk_id,
            "score": round(c.effective_score, 4),
            "lang": c.lang,
            "query_type": c.query_type,
            "is_ground_truth": c.is_selected,
            "snippet": c.text[:120] + "..." if len(c.text) > 120 else c.text,
        })
    return citations
