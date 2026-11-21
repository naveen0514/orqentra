"""Optional local Ollama adapter. It is never used for OTPs or secrets."""
import json
import os
import urllib.request


class OptionalLlama:
    def __init__(self):
        self.enabled = os.getenv("ORQENTRA_OLLAMA_ENABLED", "false").lower() in {"1", "true", "yes"}
        self.model = os.getenv("ORQENTRA_OLLAMA_MODEL", "llama3")
        self.host = os.getenv("ORQENTRA_OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")

    def extract_profile(self, text: str, allowed_keys: list[str]) -> dict:
        """Fallback structured extraction for ambiguous user-provided non-secret details."""
        if not self.enabled or not text.strip() or not allowed_keys:
            return {}
        prompt = (
            "Extract only explicitly stated applicant facts from the supplied text. "
            "Do not infer or invent values. Return a JSON object whose keys are selected only from: "
            + ", ".join(allowed_keys)
            + ". If a value is not explicitly present, omit it. Never extract passwords, OTPs, payment data or authentication secrets.\n\n"
            + text[:5000]
        )
        payload = json.dumps({"model": self.model, "prompt": prompt, "stream": False, "format": "json"}).encode()
        request = urllib.request.Request(self.host + "/api/generate", data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                result = json.loads(response.read().decode("utf-8"))
            parsed = json.loads(result.get("response", "{}"))
            if not isinstance(parsed, dict):
                return {}
            return {k: v for k, v in parsed.items() if k in allowed_keys and isinstance(v, (str, int, float, bool)) and str(v).strip()}
        except Exception:
            return {}
