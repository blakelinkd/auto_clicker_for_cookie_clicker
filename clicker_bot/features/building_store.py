from dataclasses import dataclass


@dataclass
class BuildingStoreAction:
    kind: str
    screen_x: int
    screen_y: int
    building_id: int | None = None
    building_name: str | None = None
    store_mode: int | None = None
    store_bulk: int | None = None
    quantity: int | None = None
    current_store_mode: int | None = None
    current_store_bulk: int | None = None
    section_name: str | None = None
    scroll_steps: int | None = None
    planner_context: dict | None = None


class BuildingStoreController:
    SCROLL_PIXELS_PER_STEP = 1
    MAX_SCROLL_STEPS = 64

    def extract_state(self, snapshot, to_screen_point):
        if not snapshot or not isinstance(snapshot, dict):
            return None
        raw_store = snapshot.get("store")
        raw_buildings = snapshot.get("buildings")
        if not isinstance(raw_store, dict) or not isinstance(raw_buildings, list):
            return None

        obstructing_rects = self._extract_obstructing_rects(raw_store)
        store = {
            "buy_mode": raw_store.get("buyMode"),
            "buy_bulk": raw_store.get("buyBulk"),
            "mode_buy": self._normalize_target(raw_store.get("modeBuy"), to_screen_point),
            "mode_sell": self._normalize_target(raw_store.get("modeSell"), to_screen_point),
            "products_viewport": self._normalize_scroll_anchor(raw_store.get("productsViewport"), to_screen_point),
            "bulk_targets": {
                1: self._normalize_target(raw_store.get("bulk1"), to_screen_point),
                10: self._normalize_target(raw_store.get("bulk10"), to_screen_point),
                100: self._normalize_target(raw_store.get("bulk100"), to_screen_point),
                -1: self._normalize_target(raw_store.get("bulkMax"), to_screen_point),
            },
            "sections": self._extract_sections(raw_store, to_screen_point),
        }

        buildings = {}
        for raw in raw_buildings:
            if not isinstance(raw, dict):
                continue
            building_id = raw.get("id")
            if building_id is None:
                continue
            buildings[int(building_id)] = {
                "id": int(building_id),
                "name": raw.get("name") or f"building-{building_id}",
                "amount": int(raw.get("amount") or 0),
                "price": None if raw.get("price") is None else float(raw.get("price")),
                "stored_cps": None if raw.get("storedCps") is None else float(raw.get("storedCps")),
                "sum_price_10": None if raw.get("sumPrice10") is None else float(raw.get("sumPrice10")),
                "sum_price_100": None if raw.get("sumPrice100") is None else float(raw.get("sumPrice100")),
                "sell_value_1": None if raw.get("sellValue1") is None else float(raw.get("sellValue1")),
                "sell_value_10": None if raw.get("sellValue10") is None else float(raw.get("sellValue10")),
                "sell_value_100": None if raw.get("sellValue100") is None else float(raw.get("sellValue100")),
                "sell_multiplier": None if raw.get("sellMultiplier") is None else float(raw.get("sellMultiplier")),
                "can_buy": bool(raw.get("canBuy")),
                "can_sell": bool(raw.get("canSell")),
                "visible": bool(raw.get("visible", True)),
                "target": self._normalize_target(
                    raw.get("target") or raw.get("row"),
                    to_screen_point,
                    avoid_rects=obstructing_rects,
                ),
            }
        return {
            "store": store,
            "buildings": buildings,
        }

    def plan_buy(self, snapshot, to_screen_point, building_id, quantity=1):
        return self._plan_trade(snapshot, to_screen_point, building_id, mode=1, quantity=quantity)

    def plan_sell(self, snapshot, to_screen_point, building_id, quantity=1):
        return self._plan_trade(snapshot, to_screen_point, building_id, mode=-1, quantity=quantity)

    def plan_focus_building(self, snapshot, to_screen_point, building_id):
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return None
        building = state["buildings"].get(int(building_id))
        if building is None or building["target"] is None:
            return None
        return self._plan_products_visibility(state["store"], building)

    def plan_reset_to_default(self, snapshot, to_screen_point):
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return None
        store = state["store"]
        if store["buy_mode"] != 1:
            target = store["mode_buy"]
            if target is None:
                return None
            return BuildingStoreAction(
                kind="set_store_mode",
                screen_x=target["screen_x"],
                screen_y=target["screen_y"],
                store_mode=1,
                store_bulk=1,
                current_store_mode=store["buy_mode"],
                current_store_bulk=store["buy_bulk"],
            )
        if store["buy_bulk"] != 1:
            target = store["bulk_targets"].get(1)
            if target is None:
                return None
            return BuildingStoreAction(
                kind="set_store_bulk",
                screen_x=target["screen_x"],
                screen_y=target["screen_y"],
                store_mode=1,
                store_bulk=1,
                quantity=1,
                current_store_mode=store["buy_mode"],
                current_store_bulk=store["buy_bulk"],
            )
        return BuildingStoreAction(
            kind="store_ready",
            screen_x=0,
            screen_y=0,
            store_mode=1,
            store_bulk=1,
            current_store_mode=store["buy_mode"],
            current_store_bulk=store["buy_bulk"],
        )

    def _plan_trade(self, snapshot, to_screen_point, building_id, mode, quantity):
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return None

        building = state["buildings"].get(int(building_id))
        if building is None or building["target"] is None:
            return None

        store = state["store"]
        planner_context = self._get_products_planner_context(store, building)
        if store["buy_mode"] != mode:
            target = store["mode_buy"] if mode == 1 else store["mode_sell"]
            if target is None:
                return None
            return BuildingStoreAction(
                kind="set_store_mode",
                screen_x=target["screen_x"],
                screen_y=target["screen_y"],
                store_mode=mode,
                current_store_mode=store["buy_mode"],
                current_store_bulk=store["buy_bulk"],
            )

        bulk = self._normalize_quantity(quantity)
        if store["buy_bulk"] != bulk:
            target = store["bulk_targets"].get(bulk)
            if target is None:
                return None
            return BuildingStoreAction(
                kind="set_store_bulk",
                screen_x=target["screen_x"],
                screen_y=target["screen_y"],
                store_bulk=bulk,
                quantity=bulk,
                current_store_mode=store["buy_mode"],
                current_store_bulk=store["buy_bulk"],
            )

        if mode == 1:
            section_action = self._plan_products_visibility(store, building)
            if section_action is not None:
                return section_action

        can_trade = building["can_buy"] if mode == 1 else building["can_sell"]
        if not can_trade:
            return None

        return BuildingStoreAction(
            kind="click_building",
            screen_x=building["target"]["screen_x"],
            screen_y=building["target"]["screen_y"],
            building_id=building["id"],
            building_name=building["name"],
            store_mode=mode,
            store_bulk=bulk,
            quantity=bulk,
            current_store_mode=store["buy_mode"],
            current_store_bulk=store["buy_bulk"],
            planner_context=planner_context,
        )

    def _extract_sections(self, raw_store, to_screen_point):
        raw_sections = raw_store.get("sections")
        if not isinstance(raw_sections, dict):
            return {}
        sections = {}
        for name, raw_section in raw_sections.items():
            if not isinstance(raw_section, dict):
                continue
            sections[str(name)] = {
                "toggle": self._normalize_target(raw_section.get("toggle"), to_screen_point),
                "collapsed": bool(raw_section.get("collapsed")),
                "visible": bool(raw_section.get("visible", True)),
            }
        return sections

    def _extract_obstructing_rects(self, raw_store):
        rects = []
        for key in ("modeBuy", "modeSell", "bulk1", "bulk10", "bulk100", "bulkMax"):
            rect = raw_store.get(key)
            if isinstance(rect, dict):
                rects.append(rect)
        return rects

    def _plan_products_visibility(self, store, building):
        products = store["sections"].get("products") or {}
        if products.get("collapsed"):
            target = products.get("toggle")
            if target is not None:
                return BuildingStoreAction(
                    kind="expand_store_section",
                    screen_x=target["screen_x"],
                    screen_y=target["screen_y"],
                    section_name="products",
                    current_store_mode=store["buy_mode"],
                    current_store_bulk=store["buy_bulk"],
                    planner_context={"reason": "products_section_collapsed"},
                )

        planner_context = self._get_products_planner_context(store, building)
        if planner_context is None:
            return None
        viewport = store.get("products_viewport")
        if viewport is None:
            return None

        if planner_context["fully_visible"] or (
            planner_context.get("building_visible") and planner_context.get("click_within_viewport")
        ):
            return None
        delta_y = int(planner_context["delta_y"])
        if delta_y == 0:
            return None

        steps = (abs(delta_y) + self.SCROLL_PIXELS_PER_STEP - 1) // self.SCROLL_PIXELS_PER_STEP
        steps = max(1, min(self.MAX_SCROLL_STEPS, steps))
        if delta_y > 0:
            steps *= -1

        return BuildingStoreAction(
            kind="scroll_store",
            screen_x=viewport["screen_x"],
            screen_y=viewport["screen_y"],
            section_name="products",
            scroll_steps=steps,
            building_id=building["id"],
            building_name=building["name"],
            current_store_mode=store["buy_mode"],
            current_store_bulk=store["buy_bulk"],
            planner_context=planner_context,
        )

    def _get_products_planner_context(self, store, building):
        viewport = store.get("products_viewport")
        target = building.get("target")
        if viewport is None or target is None:
            return None

        padding = 12
        viewport_top = int(viewport.get("top", viewport["client_y"]))
        viewport_bottom = int(viewport.get("bottom", viewport["client_y"]))
        viewport_left = int(viewport.get("left", viewport["client_x"]))
        viewport_right = int(viewport.get("right", viewport["client_x"]))
        target_top = int(target.get("top", target["client_y"]))
        target_bottom = int(target.get("bottom", target["client_y"]))
        target_left = int(target.get("left", target["client_x"]))
        target_right = int(target.get("right", target["client_x"]))
        target_center_x = int(target.get("client_x", (target_left + target_right) // 2))
        target_center_y = int(target.get("client_y", (target_top + target_bottom) // 2))
        click_within_viewport = (
            viewport_left <= target_center_x <= viewport_right
            and (viewport_top + padding) <= target_center_y <= (viewport_bottom - padding)
        )
        fully_visible = (
            building.get("visible", True)
            and target_top >= (viewport_top + padding)
            and target_bottom <= (viewport_bottom - padding)
        )
        center_within_viewport = (
            viewport_left <= target_center_x <= viewport_right
            and viewport_top <= target_center_y <= viewport_bottom
        )
        if target_bottom > (viewport_bottom - padding):
            delta_y = target_bottom - (viewport_bottom - padding)
            reason = "target_below_viewport"
        elif target_top < (viewport_top + padding):
            delta_y = target_top - (viewport_top + padding)
            reason = "target_above_viewport"
        else:
            delta_y = 0
            reason = "target_within_viewport"
        return {
            "reason": "target_clickable_in_viewport" if (not fully_visible and click_within_viewport) else (reason if not fully_visible else "target_fully_visible"),
            "padding": padding,
            "building_visible": bool(building.get("visible", True)),
            "fully_visible": fully_visible,
            "click_within_viewport": click_within_viewport,
            "center_within_viewport": center_within_viewport,
            "delta_y": int(delta_y),
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

    def _normalize_quantity(self, quantity):
        quantity = int(quantity)
        if quantity <= 1:
            return 1
        if quantity <= 10:
            return 10
        if quantity <= 100:
            return 100
        return -1

    def _point_in_any_rect(self, x, y, rects):
        for rect in rects:
            if not isinstance(rect, dict):
                continue
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
        width = right - left
        height = bottom - top
        inset_x = max(8, min(24, int(width * 0.08)))
        inset_y = max(4, min(12, int(height * 0.15)))
        candidates = [
            (int(round(left + width * 0.45)), int(round(top + height * 0.50))),
            (int(round(left + width * 0.60)), int(round(top + height * 0.50))),
            (int(round(left + width * 0.32)), int(round(top + height * 0.50))),
            (int(round(left + width * 0.45)), int(round(top + height * 0.30))),
            (int(round(left + width * 0.45)), int(round(top + height * 0.70))),
            (int(left + inset_x), int(round(top + height * 0.50))),
            (int(right - inset_x), int(round(top + height * 0.50))),
            (int(round((left + right) / 2)), int(round((top + bottom) / 2))),
        ]
        min_x = int(left + inset_x)
        max_x = int(right - inset_x)
        min_y = int(top + inset_y)
        max_y = int(bottom - inset_y)
        for x, y in candidates:
            x = max(min_x, min(max_x, x))
            y = max(min_y, min(max_y, y))
            if not self._point_in_any_rect(x, y, avoid_rects):
                return x, y
        return None

    def _normalize_target(self, rect, to_screen_point, avoid_rects=None):
        if not isinstance(rect, dict):
            return None
        avoid_rects = avoid_rects or []
        click_x_value = rect.get("clickX")
        click_y_value = rect.get("clickY")
        has_explicit_click_point = click_x_value is not None and click_y_value is not None
        center_x = click_x_value
        center_y = click_y_value
        if center_x is None or center_y is None:
            center_x = rect.get("centerX")
            center_y = rect.get("centerY")
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

    def _normalize_scroll_anchor(self, rect, to_screen_point):
        if not isinstance(rect, dict):
            return None
        anchor = self._choose_safe_point(rect, [])
        if anchor is None:
            anchor_x = rect.get("centerX")
            anchor_y = rect.get("centerY")
            if anchor_x is None or anchor_y is None:
                return None
            anchor = (int(anchor_x), int(anchor_y))
        screen_x, screen_y = to_screen_point(anchor[0], anchor[1])
        return {
            "left": None if rect.get("left") is None else int(rect.get("left")),
            "top": None if rect.get("top") is None else int(rect.get("top")),
            "right": None if rect.get("right") is None else int(rect.get("right")),
            "bottom": None if rect.get("bottom") is None else int(rect.get("bottom")),
            "client_x": int(anchor[0]),
            "client_y": int(anchor[1]),
            "screen_x": int(screen_x),
            "screen_y": int(screen_y),
        }
