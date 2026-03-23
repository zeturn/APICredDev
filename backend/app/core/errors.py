from typing import Any, Dict
from uuid import UUID


class AppError(Exception):
    def __init__(self, code: str, message: str, request_id: UUID, status_code: int = 400):
        self.code = code
        self.message = message
        self.request_id = request_id
        self.status_code = status_code
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "request_id": str(self.request_id),
            }
        }

