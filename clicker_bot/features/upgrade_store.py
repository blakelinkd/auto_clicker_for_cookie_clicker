from dataclasses import dataclass


@dataclass
class UpgradeStoreAction:
    kind: str
    screen_x: int
    screen_y: int
    upgrade_id: int | None = None
    upgrade_name: str | None = None
    current_store_mode: int | None = None
    current_store_bulk: int | None = None
    section_name: str | None = None
    scroll_steps: int | None = None
    planner_context: dict | None = None


class UpgradeStoreController:
    def extract_state(self, snapshot, to_screen_point):
        if not snapshot or not isinstance(snapshot, dict):
            return None
        raw_store = snapshot.get("store")
        raw_upgrades = snapshot.get("upgrades")
        if not isinstance(raw_store, dict) or not isinstance(raw_upgrades, list):
            return None

        sections = raw_store.get("sections") if isinstance(raw_store.get("sections"), dict) else {}
        upgrades_section = sections.get("upgrades") if isinstance(sections.get("upgrades"), dict) else {}
        obstructing_rects = self._extract_obstructing_rects(raw_store)
        upgrades = {}
        for raw in raw_upgrades:
            if not isinstance(raw, dict):
                continue
            upgrade_id = raw.get("id")
            if upgrade_id is None:
                continue
            upgrades[int(upgrade_id)] = {
                "id": int(upgrade_id),
                "name": raw.get("displayName") or raw.get("name") or f"upgrade-{upgrade_id}",
                "can_buy": bool(raw.get("canBuy")),
                "visible": bool(raw.get("visible", True)),
                "row": self._normalize_target(raw.get("row"), to_screen_point),
                "target": self._normalize_target(
                    raw.get("target") or raw.get("row"),
                    to_screen_point,
                    avoid_rects=obstructing_rects,
                ),
            }

        return {
            "store_mode": raw_store.get("buyMode"),
            "store_bulk": raw_store.get("buyBulk"),
            "products_viewport": self._normalize_target(raw_store.get("productsViewport"), to_screen_point),
            "upgrades_section": {
                "collapsed": bool(upgrades_section.get("collapsed")),
                "toggle": self._normalize_target(upgrades_section.get("toggle"), to_screen_point),
                "rect": self._normalize_target(upgrades_section.get("rect"), to_screen_point),
            },
            "upgrades": upgrades,
        }

    def plan_buy(self, snapshot, to_screen_point, upgrade_id):
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return None

        upgrade = state["upgrades"].get(int(upgrade_id))
        if upgrade is None:
            return None

        section = state["upgrades_section"]
        if section.get("collapsed"):
            target = section.get("toggle")
            if target is None:
                return None
            return UpgradeStoreAction(
                kind="expand_upgrades_section",
                screen_x=target["screen_x"],
                screen_y=target["screen_y"],
                current_store_mode=state["store_mode"],
                current_store_bulk=state["store_bulk"],
            )

        visibility_action = self._plan_visibility(state, upgrade)
        if visibility_action is not None:
            return visibility_action

        if not upgrade["can_buy"] or upgrade["target"] is None:
            return None

        planner_context = self._get_upgrade_planner_context(state, upgrade)
        return UpgradeStoreAction(
            kind="click_upgrade",
            screen_x=upgrade["target"]["screen_x"],
            screen_y=upgrade["target"]["screen_y"],
            upgrade_id=upgrade["id"],
            upgrade_name=upgrade["name"],
            current_store_mode=state["store_mode"],
            current_store_bulk=state["store_bulk"],
            planner_context=planner_context,
        )

    def plan_focus_section(self, snapshot, to_screen_point, section_name="upgrades"):
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return None
        if section_name != "upgrades":
            return None
        section = state.get("upgrades_section") or {}
        target = section.get("rect") or state.get("products_viewport")
        if target is None:
            return None
        return UpgradeStoreAction(
            kind="focus_store_section",
            screen_x=target["screen_x"],
            screen_y=target["screen_y"],
            current_store_mode=state["store_mode"],
            current_store_bulk=state["store_bulk"],
            section_name="upgrades",
        )

    def _plan_visibility(self, state, upgrade):
        section = state.get("upgrades_section") or {}
        if section.get("collapsed"):
            target = section.get("toggle")
            if target is None:
                return None
            return UpgradeStoreAction(
                kind="expand_upgrades_section",
                screen_x=target["screen_x"],
                screen_y=target["screen_y"],
                current_store_mode=state["store_mode"],
                current_store_bulk=state["store_bulk"],
            )

        planner_context = self._get_upgrade_planner_context(state, upgrade)
        if planner_context is None:
            return None
        if planner_context["actionable"]:
            return None

        viewport = section.get("rect") or state.get("products_viewport")
        if viewport is None:
            return None

        return UpgradeStoreAction(
            kind="focus_store_section",
            screen_x=viewport["screen_x"],
            screen_y=viewport["screen_y"],
            upgrade_id=upgrade["id"],
            upgrade_name=upgrade["name"],
            current_store_mode=state["store_mode"],
            current_store_bulk=state["store_bulk"],
            section_name="upgrades",
            planner_context=planner_context,
        )

    def _get_upgrade_planner_context(self, state, upgrade):
        section = state.get("upgrades_section") or {}
        viewport = section.get("rect") or state.get("products_viewport")
        target = upgrade.get("target")
        row = upgrade.get("row")
        if viewport is None or target is None:
            return None

        padding = 8
        viewport_top = self._coord(viewport, "top")
        viewport_bottom = self._coord(viewport, "bottom")
        viewport_left = self._coord(viewport, "left")
        viewport_right = self._coord(viewport, "right")

        bounds_source = row or target
        target_top = self._coord(bounds_source, "top")
        target_bottom = self._coord(bounds_source, "bottom")
        target_left = self._coord(bounds_source, "left")
        target_right = self._coord(bounds_source, "right")
        target_center_x = int(target.get("client_x", (target_left + target_right) // 2))
        target_center_y = int(target.get("client_y", (target_top + target_bottom) // 2))

        row_within_viewport = (
            target_top >= (viewport_top + padding)
            and target_bottom <= (viewport_bottom - padding)
        )
        center_within_viewport = (
            viewport_left <= target_center_x <= viewport_right
            and viewport_top <= target_center_y <= viewport_bottom
        )
        actionable = bool(upgrade.get("visible")) or row_within_viewport or center_within_viewport

        return {
            "reason": "upgrade_actionable" if actionable else "upgrade_not_actionable",
            "padding": padding,
            "upgrade_visible": bool(upgrade.get("visible")),
            "row_within_viewport": row_within_viewport,
            "center_within_viewport": center_within_viewport,
            "actionable": actionable,
            "viewport_left": viewport_left,
            "viewport_top": viewport_top,
            "viewport_right": viewport_right,
            "viewport_bottom": viewport_bottom,
            "target_left": target_left,
            "target_top": target_top,
            "target_right": target_right,
            "target_bottom": target_bottom,
            "target_center_x": target_center_x,
            "target_center_y": target_center_y,
        }

    def _coord(self, rect, axis):
        value = rect.get(axis)
        if value is not None:
            return int(value)
        if axis in {"left", "right"}:
            return int(rect["client_x"])
        return int(rect["client_y"])

    def _extract_obstructing_rects(self, raw_store):
        rects = []
        for key in ("modeBuy", "modeSell", "bulk1", "bulk10", "bulk100", "bulkMax"):
            rect = raw_store.get(key)
            if isinstance(rect, dict):
                rects.append(rect)
        return rects

    def _point_in_any_rect(self, x, y, rects):
        for rect in rects:
            left = rect.get("left")
            top = rect.get("top")
            right = rect.get("right")
            bottom = rect.get("bottom")
            if not all(isinstance(value, (int, float)) for value in (left, top, right, bottom)):
                continue
            if left <= x < right and top <= y < bottom:
                return True
        return False

    def _choose_safe_point(self, rect, avoid_rects):
        left = rect.get("left")
        top = rect.get("top")
        right = rect.get("right")
        bottom = rect.get("bottom")
        if not all(isinstance(value, (int, float)) for value in (left, top, right, bottom)):
            return None
        if right <= left or bottom <= top:
            return None

        inset_x = max(2, min(6, int((right - left) // 4) or 2))
        inset_y = max(2, min(6, int((bottom - top) // 4) or 2))
        center_x = int(round((left + right) / 2))
        center_y = int(round((top + bottom) / 2))
        candidates = [
            (center_x, int(top + inset_y)),
            (center_x, int(bottom - inset_y)),
            (int(left + inset_x), center_y),
            (int(right - inset_x), center_y),
            (int(left + inset_x), int(top + inset_y)),
            (int(right - inset_x), int(top + inset_y)),
            (int(left + inset_x), int(bottom - inset_y)),
            (int(right - inset_x), int(bottom - inset_y)),
            (center_x, center_y),
        ]
        for x, y in candidates:
            if not self._point_in_any_rect(x, y, avoid_rects):
                return x, y
        return None

    def _normalize_target(self, rect, to_screen_point, avoid_rects=None):
        if not isinstance(rect, dict):
            return None
        click_x_value = rect.get("clickX")
        click_y_value = rect.get("clickY")
        has_explicit_click_point = click_x_value is not None and click_y_value is not None
        center_x = click_x_value if click_x_value is not None else rect.get("centerX")
        center_y = click_y_value if click_y_value is not None else rect.get("centerY")
        if center_x is None:
            left = rect.get("left")
            right = rect.get("right")
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                center_x = int(round((left + right) / 2))
        if center_y is None:
            top = rect.get("top")
            bottom = rect.get("bottom")
            if isinstance(top, (int, float)) and isinstance(bottom, (int, float)):
                center_y = int(round((top + bottom) / 2))
        if center_x is None or center_y is None:
            return None
        click_x = int(center_x)
        click_y = int(center_y)
        if avoid_rects and not has_explicit_click_point:
            safe_point = self._choose_safe_point(rect, avoid_rects)
            if safe_point is not None:
                click_x, click_y = safe_point
        screen_x, screen_y = to_screen_point(click_x, click_y)
        return {
            "left": None if rect.get("left") is None else int(rect.get("left")),
            "top": None if rect.get("top") is None else int(rect.get("top")),
            "right": None if rect.get("right") is None else int(rect.get("right")),
            "bottom": None if rect.get("bottom") is None else int(rect.get("bottom")),
            "client_x": int(click_x),
            "client_y": int(click_y),
            "screen_x": int(screen_x),
            "screen_y": int(screen_y),
        }
