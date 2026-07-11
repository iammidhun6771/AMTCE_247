from typing import Dict, Any, List
from connectors.gemini import call_gemini
from connectors.groq_connector import call_groq
from connectors.mistral import call_mistral
from emotion.adapter import adapt_prompt_with_emotion

def execute_vision_chain(prompt: str, images: List[Any], emotion_data: Dict[str, Any]) -> Dict[str, Any]:
    # Adjust prompt
    adjusted_prompt = adapt_prompt_with_emotion(prompt, emotion_data)
    
    # In a real implementation with `google-genai`, `contents` can accept a list of text + PIL images.
    print("Executing Vision Model (Gemini)...")
    gemini_prompt = [adjusted_prompt] + images
    res_gemini = call_gemini(gemini_prompt, system_prompt="You are a Vision AI. Analyze the images and answer the prompt.", task_type="ali_vision")
    vision_analysis = res_gemini.get("answer", "")
    
    # Groq reasons about what Gemini saw (replaced DeepSeek — free tier discontinued)
    print("Executing Reasoning Model (Groq: Llama 3.3 70B)...")
    groq_prompt = f"User asked: {prompt}\n\nVision Analysis:\n{vision_analysis}\n\nPlease reason about this visual analysis and provide a deeper logical conclusion."
    res_groq = call_groq(groq_prompt, system_prompt="You are a logical reasoner. Analyze the provided visual context.", model="llama-3.3-70b-versatile")
    reasoning = res_groq.get("answer", "")
    
    # Mistral synthesizes
    print("Executing Synthesis Model (Mistral)...")
    mistral_prompt = f"Synthesize a final response based on the logical reasoning:\n{reasoning}"
    res_mistral = call_mistral(mistral_prompt, system_prompt="You are the final synthesizer. Make the answer clear and human-friendly.")
    
    return {
        "final_answer": res_mistral.get("answer", ""),
        "chain_trace": {
            "gemini_vision": vision_analysis,
            "groq_reasoning": reasoning,        # was deepseek_reasoning
            "mistral_synthesis": res_mistral.get("answer", "")
        }
    }
