from typing import Any


class OrderResponseParseError(Exception):
    """Raised when IB returns a 2xx order response we cannot parse.

    The order may already be placed on IB's side at this point, so callers
    should treat this as "outcome unknown" (reconcile via order status) rather
    than "placement failed". The raw payload is attached for reconciliation.
    """

    def __init__(self, payload: Any) -> None:
        self.payload = payload
        super().__init__(f"Could not parse place order response: {payload!r}")
