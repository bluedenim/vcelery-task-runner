from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PaymentMethod(Enum):
    """
    Different payment methods we support
    """
    CASH = "CASH"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    COMP = "COMP"


class Payment(BaseModel):
    """
    A payment DTO
    """
    amount: int = Field(gt=0)
    method: PaymentMethod
    payment_dt: datetime
