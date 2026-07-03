"""Ingestion service (Phase 1).

Contract: every ingest run must (1) verify the source is registered and
policy-approved, (2) store raw bytes with SHA-256 in SourceDocument,
(3) respect the source's rate limits and terms. See DATA_SOURCE_POLICY.md.
"""

import hashlib


def sha256_bytes(data: bytes) -> str:
    """Chain-of-custody hash applied to every retrieved artifact."""
    return hashlib.sha256(data).hexdigest()
