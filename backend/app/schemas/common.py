from pydantic import BaseModel


class ErrorInfo(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorInfo

