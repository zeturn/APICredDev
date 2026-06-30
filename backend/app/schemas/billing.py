from pydantic import BaseModel


class WalletResponse(BaseModel):
    balance_credits: float
    updated_at: str


class LedgerItem(BaseModel):
    id: str
    entry_type: str
    amount_credits: float
    status: str
    ref_type: str
    ref_id: str
    meta: dict
    created_at: str

