from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ReservePolicy:
    lucky_reserve_cps_seconds: float
    crafty_pixies_buff: str
    building_buff_burst_min_remaining_seconds: float
    cookie_clicker_fps: float
    log: Any
    monotonic: Callable[[], float]
    last_lucky_multiplier: float = 1.0
    last_lucky_multiplier_logged_at: float = 0.0

    def get_lucky_reserve_multiplier(self, snapshot: dict[str, Any] | None) -> float:
        if not isinstance(snapshot, dict):
            return 1.0
        ascension = snapshot.get("ascension")
        if not isinstance(ascension, dict):
            return 1.0
        ascend_gain = ascension.get("ascendGain")
        if isinstance(ascend_gain, (int, float)) and ascend_gain >= 0:
            gain = float(ascend_gain)
            if gain >= 30:
                multiplier = 1.0
            elif gain <= 0:
                multiplier = 0.3
            else:
                multiplier = 0.3 + 0.7 * (gain / 30.0)
                multiplier = min(1.0, max(0.3, multiplier))
        else:
            current_prestige = ascension.get("currentPrestige")
            if isinstance(current_prestige, (int, float)) and current_prestige > 0:
                prestige = float(current_prestige)
                if prestige >= 3000:
                    multiplier = 1.0
                elif prestige <= 100:
                    multiplier = 0.3
                else:
                    multiplier = 0.3 + 0.7 * (prestige - 100) / (3000 - 100)
                    multiplier = min(1.0, max(0.3, multiplier))
            else:
                multiplier = 1.0

        now = self.monotonic()
        if abs(multiplier - self.last_lucky_multiplier) > 0.05 or (
            now - self.last_lucky_multiplier_logged_at
        ) > 300.0:
            self.log.info(
                f"Lucky reserve multiplier {multiplier:.2f} "
                f"(ascendGain={ascend_gain}, currentPrestige={ascension.get('currentPrestige')})"
            )
            self.last_lucky_multiplier = multiplier
            self.last_lucky_multiplier_logged_at = now
        return multiplier

    def get_lucky_cookie_reserve(self, snapshot: dict[str, Any] | None, *, use_live_cps: bool = False) -> float:
        if not isinstance(snapshot, dict):
            return 0.0
        cookies_ps = snapshot.get("cookiesPs") if use_live_cps else snapshot.get("cookiesPsRawHighest")
        if not isinstance(cookies_ps, (int, float)) and not use_live_cps:
            cookies_ps = snapshot.get("cookiesPs")
        if not isinstance(cookies_ps, (int, float)) and use_live_cps:
            cookies_ps = snapshot.get("cookiesPsRawHighest")
        if not isinstance(cookies_ps, (int, float)):
            return 0.0
        multiplier = self.get_lucky_reserve_multiplier(snapshot)
        return max(0.0, float(cookies_ps)) * self.lucky_reserve_cps_seconds * multiplier

    def get_building_buff_burst_window(
        self,
        snapshot: dict[str, Any] | None,
        building_diag: dict[str, Any] | None = None,
        spell_diag: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(snapshot, dict) or not isinstance(building_diag, dict):
            return {"active": False}
        target_building = building_diag.get("candidate") or building_diag.get("next_candidate")
        if not target_building:
            return {"active": False}
        raw_buffs = snapshot.get("buffs")
        if not isinstance(raw_buffs, list):
            return {"active": False}
        matched_buff = None
        for buff in raw_buffs:
            if not isinstance(buff, dict):
                continue
            if buff.get("type") != "building buff":
                continue
            if buff.get("buildingName") != target_building:
                continue
            mult = buff.get("multCpS")
            remaining = buff.get("time")
            if not isinstance(mult, (int, float)) or float(mult) <= 1.0:
                continue
            if not isinstance(remaining, (int, float)) or float(remaining) <= 0:
                continue
            matched_buff = buff
            break
        if not isinstance(matched_buff, dict):
            return {"active": False}
        remaining_seconds = max(0.0, float(matched_buff.get("time") or 0.0) / self.cookie_clicker_fps)
        pixies_active = any(
            isinstance(buff, dict) and buff.get("name") == self.crafty_pixies_buff for buff in raw_buffs
        )
        pixies_ready = (
            isinstance(spell_diag, dict)
            and spell_diag.get("reason") == "crafty_pixies_ready"
            and spell_diag.get("crafty_pixies_target") == target_building
        )
        burst_active = (
            remaining_seconds >= self.building_buff_burst_min_remaining_seconds and (pixies_active or pixies_ready)
        )
        return {
            "active": burst_active,
            "building_name": target_building,
            "buff_name": matched_buff.get("name"),
            "multiplier": float(matched_buff.get("multCpS") or 1.0),
            "remaining_seconds": remaining_seconds,
            "pixies_active": pixies_active,
            "pixies_ready": pixies_ready,
        }

    def get_global_cookie_reserve(
        self,
        snapshot: dict[str, Any] | None,
        garden_diag: dict[str, Any] | None,
        *,
        get_garden_cookie_reserve: Callable[[dict[str, Any] | None, dict[str, Any] | None], float],
        lucky_reserve_enabled: bool,
        building_diag: dict[str, Any] | None = None,
        spell_diag: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        garden_reserve = get_garden_cookie_reserve(snapshot, garden_diag)
        hard_lucky_reserve = self.get_lucky_cookie_reserve(snapshot, use_live_cps=False) if lucky_reserve_enabled else 0.0
        live_lucky_reserve = self.get_lucky_cookie_reserve(snapshot, use_live_cps=True) if lucky_reserve_enabled else 0.0
        burst_window = self.get_building_buff_burst_window(snapshot, building_diag, spell_diag)
        base_total_reserve = max(0.0, float(garden_reserve)) + max(0.0, float(hard_lucky_reserve))
        building_total_reserve = 0.0 if burst_window.get("active") else base_total_reserve
        return {
            "garden_reserve": max(0.0, float(garden_reserve)),
            "lucky_reserve": max(0.0, float(hard_lucky_reserve)),
            "hard_lucky_reserve": max(0.0, float(hard_lucky_reserve)),
            "live_lucky_reserve": max(0.0, float(live_lucky_reserve)),
            "soft_lucky_delta": max(0.0, float(live_lucky_reserve) - float(hard_lucky_reserve)),
            "lucky_reserve_enabled": bool(lucky_reserve_enabled),
            "total_reserve": base_total_reserve,
            "building_total_reserve": building_total_reserve,
            "burst_window": burst_window,
        }


def apply_building_burst_purchase_goal(
    snapshot: dict[str, Any] | None,
    building_diag: dict[str, Any] | None,
    purchase_goal: dict[str, Any] | None,
    burst_window: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(snapshot, dict) or not isinstance(building_diag, dict) or not isinstance(burst_window, dict):
        return purchase_goal
    if not burst_window.get("active"):
        return purchase_goal
    name = building_diag.get("next_candidate")
    price = building_diag.get("next_candidate_price")
    payback = building_diag.get("next_candidate_payback_seconds")
    if not name or not isinstance(price, (int, float)) or not isinstance(payback, (int, float)):
        return purchase_goal
    cookies = max(0.0, float(snapshot.get("cookies") or 0.0))
    return {
        "kind": "building",
        "name": str(name),
        "price": float(price),
        "payback_seconds": float(payback),
        "cookies": cookies,
        "can_buy": bool(building_diag.get("next_candidate_can_buy")),
        "shortfall": max(0.0, float(price) - cookies),
        "force_wrinkler_liquidation": True,
        "burst_window_building": burst_window.get("building_name"),
        "burst_window_remaining_seconds": burst_window.get("remaining_seconds"),
        "burst_window_buff_name": burst_window.get("buff_name"),
    }
