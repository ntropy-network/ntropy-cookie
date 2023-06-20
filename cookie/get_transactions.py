import json
from datetime import date

from cookie.transactions import Transaction, UnregisteredUser
from cookie.user_store import User


def get_transactions(user: User, n: int) -> list[Transaction]:
    if user.cached_txs_json:
        txs = json.loads(user.cached_txs_json)
        for tx in txs:
            tx["date"] = date.fromisoformat(tx["date"])
        txs = sorted(txs, key=lambda tx: tx["date"])
        return txs[-n:]
    else:
        raise UnregisteredUser()
