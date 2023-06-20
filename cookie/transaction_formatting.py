from more_itertools import unzip
from tabulate import tabulate

from cookie.transactions import EnrichedTransaction, Transaction

transaction_fields = [
    ("date", "Date"),
    ("description", "Description"),
    ("amount", "Amount"),
    ("iso_currency_code", "Currency"),
    ("merchant", "Merchant"),
    ("website", "Website"),
    ("labels", "Labels"),
    ("location", "Location"),
]

field_keys = list(list(unzip(transaction_fields))[0])
field_headers = list(list(unzip(transaction_fields))[1])


def _transactions_to_rows(
    transactions: list[Transaction | EnrichedTransaction],
) -> list[tuple]:
    return [tuple(tx[k] for k in field_keys if k in tx) for tx in transactions]


def table_format_transactions(
    transactions: list[Transaction | EnrichedTransaction],
) -> str:
    rows = _transactions_to_rows(transactions)
    table = tabulate(tabular_data=rows, headers=field_headers)
    return table


def prompt_format_transactions(
    transactions: list[EnrichedTransaction],
) -> str:
    grouped_transactions: dict[str, EnrichedTransaction] = {}
    for transaction in transactions:
        key = (
            transaction["description"]
            if transaction["merchant"] is None
            else transaction["merchant"]
        )

        if key not in grouped_transactions:
            grouped_transactions[key] = []
        grouped_transactions[key].append(transaction)

    s = ""
    for key, transaction_group in grouped_transactions.items():
        s += (
            key
            + (
                (" " + transaction_group[0]["website"])
                if transaction_group[0]["website"]
                else ""
            )
            + (
                (" " + transaction_group[0]["location"])
                if transaction_group[0]["location"]
                else ""
            )
            + "\n"
        )
        for transaction in transaction_group:
            s += (
                str(transaction["date"])
                + " "
                + str(transaction["amount"])
                + transaction["iso_currency_code"]
                + " "
                + transaction["labels"]
                + "\n"
            )

        s += "\n"
    return s
