from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple


class ProviderAdapter(ABC):
    name: str

    @abstractmethod
    async def chat_completions(self, payload: Dict[str, Any], api_key: str, base_url: str) -> Tuple[Dict[str, Any], Dict[str, int]]:
        raise NotImplementedError

    @abstractmethod
    def normalize_error(self, exception_or_response: Any) -> Dict[str, Any]:
        raise NotImplementedError

