from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class OllamaClient:
    base_url: str = "http://127.0.0.1:11434"
    model: str = "qwen2.5-coder:7b"
    timeout_seconds: int = 30

    def ready(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=2) as response:
                data = json.loads(response.read().decode("utf-8"))
            return any(item.get("name") == self.model for item in data.get("models", []))
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            return False

    def complete(self, prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        return str(data.get("response", "")).strip()
