from typing import Any, Callable


def normalize_snapshot_target(
    rect: dict[str, Any] | None,
    to_screen_point: Callable[[int, int], tuple[int, int]],
) -> dict[str, int] | None:
    if not isinstance(rect, dict):
        return None
    x = rect.get("clickX")
    y = rect.get("clickY")
    if x is None:
        x = rect.get("centerX")
    if y is None:
        y = rect.get("centerY")
    if x is None or y is None:
        return None
    screen_x, screen_y = to_screen_point(int(x), int(y))
    return {
        "client_x": int(x),
        "client_y": int(y),
        "screen_x": int(screen_x),
        "screen_y": int(screen_y),
    }


def extract_big_cookie(
    snapshot: dict[str, Any] | None,
    *,
    to_screen_point: Callable[[int, int], tuple[int, int]],
) -> dict[str, int] | None:
    if not snapshot:
        return None
    big_cookie = snapshot.get("bigCookie")
    if not isinstance(big_cookie, dict):
        return None
    point = normalize_snapshot_target(big_cookie, to_screen_point)
    if point is None:
        return None
    return point


def extract_spell(
    snapshot: dict[str, Any] | None,
    *,
    to_screen_point: Callable[[int, int], tuple[int, int]],
) -> dict[str, Any] | None:
    if not snapshot:
        return None
    spell = snapshot.get("spell")
    if not isinstance(spell, dict):
        return None
    rect = spell.get("rect")
    point = normalize_snapshot_target(rect, to_screen_point)
    if point is None:
        return None
    return {
        "id": spell.get("id"),
        "key": spell.get("key"),
        "name": spell.get("name"),
        "ready": bool(spell.get("ready")),
        "on_minigame": bool(spell.get("onMinigame")),
        "cost": float(spell.get("cost", 0)),
        "magic": float(spell.get("magic", 0)),
        "max_magic": float(spell.get("maxMagic", 0)),
        **point,
    }


def extract_shimmers(
    snapshot: dict[str, Any] | None,
    *,
    to_screen_point: Callable[[int, int], tuple[int, int]],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not snapshot:
        return items
    seed = snapshot.get("seed")
    for shimmer in snapshot.get("shimmers", []):
        if not isinstance(shimmer, dict):
            continue
        point = normalize_snapshot_target(shimmer, to_screen_point)
        shimmer_id = shimmer.get("id")
        if point is None or shimmer_id is None:
            continue
        item = {
            "id": int(shimmer_id),
            "type": str(shimmer.get("type") or "golden"),
            "wrath": bool(shimmer.get("wrath")),
            "client_x": point["client_x"],
            "client_y": point["client_y"],
            "screen_x": point["screen_x"],
            "screen_y": point["screen_y"],
            "life": shimmer.get("life"),
            "dur": shimmer.get("dur"),
        }
        if seed:
            item["seed"] = seed
        items.append(item)
    return items


def extract_buffs(snapshot: dict[str, Any] | None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not snapshot:
        return items
    raw_buffs = snapshot.get("buffs")
    if not isinstance(raw_buffs, list):
        spellbook = snapshot.get("spellbook")
        if isinstance(spellbook, dict):
            raw_buffs = spellbook.get("activeBuffs")
    if not isinstance(raw_buffs, list):
        return items
    for buff in raw_buffs:
        if not isinstance(buff, dict):
            continue
        name = buff.get("name") or buff.get("key")
        if not name:
            continue
        items.append(
            {
                "key": buff.get("key") or name,
                "name": name,
                "time": buff.get("time"),
                "max_time": buff.get("maxTime"),
                "mult_cpS": buff.get("multCpS"),
                "mult_click": buff.get("multClick"),
            }
        )
    return items
