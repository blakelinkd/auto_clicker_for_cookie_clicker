from typing import Any


def has_cookies_after_reserve(
    snapshot: dict[str, Any] | None,
    price: float | int | None,
    reserve_cookies: float | int,
) -> bool:
    if not isinstance(price, (int, float)):
        return False
    cookies = 0.0 if not isinstance(snapshot, dict) else max(0.0, float(snapshot.get("cookies") or 0.0))
    return cookies >= (float(reserve_cookies) + float(price))


def get_stock_buy_controls(building_diag: dict[str, Any] | None, enabled: bool, reserve_cookies: float | int) -> dict[str, Any]:
    return {
        "allow_buy_actions": True,
        "buy_reserve_cookies": max(0.0, float(reserve_cookies or 0.0)),
        "reason": "stock_ignores_building_constraints",
    }


def build_disabled_bank_diag(
    snapshot: dict[str, Any] | None,
    *,
    held_positions: dict[Any, dict[str, Any]],
) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {"available": False, "reason": "no_bank_data", "enabled": False}
    bank = snapshot.get("bank")
    if not isinstance(bank, dict):
        return {"available": False, "reason": "no_bank_data", "enabled": False}
    goods = [item for item in bank.get("goods", []) if isinstance(item, dict)]
    return {
        "available": True,
        "reason": "trading_disabled",
        "cookies": float(snapshot.get("cookies") or 0.0),
        "cookies_ps_raw_highest": float(snapshot.get("cookiesPsRawHighest") or snapshot.get("cookiesPs") or 0.0),
        "brokers": int(bank.get("brokers") or 0),
        "on_minigame": bool(bank.get("onMinigame")),
        "has_open_target": bank.get("openControl") is not None,
        "goods_total": len(goods),
        "goods_with_buy_target": 0,
        "goods_with_sell_target": 0,
        "goods_with_buy_enabled": 0,
        "goods_in_buy_zone": 0,
        "goods_with_thresholds": 0,
        "goods_at_capacity": 0,
        "goods_with_history": 0,
        "held_goods": len(held_positions),
        "held_shares": sum(int(position.get("shares") or 0) for position in held_positions.values()),
        "portfolio_exposure": None,
        "portfolio_cap": None,
        "portfolio_cap_ratio": None,
        "portfolio_exposure_ratio": None,
        "portfolio_remaining": None,
        "buy_actions_enabled": False,
        "sell_actions_enabled": False,
        "buy_reserve_cookies": 0.0,
        "buy_cookies_available": 0.0,
        "buy_candidate": None,
        "sell_candidate": None,
        "buy_threshold": None,
        "sell_threshold": None,
        "enabled": False,
    }


def stock_trade_management_active(
    *,
    stock_trading_enabled: bool,
    held_positions: dict[Any, Any],
    pending_actions: dict[Any, Any],
) -> bool:
    return stock_trading_enabled or bool(held_positions) or bool(pending_actions)


def should_pause_stock_trading(buffs: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> bool:
    return False


def should_defer_stock_actions_for_upgrade(
    snapshot: dict[str, Any] | None,
    upgrade_diag: dict[str, Any] | None,
    *,
    upgrade_autobuy_enabled: bool,
    pause_non_click_actions: bool = False,
    allow_upgrade_during_pause: bool = False,
    global_cookie_reserve: float = 0.0,
    shimmers_present: bool = False,
    combo_pending: bool = False,
    upgrade_signature_blocked: bool = False,
    now: float = 0.0,
    upgrade_blocked_until: float = 0.0,
) -> bool:
    if not upgrade_autobuy_enabled or shimmers_present or combo_pending:
        return False
    if pause_non_click_actions and not allow_upgrade_during_pause:
        return False
    if upgrade_signature_blocked or float(now) < float(upgrade_blocked_until or 0.0):
        return False
    if not isinstance(upgrade_diag, dict):
        return False
    if not bool(upgrade_diag.get("candidate_can_buy")) or upgrade_diag.get("candidate_id") is None:
        return False
    return has_cookies_after_reserve(
        snapshot,
        upgrade_diag.get("candidate_price"),
        global_cookie_reserve,
    )


def get_garden_cookie_reserve(
    snapshot: dict[str, Any] | None,
    garden_diag: dict[str, Any] | None,
    *,
    garden_automation_enabled: bool,
) -> float:
    if not garden_automation_enabled:
        return 0.0
    if not isinstance(snapshot, dict) or not isinstance(garden_diag, dict):
        return 0.0
    if garden_diag.get("plan_mode") != "mutation":
        return 0.0
    if garden_diag.get("planner_state") != "waiting_for_seed_funds":
        return 0.0
    remaining = garden_diag.get("remaining_layout_cost")
    if not isinstance(remaining, (int, float)) or float(remaining) <= 0:
        return 0.0
    cookies = max(0.0, float(snapshot.get("cookies") or 0.0))
    remaining = max(0.0, float(remaining))
    if remaining > cookies:
        return 0.0
    return min(cookies, remaining)
