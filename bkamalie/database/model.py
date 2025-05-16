from pydantic import BaseModel
from datetime import datetime, date
from enum import StrEnum


class FineStatus(StrEnum):
    ACCEPTED = "Accepted"
    DECLINED = "Declined"
    PENDING = "Pending"


class FineCategory(StrEnum):
    TRAINING = "Training"
    MATCH = "Match"
    OTHER = "Other"


class Fine(BaseModel):
    id: int | None
    name: str
    fixed_amount: int
    varible_amount: int
    holdbox_amount: int
    description: str
    category: FineCategory


class Payment(BaseModel):
    id: int | None
    member_id: int
    amount: int
    payment_date: datetime
    payment_status: FineStatus


class RecordedFine(BaseModel):
    id: int | None
    fine_id: int
    fixed_count: int
    variable_count: int
    holdbox_count: int
    fined_member_id: int
    fine_date: date
    created_by_member_id: int
    fine_status: FineStatus
    updated_at: datetime
    updated_by_member_id: int
    total_fine: int
    comment: str | None


class User(BaseModel):
    id: int | None
    full_name: str
