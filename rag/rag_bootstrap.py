"""
RAG Bootstrap Module
--------------------
Ensures the Chroma collection is populated before any query runs.
The Chroma store is persistent on disk, but a fresh install will have
an empty collection. This module detects that and lazily loads the
curated dataset so the pipeline always has retrieval patterns.

Usage (called automatically by editor_brain.py):
    from rag.rag_bootstrap import ensure_collection_ready
    ensure_collection_ready(collection)
"""

from __future__ import annotations

import logging

logger = logging.getLogger("rag_bootstrap")

# Process-level flag — avoids repeated heavy disk checks
_bootstrapped: bool = False


def ensure_collection_ready(collection) -> bool:
    """
    Idempotent bootstrap: checks whether the collection has documents.
    If empty, loads the curated editing-patterns dataset.

    Returns True  → collection has data and is query-ready.
    Returns False → bootstrap failed (pipeline degrades gracefully).
    """
    global _bootstrapped

    if _bootstrapped:
        return True

    try:
        existing = collection.get()
        count = len(existing.get("ids", []) or [])

        if count > 0:
            logger.info(
                f"[RAG_BOOTSTRAP] Collection already populated "
                f"({count} patterns). Skipping load."
            )
            _bootstrapped = True
            return True

        # Collection is empty — load the curated dataset
        logger.info(
            "[RAG_BOOTSTRAP] Collection is empty. "
            "Loading curated editing-patterns dataset..."
        )
        from rag.dataset_loader import load_dataset

        # clear=False because we just verified the collection is empty
        load_dataset(collection, clear=False)

        # Verify load succeeded
        check = collection.get()
        loaded = len(check.get("ids", []) or [])
        if loaded > 0:
            logger.info(
                f"[RAG_BOOTSTRAP] Dataset loaded successfully. "
                f"{loaded} patterns available."
            )
            _bootstrapped = True
            return True

        logger.warning(
            "[RAG_BOOTSTRAP] load_dataset completed but collection is still empty. "
            "RAG queries will return no results."
        )
        return False

    except Exception as exc:
        logger.error(
            f"[RAG_BOOTSTRAP] Bootstrap failed (non-fatal): {exc}. "
            "Pipeline will continue without RAG patterns."
        )
        return False


def get_ready_collection(collection_name: str = "editing_patterns"):
    """
    Convenience wrapper: get a collection that is guaranteed to have data.

    Returns the Chroma collection (populated) or None on failure.
    Callers should check for None and degrade gracefully.
    """
    try:
        from rag.chroma_client import get_collection

        collection = get_collection(collection_name)
        ensure_collection_ready(collection)
        return collection
    except Exception as exc:
        logger.error(f"[RAG_BOOTSTRAP] Cannot initialise collection: {exc}")
        return None


def reset_bootstrap_flag() -> None:
    """
    Force a re-check on next call to ensure_collection_ready.
    Useful in tests or after manually clearing the Chroma store.
    """
    global _bootstrapped
    _bootstrapped = False
