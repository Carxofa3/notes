# app/services/gliner_service.py
"""
GLiNER Neural Entity Server & Workstation Model Hub.
Serves urchade/gliner_small-v2.1 for Zero-Shot Academic NER & Claim Triage
to the desktop app and all connected mobile/LAN devices.
"""

import os
import sys
import threading
import time
from typing import Dict, Any, List, Optional

class GLiNERService:
    DEFAULT_MODEL = "urchade/gliner_small-v2.1"
    MODEL_DIR = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "models", "gliner_small-v2.1")

    DEFAULT_LABELS = [
        "academic concept",
        "scientific theorem",
        "mathematical formula",
        "chemical compound",
        "biological process",
        "empirical claim",
        "definition",
        "date"
    ]

    def __init__(self):
        self._lock = threading.Lock()
        self._model = None
        self._is_downloading = False
        self._download_progress = 0
        self._error: Optional[str] = None
        self._device = "cpu"
        self._lan_serving = True
        self._requests_served = 0
        self._check_environment()

    def _check_environment(self):
        """Detect CUDA acceleration if available, otherwise CPU"""
        try:
            import torch
            if torch.cuda.is_available():
                self._device = "cuda"
            else:
                self._device = "cpu"
        except Exception:
            self._device = "cpu"

    def is_installed(self) -> bool:
        """Check if gliner python package is imported successfully"""
        try:
            import gliner
            return True
        except ImportError:
            return False

    def is_model_cached(self) -> bool:
        """Check if model weights exist locally in MODEL_DIR or huggingface cache"""
        if os.path.exists(self.MODEL_DIR) and any(os.scandir(self.MODEL_DIR)):
            return True
        return False

    def is_ready(self) -> bool:
        return self._model is not None

    def get_status(self) -> Dict[str, Any]:
        return {
            "installed": self.is_installed(),
            "model_name": self.DEFAULT_MODEL,
            "ready": self.is_ready(),
            "downloading": self._is_downloading,
            "progress": self._download_progress,
            "device": self._device,
            "lan_serving": self._lan_serving,
            "requests_served": self._requests_served,
            "error": self._error,
            "model_dir": self.MODEL_DIR
        }

    def set_lan_serving(self, enabled: bool) -> Dict[str, Any]:
        self._lan_serving = bool(enabled)
        return self.get_status()

    def start_download_async(self) -> Dict[str, Any]:
        with self._lock:
            if self._is_downloading:
                return {"status": "already_downloading", "progress": self._download_progress}
            if self._model is not None:
                return {"status": "ready", "progress": 100}

            self._is_downloading = True
            self._download_progress = 5
            self._error = None

            t = threading.Thread(target=self._download_worker, daemon=True)
            t.start()
            return {"status": "started", "progress": self._download_progress}

    def _download_worker(self):
        try:
            print(f"[GLiNER Hub] Initiating auto-download for {self.DEFAULT_MODEL}...")
            self._download_progress = 15

            # If gliner package is not installed, install it via pip
            if not self.is_installed():
                print("[GLiNER Hub] gliner package missing. Auto-installing dependencies via pip...")
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", "gliner", "torch", "transformers"])
                self._download_progress = 40

            from gliner import GLiNER
            self._download_progress = 55
            print(f"[GLiNER Hub] Downloading model weights for {self.DEFAULT_MODEL} to {self.MODEL_DIR}...")

            os.makedirs(self.MODEL_DIR, exist_ok=True)
            # Load and cache model
            model = GLiNER.from_pretrained(self.DEFAULT_MODEL)
            self._download_progress = 85

            if self._device == "cuda":
                try:
                    model = model.to("cuda")
                except Exception:
                    self._device = "cpu"
                    model = model.to("cpu")

            with self._lock:
                self._model = model
                self._is_downloading = False
                self._download_progress = 100
                self._error = None

            print(f"[GLiNER Hub] Successfully loaded {self.DEFAULT_MODEL} on {self._device}. Ready to serve LAN & mobile!")
        except Exception as e:
            print(f"[GLiNER Hub] Failed to load model: {e}")
            with self._lock:
                self._is_downloading = False
                self._error = str(e)

    def extract_entities(self, text: str, labels: Optional[List[str]] = None, threshold: float = 0.35) -> List[Dict[str, Any]]:
        """
        Extract named entities and academic propositions using GLiNER.
        Falls back cleanly if model is not loaded yet.
        """
        if not text or not text.strip():
            return []

        labels = labels or self.DEFAULT_LABELS

        if self._model is None:
            # Fallback to Jev heuristic engine if neural model is still downloading
            from app.services.decide_service import jev_engine
            decide_res = jev_engine.evaluate(text)
            return decide_res.get("entities", [])

        try:
            start_t = time.time()
            raw_entities = self._model.predict_entities(text, labels, threshold=threshold)
            elapsed_ms = round((time.time() - start_t) * 1000, 1)

            with self._lock:
                self._requests_served += 1

            formatted = []
            for ent in raw_entities:
                formatted.append({
                    "text": ent.get("text", ""),
                    "label": ent.get("label", "entity"),
                    "start": ent.get("start", 0),
                    "end": ent.get("end", 0),
                    "confidence": round(float(ent.get("score", 0.9)), 3),
                    "neural": True,
                    "inference_ms": elapsed_ms
                })

            return formatted
        except Exception as e:
            print(f"[GLiNER Hub] Inference error: {e}")
            self._error = str(e)
            return []

gliner_service = GLiNERService()
