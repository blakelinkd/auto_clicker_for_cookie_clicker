from typing import Any


GARDEN_LONG_BUFF_THRESHOLD_FRAMES = 5 * 60 * 30


def get_active_click_buff_names(
    buffs: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None,
    *,
    production_stack_buff_keys: set[str],
    known_click_value_buffs: set[str],
) -> tuple[str, ...]:
    names = set()
    for buff in buffs or ():
        if not isinstance(buff, dict):
            continue
        name = buff.get("name") or buff.get("key")
        if name in production_stack_buff_keys:
            continue
        mult_click = buff.get("multClick")
        if isinstance(mult_click, (int, float)) and float(mult_click) > 1.0 and name:
            names.add(str(name))
            continue
        if name in known_click_value_buffs:
            names.add(str(name))
    return tuple(sorted(names))


def has_positive_active_buffs(snapshot: dict[str, Any] | None, *, known_negative_buffs: set[str]) -> bool:
    if not isinstance(snapshot, dict):
        return False
    raw_buffs = snapshot.get("buffs")
    if not isinstance(raw_buffs, list):
        spellbook = snapshot.get("spellbook")
        if isinstance(spellbook, dict):
            raw_buffs = spellbook.get("activeBuffs")
    if not isinstance(raw_buffs, list):
        return False
    for buff in raw_buffs:
        if not isinstance(buff, dict):
            continue
        name = buff.get("name") or buff.get("key")
        if not name:
            continue
        if name in known_negative_buffs:
            continue
        mult_cps = buff.get("multCpS")
        mult_click = buff.get("multClick")
        if isinstance(mult_cps, (int, float)) and float(mult_cps) > 1.0:
            return True
        if isinstance(mult_click, (int, float)) and float(mult_click) > 1.0:
            return True
        if name not in known_negative_buffs:
            return True
    return False


def has_long_positive_active_buff(
    snapshot: dict[str, Any] | None,
    *,
    known_negative_buffs: set[str],
    long_buff_threshold_frames: float = GARDEN_LONG_BUFF_THRESHOLD_FRAMES,
) -> bool:
    if not isinstance(snapshot, dict):
        return False
    raw_buffs = snapshot.get("buffs")
    if not isinstance(raw_buffs, list):
        spellbook = snapshot.get("spellbook")
        if isinstance(spellbook, dict):
            raw_buffs = spellbook.get("activeBuffs")
    if not isinstance(raw_buffs, list):
        return False
    for buff in raw_buffs:
        if not isinstance(buff, dict):
            continue
        name = buff.get("name") or buff.get("key")
        if not name or name in known_negative_buffs:
            continue
        mult_cps = buff.get("multCpS")
        mult_click = buff.get("multClick")
        is_positive = False
        if isinstance(mult_cps, (int, float)) and float(mult_cps) > 1.0:
            is_positive = True
        if isinstance(mult_click, (int, float)) and float(mult_click) > 1.0:
            is_positive = True
        if not is_positive and name not in known_negative_buffs:
            is_positive = True
        if not is_positive:
            continue
        remaining = buff.get("time")
        total = buff.get("maxTime")
        if isinstance(remaining, (int, float)) and float(remaining) > long_buff_threshold_frames:
            return True
        if isinstance(total, (int, float)) and float(total) > long_buff_threshold_frames:
            return True
    return False


def has_buff_only_non_click_pause(pause_reasons: tuple[str, ...] | list[str] | None) -> bool:
    if not pause_reasons:
        return False
    return all(str(reason).startswith("click_buffs=") for reason in pause_reasons)


def should_allow_non_click_actions_during_pause(
    snapshot: dict[str, Any] | None,
    pause_reasons: tuple[str, ...] | list[str] | None,
) -> bool:
    return False


def should_allow_garden_action(
    snapshot: dict[str, Any] | None,
    garden_diag: dict[str, Any] | None,
    *,
    production_stack_buff_keys: set[str],
    known_click_value_buffs: set[str],
) -> bool:
    if not isinstance(snapshot, dict):
        return True
    raw_buffs = snapshot.get("buffs")
    if not isinstance(raw_buffs, list):
        spellbook = snapshot.get("spellbook")
        if isinstance(spellbook, dict):
            raw_buffs = spellbook.get("activeBuffs")
    if not isinstance(raw_buffs, list):
        return True
    return not bool(
        get_active_click_buff_names(
            raw_buffs,
            production_stack_buff_keys=production_stack_buff_keys,
            known_click_value_buffs=known_click_value_buffs,
        )
    )
