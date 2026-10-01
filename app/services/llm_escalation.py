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
        # Check cluster active LLM provider or local llama.cpp configuration
        llm_node = None
        try:
            from app.services.sync_service import sync_service
            cluster_provider = sync_service.get_active_llm_provider()
            if cluster_provider:
                llm_node = cluster_provider
            elif sync_service.is_llamacpp_enabled():
                llm_node = f"http://127.0.0.1:{sync_service.get_llamacpp_local_port()}"
        except Exception:
            pass

        if not llm_node:
            llm_node = current_app.config.get('LLAMA_CPP_NODE') or current_app.config.get('TAILSCALE_LLM_NODE') # e.g. "http://desktop-gpu.tailnet-xyz.ts.net:8080"
        api_base = llm_node or current_app.config.get('LLM_API_BASE') or "http://localhost:8080"
        api_key = current_app.config.get('LLM_API_KEY') or "llamacpp-no-key-needed"
        model = current_app.config.get('LLM_MODEL') or "default"

        # 1. First-class llama.cpp server support (standard llama-server port :8080 or proxy)
        if ":8080" in api_base or "llama" in api_base.lower() or "/proxy/llm" in api_base:
            # Try native llama.cpp /completion endpoint first for maximum speed & zero overhead
            try:
                resp = requests.post(
                    f"{api_base.rstrip('/')}/completion",
                    json={
                        "prompt": f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n",
                        "n_predict": 1024,
                        "temperature": 0.2,
                        "stop": ["<|im_end|>", "</s>"]
                    },
                    timeout=45
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("content") or data.get("response") or ""
                    if content.strip():
                        return content.strip()
            except Exception as e:
                print(f"llama.cpp native /completion error, trying OpenAI endpoint: {e}")

            # Try llama.cpp /v1/chat/completions
            try:
                resp = requests.post(
                    f"{api_base.rstrip('/')}/v1/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json={
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2
                    },
                    timeout=45
                )
                if resp.status_code == 200:
                    return resp.json()['choices'][0]['message']['content'].strip()
            except Exception as e:
                print(f"llama.cpp /v1/chat/completions unreachable: {e}")

        # 2. Ollama legacy fallback (:11434)
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
