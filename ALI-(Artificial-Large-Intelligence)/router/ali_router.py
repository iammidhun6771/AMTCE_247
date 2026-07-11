import json
from typing import Dict, Any
from connectors.mistral import call_mistral

def classify_task(prompt: str) -> Dict[str, Any]:
    system_prompt = """
    You are the ALI task router. Classify the user's prompt into one of the following categories:
    - "code" (programming, logic, math, debugging)
    - "vision" (images, visual descriptions requested)
    - "multilingual" (translation, non-English)
    - "factual" (history, science, objective facts)
    - "creative" (storytelling, opinion, casual chat)
    
    Return ONLY valid JSON:
    {
        "category": "code | vision | multilingual | factual | creative"
    }
    """
    
    result = call_mistral(prompt, system_prompt)
    if "error" in result:
        return {"category": "creative", "error": result["error"]}
        
    try:
        content = result["answer"].strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        return data
    except Exception:
        return {"category": "creative", "error": "parse_error"}

def get_routing_plan(category: str, emotion_data: Dict[str, Any]) -> Dict[str, str]:
    emotion = emotion_data.get("emotion", "neutral")

    # Model waterfall (DeepSeek removed — free tier discontinued):
    #   code       → groq:Qwen2.5-Coder-32B  (beats GPT-4o on HumanEval)
    #   vision     → gemini                   (multimodal, only option)
    #   multilingual → qwen                   (HF Qwen 72B, best multilingual)
    #   factual    → qwen                     (HF Command-R+, RAG specialist)
    #   creative   → mistral                  (fast, expressive)
    if category == "code":
        lead = "groq"        # Qwen2.5-Coder-32B via Groq
    elif category == "vision":
        lead = "gemini"
    elif category == "multilingual":
        lead = "qwen"
    elif category == "factual":
        lead = "qwen"
    else:
        lead = "mistral"
        
    # Emotion overrides
    if emotion in ["sad", "crisis"]:
        lead = "mistral"
    elif emotion == "frustrated" and category == "code":
        # On frustration, still use best coder (Qwen via Groq)
        lead = "groq"
    elif emotion == "curious":
        # Exploratory reasoning: Llama 3.3 70B on Groq (was DeepSeek-Reasoner)
        lead = "groq"
        
    return {
        "lead_model": lead,
        "category": category,
        "emotion_override": emotion if emotion != "neutral" else None
    }
