import json
import uuid
from datetime import date
from functools import partial
from typing import Iterable

from cachetools import LRUCache, cached
from ntropy_sdk import SDK
from ntropy_sdk import EnrichedTransaction as NtropyEnrichedTransaction
from ntropy_sdk import Transaction as NtropyTransaction

from cookie.transactions import EnrichedTransaction, Transaction

sdk = SDK()


def transaction_to_ntropy(
    transaction: Transaction, account_holder_id: str
) -> NtropyTransaction:
    signed_amount = transaction["amount"]
    return NtropyTransaction(
        amount=abs(signed_amount),
        description=transaction["description"],
        entry_type="incoming" if signed_amount > 0 else "outgoing",
        iso_currency_code=transaction["iso_currency_code"],
        date=transaction["date"].isoformat(),
        account_holder_type="consumer",
        account_holder_id=account_holder_id,
    )


def enriched_transaction_from_ntropy(
    transaction_pair: tuple[NtropyTransaction, NtropyEnrichedTransaction]
) -> EnrichedTransaction:
    transaction, enriched_transaction = transaction_pair
    return {
        "amount": transaction.amount
        * (1 if transaction.entry_type == "incoming" else -1),
        "date": date.fromisoformat(transaction.date),
        "iso_currency_code": transaction.iso_currency_code,
        "description": transaction.description,
        "labels": "-".join(enriched_transaction.labels),
        "location": enriched_transaction.location,
        "merchant": enriched_transaction.merchant,
        "website": enriched_transaction.website,
    }


def _make_serializable_tx(tx: Transaction):
    serializable_tx = tx.copy()
    serializable_tx["date"] = serializable_tx["date"].isoformat()
    return serializable_tx


@cached(
    LRUCache(maxsize=256),
    key=lambda transactions: json.dumps(list(map(_make_serializable_tx, transactions))),
)
def enrich(transactions: Iterable[Transaction]) -> list[NtropyEnrichedTransaction]:
    ntropy_transactions = list(
        map(
            partial(transaction_to_ntropy, account_holder_id=str(uuid.uuid4())),
            transactions,
        )
    )
    enriched = sdk.add_transactions(ntropy_transactions)
    return list(
        map(enriched_transaction_from_ntropy, zip(ntropy_transactions, enriched))
    )
