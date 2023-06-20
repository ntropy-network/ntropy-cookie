from datetime import date
from typing import TypedDict


class Transaction(TypedDict):
    date: date
    description: str
    amount: float
    iso_currency_code: str


class EnrichedTransaction(Transaction):
    merchant: str | None
    website: str | None
    labels: str | None
    location: str | None


class UnregisteredUser(Exception):
    pass
