from pydantic import BaseModel
from datetime import datetime, date
from enum import StrEnum, Enum


class FineStatus(StrEnum):
    ACCEPTED = "Accepted"
    DECLINED = "Declined"
    PENDING = "Pending"


class FineCategory(StrEnum):
    TRAINING = "Training"
    MATCH = "Match"
    OTHER = "Other"


class Teams(Enum):
    BOLDKLUBBEN_AMALIE = 5289  # Mens Team
    AMALIE_KVINDER = 53781
    AMALIE_OLD_BOYS = 649608


class Fine(BaseModel):
    id: int | None = None
    name: str
    fixed_amount: int
    variable_amount: int
    holdbox_amount: int
    description: str | None
    category: FineCategory
    team_id: int


class Payment(BaseModel):
    id: int | None
    member_id: int
    amount: int
    payment_date: datetime
    payment_status: FineStatus
    team_id: int


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
    team_id: int


class User(BaseModel):
    id: int | None
    full_name: str


class Team(BaseModel):
    id: int
    name: str
