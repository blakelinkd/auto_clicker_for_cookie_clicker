from typing import Any, Callable


def plan_minigame_store_access(
    snapshot: dict[str, Any] | None,
    *,
    spell_diag: dict[str, Any] | None,
    bank_diag: dict[str, Any] | None,
    garden_diag: dict[str, Any] | None,
    minigame_building_ids: dict[str, int],
    plan_focus_building: Callable[[dict[str, Any] | None, Callable[..., Any], int], Any],
    to_screen_point: Callable[..., Any],
) -> tuple[str | None, Any]:
    candidates = []
    if isinstance(spell_diag, dict) and spell_diag.get("reason") == "grimoire_closed":
        if not bool(spell_diag.get("has_open_target")):
            candidates.append(("grimoire", minigame_building_ids["grimoire"]))
    if isinstance(bank_diag, dict) and bank_diag.get("reason") == "bank_closed_missing_open_control":
        candidates.append(("bank", minigame_building_ids["bank"]))
    if isinstance(garden_diag, dict) and garden_diag.get("reason") == "garden_closed_missing_open_control":
        candidates.append(("garden", minigame_building_ids["garden"]))
    for owner, building_id in candidates:
        access_action = plan_focus_building(snapshot, to_screen_point, building_id)
        if access_action is not None:
            return owner, access_action
    return None, None
