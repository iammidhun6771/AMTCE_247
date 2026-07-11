import os
import logging
from connectors.gemini import call_gemini
from connectors.kintio_claude import call_kintio_claude

logger = logging.getLogger("SonOfAnton.Validator")

def validate_solution(problem: str, solution: str) -> bool:
    prompt = f"Problem:\n{problem}\n\nProposed Solution:\n{solution}\n\nIs this solution factually and logically correct? Answer YES or NO."
    
    # Try Kintio Claude first if keys are configured
    if os.getenv("KINTIO_API_KEYS"):
        try:
            logger.info("Calling Kintio Claude for validation...")
            res = call_kintio_claude(prompt, system_prompt="You are a strict validator.")
            if "error" not in res and res.get("answer"):
                answer = res["answer"].strip().upper()
                logger.info(f"Kintio Claude validation response: {answer}")
                return answer.startswith("YES")
            logger.warning(f"Kintio Claude failed: {res.get('error')} — falling back to Gemini")
        except Exception as e:
            logger.warning(f"Kintio Claude exception: {e} — falling back to Gemini")
            
    # Fallback to Gemini
    logger.info("Calling Gemini for validation...")
    res = call_gemini(prompt, system_prompt="You are a strict validator.", task_type="ali_reasoning")
    answer = res.get("answer", "").strip().upper()
    return answer.startswith("YES")
