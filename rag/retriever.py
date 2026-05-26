"""Retriever utilities for the RAG prototype."""

from __future__ import annotations

from typing import List, Dict

from rag.dataset_loader import normalize_text


def get_top_patterns(collection, query: str, profile: dict, k: int = 3) -> List[Dict]:
    """Query the collection, filter hard constraints, and re-rank with attribute scores."""

    normalized_query = normalize_text(query)
    # Fetch a larger pool of candidates for filtering and re-ranking
    results = collection.query(
        query_texts=[normalized_query],
        n_results=15,
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents", [[]])[0] if results else []
    metadatas = results.get("metadatas", [[]])[0] if results else []
    distances = results.get("distances", [[]])[0] if results else []

    query_energy = profile.get("energy", "").lower()
    query_pace = profile.get("pace", "").lower()

    # 1. Hard Constraints Filter
    filtered_docs = []
    filtered_metas = []
    filtered_dists = []
    removed_count = 0

    for doc, meta, dist in zip(documents, metadatas, distances):
        pat_energy = meta.get("energy", "").lower()
        pat_pace = meta.get("pace", "").lower()

        # Check opposites
        remove = False
        if query_energy == "high" and pat_energy == "low": remove = True
        elif query_energy == "low" and pat_energy == "high": remove = True
        elif query_pace == "fast" and pat_pace == "slow": remove = True
        elif query_pace == "slow" and pat_pace == "fast": remove = True

        if remove:
            removed_count += 1
        else:
            filtered_docs.append(doc)
            filtered_metas.append(meta)
            filtered_dists.append(dist)

    if removed_count > 0:
        print(f"[RAG_FILTER] removed_patterns={removed_count} reason=energy/pace mismatch")

    # 2. Attribute-Aware Scoring
    def get_match_score(pattern_val: str, query_val: str, scale_type: str) -> float:
        if not pattern_val or not query_val: return 0.0
        if pattern_val == query_val: return 1.0
        
        if scale_type == "energy": scale = ["low", "medium", "high"]
        elif scale_type == "pace": scale = ["slow", "steady", "fast"]
        else: return 0.0

        if pattern_val in scale and query_val in scale:
            if abs(scale.index(pattern_val) - scale.index(query_val)) == 1:
                return 0.5
        return 0.0

    reranked = []
    for doc, meta, dist in zip(filtered_docs, filtered_metas, filtered_dists):
        embed_sim = 1 / (1 + dist) if dist is not None else 0.0
        
        pat_energy = meta.get("energy", "").lower()
        pat_pace = meta.get("pace", "").lower()
        
        energy_match = get_match_score(pat_energy, query_energy, "energy")
        pace_match = get_match_score(pat_pace, query_pace, "pace")
        
        final_score = 0.6 * embed_sim + 0.2 * energy_match + 0.2 * pace_match
        
        pattern_id = f"{meta.get('category', 'unknown')}-{pat_energy}-{pat_pace}"
        print(f"[RAG_RERANK] pattern={pattern_id} embed={embed_sim:.4f} energy={energy_match:.1f} pace={pace_match:.1f} final={final_score:.4f}")
        
        reranked.append({
            "text": doc,
            "metadata": meta,
            "distance": dist,
            "score": final_score,
            "embed_sim": embed_sim,
            "energy_match": energy_match,
            "pace_match": pace_match
        })

    # 3. Sort by final score and select top_k
    reranked.sort(key=lambda x: x["score"], reverse=True)
    return reranked[:k]
