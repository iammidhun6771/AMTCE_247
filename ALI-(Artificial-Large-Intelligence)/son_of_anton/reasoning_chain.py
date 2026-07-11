import logging
from connectors.groq_connector import call_groq
from connectors.hf_governor import hf_governor

logger = logging.getLogger("SonOfAnton.ReasoningChain")

def anton_deep_reason(problem: str) -> str:
    """
    Cascading reasoner: Groq (Llama 3.3 70B) → HuggingFace (Qwen 72B).
    DeepSeek removed — free tier discontinued.
    """
    prompt = f"Solve the following hard problem comprehensively:\n{problem}"
    system_prompt = "You are Son of Anton. Apply brute-force logical reasoning. Think step by step before giving your final answer."

    # Tier 1: Groq — fastest free reasoning (Llama 3.3 70B, ~14,400 req/day free)
    try:
        res = call_groq(prompt, system_prompt, model="llama-3.3-70b-versatile")
        if "error" not in res and res.get("answer"):
            logger.info("[SonOfAnton] Reasoned via Groq (Llama 3.3 70B)")
            return res["answer"]
        logger.warning(f"[SonOfAnton] Groq failed: {res.get('error')} — falling back to HF")
    except Exception as e:
        logger.warning(f"[SonOfAnton] Groq exception: {e} — falling back to HF")

    # Tier 2: HuggingFace Qwen 72B — SOTA open-source reasoner
    try:
        res = hf_governor.call(prompt, system_prompt, task_type="ali_reasoning")
        if "error" not in res and res.get("answer"):
            logger.info("[SonOfAnton] Reasoned via HF Governor (Qwen 72B)")
            return res["answer"]
        logger.error(f"[SonOfAnton] HF Governor also failed: {res.get('error')}")
    except Exception as e:
        logger.error(f"[SonOfAnton] HF Governor exception: {e}")

    return ""
