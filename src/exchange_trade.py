"""Gələcək order modulu — HƏLƏLİK STUB.

Qayda: real order yalnız sənin açıq təsdiqinlə.
`confirm="yes"` gəlməsə, heç bir order göndərilmir.
Default hər şey dry-run-dur.
"""
from dataclasses import dataclass


@dataclass
class OrderRequest:
    symbol: str
    side: str  # buy / sell
    amount: float
    confirm: str = ""  # must be exactly "yes" to proceed


def place_order(req: OrderRequest, dry_run: bool = True) -> dict:
    if req.confirm != "yes":
        return {
            "status": "blocked",
            "reason": "İstifadəçi təsdiqi yoxdur (confirm='yes' lazımdır).",
            "order": None,
        }
    if dry_run:
        return {
            "status": "dry-run",
            "reason": "DRY_RUN=true — birjaya göndərilmədi, yalnız simulyasiya.",
            "order": {"symbol": req.symbol, "side": req.side, "amount": req.amount},
        }
    # Mərhələ 2-də bura ccxt create_order gələcək.
    return {"status": "not-implemented", "reason": "Live trade hələ qoşulmayıb.", "order": None}
