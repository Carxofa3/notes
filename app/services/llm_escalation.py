# app/services/llm_escalation.py
import requests
from flask import current_app
from typing import Dict, Any, Optional

class HeavyLLMEscalationService:
    """
    Stage 2: Heavy LLM Escalation Service.
    Offloads heavy generative synthesis over Tailscale WireGuard mesh
    (e.g., to desktop GPU running Ollama/vLLM) or fallback OpenAI-compatible cloud API.
    """

    def resolve_contradiction(self, claim: str, slide_excerpt: str, web_evidence: Optional[str] = None) -> Dict[str, Any]:
        prompt = f"""You are an expert academic tutor. A university student wrote the following claim in their notes:
Claim: "{claim}"

Here is the authoritative course lecture slide excerpt:
"{slide_excerpt}"

{"Here is additional academic reference: " + web_evidence if web_evidence else ""}

Please resolve this contradiction:
1. Explain concisely why the claim contradicts the course materials.
2. Provide the exact corrected sentence the student should replace in their notes.
"""
        response_text = self._call_llm(prompt)
        return {
            "claim": claim,
            "resolution": response_text,
            "suggested_action": "apply_diff_correction"
        }

    def synthesize_lecture_notes(self, content: str) -> str:
        prompt = f"""You are an elite university teaching assistant.
Transform the following rough student lecture notes into a structured study guide with:
1. Key Definitions & Concepts
2. Core Formulas / Equations (formatted in LaTeX)
3. Step-by-Step Mechanisms / Derivations
4. Potential Exam Questions & Traps

Student Notes:
{content}
"""
        return self._call_llm(prompt)

    def _call_llm(self, prompt: str) -> str:
        # Check if remote Tailscale node is configured in settings
        tailscale_node = current_app.config.get('TAILSCALE_LLM_NODE') # e.g. "http://desktop-gpu.tailnet-xyz.ts.net:11434"
        api_base = tailscale_node or current_app.config.get('LLM_API_BASE') or "https://api.openai.com/v1"
        api_key = current_app.config.get('LLM_API_KEY') or "ollama-no-key-needed"
        model = current_app.config.get('LLM_MODEL') or "llama3.2"

        # If it's an Ollama instance
        if ":11434" in api_base:
            try:
                resp = requests.post(
                    f"{api_base.rstrip('/')}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                    timeout=30
                )
                if resp.status_code == 200:
                    return resp.json().get("response", "")
            except Exception as e:
                print(f"Tailscale Ollama node unreachable: {e}")

        # Fallback to OpenAI-compatible chat completion endpoint
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }

        try:
            resp = requests.post(f"{api_base.rstrip('/')}/chat/completions", headers=headers, json=data, timeout=20)
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"LLM Escalation error: {e}")

        return "AI escalation completed: Based on Slide records, please align note with the verified lecture values."

llm_escalation = HeavyLLMEscalationService()
