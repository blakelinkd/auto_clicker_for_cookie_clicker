from typing import Any, Callable


def build_upgrade_diag(
    snapshot: dict[str, Any] | None,
    *,
    resolve_candidate_metrics: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any] | None],
    estimate_attached_wrinkler_bank: Callable[[dict[str, Any]], float],
    afford_horizon_seconds: float,
    auto_buy_payback_seconds: float,
    cheap_upgrade_sweep_ratio: float,
) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {"available": False, "reason": "no_snapshot"}

    raw_upgrades = snapshot.get("upgrades")
    if not isinstance(raw_upgrades, list):
        return {"available": False, "reason": "no_upgrade_data"}

    upgrades = [item for item in raw_upgrades if isinstance(item, dict)]
    candidate_upgrades = [item for item in upgrades if item.get("pool") not in {"toggle", "tech"}]
    affordable = sum(
        1
        for item in candidate_upgrades
        if bool(item.get("canBuy")) and isinstance(item.get("price"), (int, float))
    )
    cookies = max(0.0, float(snapshot.get("cookies") or 0.0))
    cookies_ps = max(0.0, float(snapshot.get("cookiesPsRawHighest") or snapshot.get("cookiesPs") or 0.0))
    wrinkler_bank = estimate_attached_wrinkler_bank(snapshot)
    afford_budget = cookies + wrinkler_bank + (cookies_ps * afford_horizon_seconds)

    candidates = []
    affordable_fallbacks = []
    payback_sweeps = []
    cheap_sweeps = []
    for item in candidate_upgrades:
        candidate = resolve_candidate_metrics(snapshot, item)
        if bool(item.get("canBuy")) and isinstance(item.get("price"), (int, float)):
            affordable_fallbacks.append(item)
            if cookies > 0 and float(item.get("price") or 0.0) <= (cookies * cheap_upgrade_sweep_ratio):
                cheap_sweeps.append(item)
        if candidate is not None and bool(candidate.get("canBuy")):
            if float(candidate["paybackSeconds"]) <= auto_buy_payback_seconds:
                payback_sweeps.append(candidate)
        if candidate is None:
            continue
        if float(candidate["price"]) > afford_budget:
            continue
        candidates.append(candidate)

    if payback_sweeps:
        payback_sweeps.sort(
            key=lambda item: (
                float(item["paybackSeconds"]),
                float(item["price"]),
                int(item.get("id", 0)),
            )
        )
        candidate = payback_sweeps[0]
        reason = "upgrade_ready_payback_sweep"
    elif cheap_sweeps:
        cheap_sweeps.sort(
            key=lambda item: (
                float(item.get("price") or 0.0),
                int(item.get("id", 0)),
            )
        )
        candidate = cheap_sweeps[0]
        reason = "upgrade_ready_cash_sweep"
    elif candidates:
        candidates.sort(
            key=lambda item: (
                float(item["paybackSeconds"]),
                float(item["price"]),
                int(item.get("id", 0)),
            )
        )
        candidate = candidates[0]
        reason = "upgrade_ready"
    elif affordable_fallbacks:
        affordable_fallbacks.sort(
            key=lambda item: (
                float(item.get("price") or 0.0),
                int(item.get("id", 0)),
            )
        )
        candidate = affordable_fallbacks[0]
        reason = "upgrade_ready_affordable_fallback"
    else:
        candidate = None
        reason = "no_upgrade_in_horizon"

    return {
        "available": True,
        "reason": reason,
        "upgrades_total": len(upgrades),
        "affordable": affordable,
        "horizon_seconds": afford_horizon_seconds,
        "horizon_budget": afford_budget,
        "horizon_reachable": len(candidates),
        "candidate_id": None if candidate is None else candidate.get("id"),
        "candidate": None if candidate is None else (candidate.get("displayName") or candidate.get("name")),
        "candidate_price": None if candidate is None else candidate.get("price"),
        "candidate_delta_cps": None if candidate is None else candidate.get("deltaCps"),
        "candidate_payback_seconds": None if candidate is None else candidate.get("paybackSeconds"),
        "candidate_pool": None if candidate is None else candidate.get("pool"),
        "candidate_can_buy": None if candidate is None else candidate.get("canBuy"),
    }
