ALLOWED_OPS = {"list_companies", "ledger_balance", "day_book", "trial_balance", "probe"}


def assert_op_allowed(op: str) -> None:
    if op not in ALLOWED_OPS:
        raise ValueError(f"op not allowed: {op}")
