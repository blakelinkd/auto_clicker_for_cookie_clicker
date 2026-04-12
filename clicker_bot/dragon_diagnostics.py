from typing import Any, Callable


def build_dragon_diag(
    snapshot: dict[str, Any] | None,
    *,
    to_screen_point: Callable[[int, int], tuple[int, int]],
    normalize_target: Callable[[dict[str, Any] | None, Callable[[int, int], tuple[int, int]]], dict[str, int] | None],
) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {"available": False, "reason": "no_snapshot"}

    dragon = snapshot.get("dragon")
    if not isinstance(dragon, dict):
        return {"available": False, "reason": "no_dragon_data"}

    unlocked = bool(dragon.get("unlocked"))
    if not unlocked:
        return {
            "available": False,
            "reason": "dragon_locked",
            "unlocked": False,
        }

    level = int(dragon.get("level") or 0)
    max_level = int(dragon.get("maxLevel") or 0)
    next_cost_affordable = bool(dragon.get("nextCostAffordable"))
    next_cost_type = dragon.get("nextCostType")
    next_cookie_only = bool(dragon.get("nextCookieOnly"))
    next_required_building_name = dragon.get("nextRequiredBuildingName")
    next_required_building_amount = dragon.get("nextRequiredBuildingAmount")
    next_required_building_owned = dragon.get("nextRequiredBuildingOwned")
    has_required_building_floor = True
    if next_cost_type == "building_sacrifice":
        if not isinstance(next_required_building_amount, (int, float)) or not isinstance(
            next_required_building_owned, (int, float)
        ):
            has_required_building_floor = False
        else:
            has_required_building_floor = float(next_required_building_owned) >= float(next_required_building_amount)
    open_target = normalize_target(dragon.get("dragonTab"), to_screen_point)
    action_target = normalize_target(dragon.get("actionButton"), to_screen_point)
    close_target = normalize_target(dragon.get("closeButton"), to_screen_point)
    aura_primary_control = normalize_target(dragon.get("auraPrimaryControl"), to_screen_point)
    aura_secondary_control = normalize_target(dragon.get("auraSecondaryControl"), to_screen_point)
    aura_prompt_confirm = normalize_target(dragon.get("auraPromptConfirm"), to_screen_point)
    aura_prompt_choices = {}
    raw_aura_choices = dragon.get("auraPromptChoices")
    if isinstance(raw_aura_choices, list):
        for item in raw_aura_choices:
            if not isinstance(item, dict):
                continue
            aura_id = item.get("id")
            if aura_id is None:
                continue
            target = normalize_target(item.get("target"), to_screen_point)
            if target is None:
                continue
            aura_prompt_choices[int(aura_id)] = {
                "id": int(aura_id),
                "slot": None if item.get("slot") is None else int(item.get("slot")),
                "name": item.get("name"),
                "target": target,
            }

    reason = "dragon_ready"
    actionable = True
    if level >= max_level:
        reason = "dragon_complete"
        actionable = False
    elif not next_cost_affordable or not has_required_building_floor:
        if next_cost_type == "building_sacrifice":
            reason = "waiting_for_dragon_building_floor"
        elif next_cost_type == "special":
            reason = "waiting_for_dragon_special_cost"
        else:
            reason = "waiting_for_dragon_cost"
        actionable = False
    elif not open_target:
        reason = "dragon_tab_unavailable"
        actionable = False
    elif bool(dragon.get("open")) and not action_target:
        reason = "dragon_action_unavailable"
        actionable = False

    return {
        "available": True,
        "reason": reason,
        "actionable": actionable,
        "open": bool(dragon.get("open")),
        "level": level,
        "max_level": max_level,
        "current_name": dragon.get("currentName"),
        "next_action": dragon.get("nextAction"),
        "next_cost_text": dragon.get("nextCostText"),
        "next_cost_affordable": next_cost_affordable,
        "next_cost_type": next_cost_type,
        "next_cookie_only": next_cookie_only,
        "next_required_building_name": next_required_building_name,
        "next_required_building_amount": next_required_building_amount,
        "next_required_building_owned": next_required_building_owned,
        "aura_primary": dragon.get("auraPrimary"),
        "aura_primary_id": None if dragon.get("auraPrimaryId") is None else int(dragon.get("auraPrimaryId")),
        "aura_secondary": dragon.get("auraSecondary"),
        "aura_secondary_id": None if dragon.get("auraSecondaryId") is None else int(dragon.get("auraSecondaryId")),
        "aura_primary_control": aura_primary_control,
        "aura_secondary_control": aura_secondary_control,
        "aura_prompt_open": bool(dragon.get("auraPromptOpen")),
        "aura_prompt_slot": None if dragon.get("auraPromptSlot") is None else int(dragon.get("auraPromptSlot")),
        "aura_prompt_selected_id": None
        if dragon.get("auraPromptSelectedAuraId") is None
        else int(dragon.get("auraPromptSelectedAuraId")),
        "aura_prompt_current_id": None
        if dragon.get("auraPromptCurrentAuraId") is None
        else int(dragon.get("auraPromptCurrentAuraId")),
        "aura_prompt_confirm": aura_prompt_confirm,
        "aura_prompt_choices": aura_prompt_choices,
        "aura_swap_cost_free": bool(dragon.get("auraSwapCostFree")),
        "aura_swap_cost_building_id": None
        if dragon.get("auraSwapCostBuildingId") is None
        else int(dragon.get("auraSwapCostBuildingId")),
        "aura_swap_cost_building_name": dragon.get("auraSwapCostBuildingName"),
        "aura_swap_cost_building_amount": None
        if dragon.get("auraSwapCostBuildingAmount") is None
        else int(dragon.get("auraSwapCostBuildingAmount")),
        "open_target": open_target,
        "action_target": action_target,
        "close_target": close_target,
    }
