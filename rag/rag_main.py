"""Standalone Phase-1 RAG test runner.

Keeps AMTCE main pipeline untouched. Run with:
    python rag_main.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path
root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from Diagnostics_Modules.gemini_trace import GeminiTrace
import google.generativeai as genai

# ==================== GEMINI FORENSIC PATCH ====================
_original_generate = genai.GenerativeModel.generate_content

def patched_generate(self, *args, **kwargs):
    model_name = getattr(self, "model_name", "unknown")
    start = GeminiTrace.log_start(model_name, args, kwargs)
    result = _original_generate(self, *args, **kwargs)
    GeminiTrace.log_end(start)
    return result

genai.GenerativeModel.generate_content = patched_generate
# =============================================================

from analyzer.hybrid_analyzer import HybridAnalyzer
from decision.decision_engine import generate_with_rag, generate_without_rag
from rag.chroma_client import get_collection
from rag.dataset_loader import load_dataset, normalize_text
from rag.retriever import get_top_patterns

def build_query(profile: dict) -> str:
    query = f"{profile['category']} {profile['energy']} {profile['pace']} {profile['style']} short-form editing strategy"
    return query


def main():
    print("Starting RAG test (Ph-2 Hybrid Analyzer)...")
    
    # 1) Setup Environment
    env_path = Path(__file__).resolve().parent.parent / "Credentials" / ".env"
    load_dotenv(dotenv_path=env_path)

    # 2) Initialize Chroma
    collection = get_collection()

    # 3) Load dataset
    print("Loading dataset...")
    load_dataset(collection, clear=True)

    # 4) Hybrid Clip Analysis
    print("Performing Hybrid Analysis...")
    simulated_signals = {
        "energy": "high",
        "pace": "fast",
        "motion_intensity": "high",
        "cut_density": "high"
    }
    analyzer = HybridAnalyzer()
    profile = analyzer.analyze(simulated_signals)
    print(f"[INFO] Hybrid Profile: {profile}")

    # 5) Build query
    print("Building query...")
    query = build_query(profile)
    
    # REQUIRED DEBUG PRINTS
    print("DEBUG PROFILE:", profile)
    print("DEBUG QUERY:", query)

    # 6) Retrieve patterns
    print("Retrieving patterns...")
    patterns = get_top_patterns(collection, query, profile, k=3)
    print(f"[INFO] Retrieved items: {len(patterns)}")

    # 8) Gemini generations
    print("Running Gemini WITHOUT RAG...")
    output_no_rag = generate_without_rag(profile)
    
    print("Running Gemini WITH RAG...")
    output_with_rag = generate_with_rag(profile, patterns)

    # 9) Print outputs (Single execution block)
    print("\n=== WITHOUT RAG ===")
    print(output_no_rag)

    print("\n=== WITH RAG ===")
    print(output_with_rag)

    print("\n=== RETRIEVED PATTERNS ===")
    if not patterns:
        print("No patterns retrieved")
    else:
        for idx, item in enumerate(patterns, start=1):
            print(f"Pattern {idx}:")
            print(f"  Text: {item.get('text', '')}")
            print(f"  Metadata: {item.get('metadata', {})}")
            if item.get("score") is not None:
                print(f"  Score: {item['score']:.4f}")
            if item.get("distance") is not None:
                print(f"  Distance: {item['distance']:.4f}")
            print()

    print("NOTE: Compare outputs manually for specificity, creativity, hook strength.")
    GeminiTrace.print_summary()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] RAG test failed: {exc}")
