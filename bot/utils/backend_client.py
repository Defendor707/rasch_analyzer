import os
from typing import Any, Dict, Optional

import httpx


class BackendClient:
    def __init__(self, base_url: Optional[str] = None, enabled: Optional[bool] = None) -> None:
        self.base_url = base_url or os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
        self.enabled = (
            (os.getenv("FEATURE_BACKEND_ENABLED", "0") in {"1", "true", "True"})
            if enabled is None
            else enabled
        )
        self._client = httpx.Client(timeout=10.0)

    def is_enabled(self) -> bool:
        return self.enabled

    def health(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled"}
        r = self._client.get(f"{self.base_url}/health")
        r.raise_for_status()
        return r.json()

    def finalize_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled"}
        r = self._client.post(f"{self.base_url}/v1/analysis/finalize", json=payload)
        if r.status_code == 501:
            return {"status": "not_implemented"}
        r.raise_for_status()
        return r.json()


