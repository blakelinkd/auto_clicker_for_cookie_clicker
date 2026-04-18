from dataclasses import dataclass, replace
from typing import Protocol
from typing import Any, Callable


@dataclass(frozen=True)
class PreparedSnapshot:
    snapshot: dict[str, Any] | None
    shimmers: list[dict[str, Any]]
    buffs: list[dict[str, Any]]
    spell: dict[str, Any] | None
    big_cookie: dict[str, Any] | None


@dataclass(frozen=True)
class BankDiagCache:
    diag: dict[str, Any] | None = None
    captured_at: float = 0.0


@dataclass(frozen=True)
class DomLoopBuildOptions:
    building_autobuy_enabled: bool
    lucky_reserve_enabled: bool
    stock_trading_enabled: bool
    upgrade_autobuy_enabled: bool
    ascension_prep_enabled: bool
    garden_automation_enabled: bool
    stock_diag_refresh_interval: float


@dataclass(frozen=True)
class DomLoopCycleState:
    build_options: DomLoopBuildOptions
    prepared: PreparedSnapshot
    diagnostics: "DomLoopDiagnostics"
    bank_diag_cache: BankDiagCache
    now: float
    pause_value_actions_during_clot: bool


@dataclass(frozen=True)
class DomLoopState:
    suppress_main_click_until: float
    last_spell_click: float
    last_trade_action: float
    last_building_action: float
    last_upgrade_action: float
    last_combo_action_click: float
    last_wrinkler_action: float
    last_dragon_action: float
    last_note_dismiss_action: float
    last_lump_action: float
    last_upgrade_skip_signature: Any
    post_upgrade_wrinkler_cooldown_until: float
    last_upgrade_focus_signature: Any
    last_upgrade_focus_at: float
    last_upgrade_focus_point: Any
    last_seen_golden_decision: Any
    last_feed_signature: Any
    last_feed_debug_at: float
    bank_diag_cache: BankDiagCache


@dataclass(frozen=True)
class DomLoopDiagnostics:
    garden_diag: dict[str, Any]
    lump_diag: dict[str, Any]
    building_diag: dict[str, Any]
    ascension_prep_diag: dict[str, Any]
    upgrade_diag: dict[str, Any]
    dragon_diag: dict[str, Any]
    santa_diag: dict[str, Any]
    golden_diag: dict[str, Any]
    spell_diag: dict[str, Any]
    reserve_budget: dict[str, Any]
    purchase_goal: dict[str, Any] | None
    stock_buy_controls: dict[str, Any]
    stock_management_active: bool
    bank_diag: dict[str, Any]
    wrinkler_diag: dict[str, Any]
    combo_diag: dict[str, Any]
    trade_stats: dict[str, Any]
    spell_stats: dict[str, Any]
    combo_stats: dict[str, Any]
    pause_reasons: tuple[str, ...]
    pause_non_click_actions: bool
    pause_stock_trading: bool
    allow_non_click_actions_during_pause: bool
    defer_stock_for_upgrade: bool


class SleepFn(Protocol):
    def __call__(self, seconds: float) -> None: ...


@dataclass(frozen=True)
class DomLoopActionOutcome:
    handled: bool = False
    updates: dict[str, Any] | None = None


@dataclass(frozen=True)
class UpgradeStagePlan:
    upgrade_action: Any = None
    upgrade_store_action: Any = None


@dataclass(frozen=True)
class AscensionStagePlan:
    action: Any = None
    store_action: Any = None


@dataclass(frozen=True)
class BuildingStagePlan:
    building_action: Any = None
    store_action: Any = None
    signature: Any = None
    signature_blocked: bool = False


@dataclass(frozen=True)
class MinigameStorePlan:
    owner: str | None = None
    store_action: Any = None


@dataclass(frozen=True)
class DomLoopEarlyStageContext:
    snapshot: dict[str, Any] | None
    shimmers: list[dict[str, Any]]
    lump_diag: dict[str, Any]
    garden_diag: dict[str, Any]
    building_diag: dict[str, Any]
    now: float
    action_started: float
    last_lump_action: float
    last_note_dismiss_action: float
    last_combo_action_click: float
    last_spell_click: float
    pause_non_click_actions: bool
    allow_non_click_actions_during_pause: bool
    pause_value_actions_during_clot: bool
    garden_automation_enabled: bool
    auto_cast_hand_of_fate: bool


@dataclass(frozen=True)
class DomLoopLateStageContext:
    snapshot: dict[str, Any] | None
    shimmers: list[dict[str, Any]]
    upgrade_diag: dict[str, Any]
    dragon_diag: dict[str, Any]
    combo_diag: dict[str, Any]
    spell_diag: dict[str, Any]
    purchase_goal: dict[str, Any] | None
    stock_buy_controls: dict[str, Any]
    stock_management_active: bool
    bank_diag: dict[str, Any]
    garden_diag: dict[str, Any]
    building_diag: dict[str, Any]
    building_cookie_reserve: float
    garden_cookie_reserve: float
    lucky_cookie_reserve: float
    global_cookie_reserve: float
    pause_non_click_actions: bool
    allow_non_click_actions_during_pause: bool
    pause_stock_trading: bool
    pause_reasons: tuple[str, ...] | list[str]
    upgrade_autobuy_enabled: bool
    ascension_prep_enabled: bool
    stock_trading_enabled: bool
    building_autobuy_enabled: bool
    combo_pending: bool
    combo_phase: Any
    now: float
    action_started: float
    upgrade_action: Any
    upgrade_store_action: Any
    upgrade_signature: Any
    upgrade_blocked_until: float
    upgrade_signature_blocked: bool
    cookies_after_upgrade_reserve: bool
    defer_stock_for_upgrade_live: bool
    last_upgrade_action: float
    last_upgrade_skip_signature: Any
    last_upgrade_focus_signature: Any
    last_upgrade_focus_at: float
    last_upgrade_focus_point: Any
    last_wrinkler_action: float
    post_upgrade_wrinkler_cooldown_until: float
    last_dragon_action: float
    last_building_action: float
    last_trade_action: float
    upgrade_attempt_tracker: dict[str, Any]
    building_attempt_tracker: dict[str, Any]


@dataclass(frozen=True)
class DomLoopLateStagePreparation:
    allow_upgrade_during_pause: bool
    combo_pending: bool
    upgrade_signature: Any
    upgrade_blocked_until: float
    upgrade_signature_blocked: bool
    defer_stock_for_upgrade_live: bool
    cookies_after_upgrade_reserve: bool
    upgrade_action: Any = None
    upgrade_store_action: Any = None


@dataclass(frozen=True)
class DomShimmerContext:
    snapshot: dict[str, Any] | None
    shimmers: list[dict[str, Any]]
    buffs: list[dict[str, Any]]
    now: float
    pause_value_actions_during_clot: bool
    shimmer_autoclick_enabled: bool
    last_seen_golden_decision: Any
    suppress_main_click_until: float


@dataclass(frozen=True)
class DomShimmerResult:
    handled: bool
    last_seen_golden_decision: Any
    suppress_main_click_until: float


@dataclass(frozen=True)
class DomLoopEarlyStageState:
    last_lump_action: float
    last_note_dismiss_action: float
    last_combo_action_click: float
    last_spell_click: float


@dataclass(frozen=True)
class DomLoopLateStageState:
    last_upgrade_action: float
    last_upgrade_skip_signature: Any
    post_upgrade_wrinkler_cooldown_until: float
    last_upgrade_focus_signature: Any
    last_upgrade_focus_at: float
    last_upgrade_focus_point: Any
    last_wrinkler_action: float
    last_dragon_action: float
    last_trade_action: float
    last_building_action: float


class DomActionCoordinator:
    """Runs prioritized action stages and returns the first handled outcome."""

    def run(self, stages: tuple[Callable[[], DomLoopActionOutcome], ...]) -> DomLoopActionOutcome:
        for stage in stages:
            outcome = stage()
            if outcome.handled:
                return outcome
        return DomLoopActionOutcome()


class DomActionPlanner:
    """Builds action plans so dom_loop can focus on orchestration."""

    def __init__(
        self,
        *,
        plan_reset_store_to_default: Callable[[dict[str, Any] | None, Callable[[int, int], tuple[int, int]]], Any],
        plan_upgrade_buy: Callable[[dict[str, Any] | None, Callable[[int, int], tuple[int, int]], int], Any],
        get_wrinkler_action: Callable[..., Any],
        get_desired_dragon_auras: Callable[..., dict[str, Any] | None],
        plan_dragon_aura_action: Callable[..., dict[str, Any] | None],
        is_dragon_aura_unlocked: Callable[[int, Any], bool],
        get_ascension_action: Callable[..., Any],
        plan_building_buy: Callable[..., Any],
        plan_building_sell: Callable[..., Any],
        get_trade_action: Callable[..., Any],
        get_building_action: Callable[..., Any],
        has_cookies_after_reserve: Callable[[dict[str, Any] | None, Any, float], bool],
        plan_minigame_store_access: Callable[..., tuple[str | None, Any]],
    ):
        self._plan_reset_store_to_default = plan_reset_store_to_default
        self._plan_upgrade_buy = plan_upgrade_buy
        self._get_wrinkler_action = get_wrinkler_action
        self._get_desired_dragon_auras = get_desired_dragon_auras
        self._plan_dragon_aura_action = plan_dragon_aura_action
        self._is_dragon_aura_unlocked = is_dragon_aura_unlocked
        self._get_ascension_action = get_ascension_action
        self._plan_building_buy = plan_building_buy
        self._plan_building_sell = plan_building_sell
        self._get_trade_action = get_trade_action
        self._get_building_action = get_building_action
        self._has_cookies_after_reserve = has_cookies_after_reserve
        self._plan_minigame_store_access = plan_minigame_store_access

    def plan_upgrade(
        self,
        *,
        snapshot: dict[str, Any] | None,
        to_screen_point: Callable[[int, int], tuple[int, int]],
        upgrade_diag: dict[str, Any],
        global_cookie_reserve: float,
    ) -> UpgradeStagePlan:
        if not bool(upgrade_diag.get("candidate_can_buy")) or upgrade_diag.get("candidate_id") is None:
            return UpgradeStagePlan()
        if not self._has_cookies_after_reserve(
            snapshot,
            upgrade_diag.get("candidate_price"),
            global_cookie_reserve,
        ):
            return UpgradeStagePlan()
        store_state = snapshot.get("store") if isinstance(snapshot, dict) else None
        store_buy_mode = None if not isinstance(store_state, dict) else store_state.get("buyMode")
        store_buy_bulk = None if not isinstance(store_state, dict) else store_state.get("buyBulk")
        if store_buy_mode != 1 or store_buy_bulk != 1:
            upgrade_store_action = self._plan_reset_store_to_default(snapshot, to_screen_point)
            if upgrade_store_action is not None and upgrade_store_action.kind == "store_ready":
                upgrade_store_action = None
            return UpgradeStagePlan(upgrade_store_action=upgrade_store_action)
        return UpgradeStagePlan(
            upgrade_action=self._plan_upgrade_buy(
                snapshot,
                to_screen_point,
                int(upgrade_diag["candidate_id"]),
            )
        )

    def plan_wrinkler(
        self,
        *,
        snapshot: dict[str, Any] | None,
        to_screen_point: Callable[[int, int], tuple[int, int]],
        now: float,
        purchase_goal: dict[str, Any] | None,
    ) -> Any:
        return self._get_wrinkler_action(
            snapshot,
            to_screen_point,
            now=now,
            pop_goal=purchase_goal,
        )

    def plan_dragon(
        self,
        *,
        dragon_diag: dict[str, Any],
        combo_diag: dict[str, Any],
        spell_diag: dict[str, Any],
        allow_aura_actions: bool,
    ) -> dict[str, Any] | None:
        if allow_aura_actions:
            aura_action = self._plan_dragon_aura_action(dragon_diag, combo_diag, spell_diag=spell_diag)
            if aura_action is not None:
                return aura_action
        if (
            dragon_diag.get("open")
            and not dragon_diag.get("actionable")
            and dragon_diag.get("reason") == "waiting_for_dragon_building_floor"
        ):
            target = dragon_diag.get("close_target")
            if target is not None:
                return {
                    "kind": "close_dragon",
                    "screen_x": target["screen_x"],
                    "screen_y": target["screen_y"],
                }
        if (
            dragon_diag.get("actionable")
            and not spell_diag.get("reactive_combo_stack")
            and not spell_diag.get("valuable_buffs")
        ):
            target = dragon_diag.get("action_target") if dragon_diag.get("open") else dragon_diag.get("open_target")
            if target is not None:
                return {
                    "kind": "upgrade_dragon" if dragon_diag.get("open") else "open_dragon",
                    "screen_x": target["screen_x"],
                    "screen_y": target["screen_y"],
                }
        desired_dragon_auras = self._get_desired_dragon_auras(combo_diag, spell_diag=spell_diag)
        if desired_dragon_auras is None or dragon_diag.get("open"):
            return None
        dragon_level = int(dragon_diag.get("level") or 0)
        wants_primary = self._is_dragon_aura_unlocked(
            dragon_level, desired_dragon_auras.get("primary_id")
        ) and dragon_diag.get("aura_primary_id") != desired_dragon_auras.get("primary_id")
        wants_secondary = (
            dragon_level >= 27
            and self._is_dragon_aura_unlocked(dragon_level, desired_dragon_auras.get("secondary_id"))
            and dragon_diag.get("aura_secondary_id") != desired_dragon_auras.get("secondary_id")
        )
        if not (wants_primary or wants_secondary):
            return None
        target = dragon_diag.get("open_target")
        if target is None:
            return None
        return {
            "kind": "open_dragon",
            "screen_x": target["screen_x"],
            "screen_y": target["screen_y"],
            "detail": "open_for_aura",
        }

    def plan_ascension_prep(
        self,
        *,
        snapshot: dict[str, Any] | None,
        to_screen_point: Callable[[int, int], tuple[int, int]],
        now: float,
    ) -> AscensionStagePlan:
        action = self._get_ascension_action(snapshot, now=now)
        if action is None:
            return AscensionStagePlan()
        store_action = None
        if action.kind == "buy":
            store_action = self._plan_building_buy(
                snapshot,
                to_screen_point,
                action.building_id,
                quantity=action.quantity,
            )
        elif action.kind == "sell":
            store_action = self._plan_building_sell(
                snapshot,
                to_screen_point,
                action.building_id,
                quantity=action.quantity,
            )
        return AscensionStagePlan(action=action, store_action=store_action)

    def plan_trade(
        self,
        *,
        snapshot: dict[str, Any] | None,
        to_screen_point: Callable[[int, int], tuple[int, int]],
        now: float,
        stock_trading_enabled: bool,
        stock_buy_controls: dict[str, Any],
    ) -> Any:
        return self._get_trade_action(
            snapshot,
            to_screen_point,
            now=now,
            allow_buy_actions=(stock_trading_enabled and stock_buy_controls["allow_buy_actions"]),
            allow_sell_actions=True,
            buy_reserve_cookies=stock_buy_controls["buy_reserve_cookies"],
        )

    def plan_building(
        self,
        *,
        snapshot: dict[str, Any] | None,
        to_screen_point: Callable[[int, int], tuple[int, int]],
        now: float,
        building_diag: dict[str, Any],
        building_cookie_reserve: float,
        build_signature: Callable[[Any], Any],
        blocked_signature: Any,
        blocked_until: float,
    ) -> BuildingStagePlan:
        if not self._has_cookies_after_reserve(
            snapshot,
            building_diag.get("next_candidate_price"),
            building_cookie_reserve,
        ):
            return BuildingStagePlan()
        building_action = self._get_building_action(snapshot, to_screen_point, now=now)
        signature = build_signature(building_action)
        signature_blocked = (
            blocked_signature is not None
            and now < blocked_until
            and signature == blocked_signature
        )
        if building_action is None:
            return BuildingStagePlan(signature=signature, signature_blocked=signature_blocked)
        if building_action.kind == "sell_building":
            store_action = self._plan_building_sell(
                snapshot,
                to_screen_point,
                building_action.building_id,
                quantity=building_action.quantity or 1,
            )
        else:
            store_action = self._plan_building_buy(
                snapshot,
                to_screen_point,
                building_action.building_id,
                quantity=building_action.quantity or 1,
            )
        return BuildingStagePlan(
            building_action=building_action,
            store_action=store_action,
            signature=signature,
            signature_blocked=signature_blocked,
        )

    def plan_minigame_store_access(
        self,
        *,
        snapshot: dict[str, Any] | None,
        spell_diag: dict[str, Any],
        bank_diag: dict[str, Any],
        garden_diag: dict[str, Any],
    ) -> MinigameStorePlan:
        owner, store_action = self._plan_minigame_store_access(
            snapshot,
            spell_diag,
            bank_diag,
            garden_diag,
        )
        return MinigameStorePlan(owner=owner, store_action=store_action)


class DomAttemptTracker:
    """Maintains candidate attempt state and blocker-signature logging."""

    @staticmethod
    def sync_tracker(
        tracker: dict[str, Any],
        *,
        candidate_id: Any,
        candidate_signature: Any,
        now: float,
    ) -> None:
        if candidate_id is None or candidate_signature is None:
            tracker["candidate_id"] = None
            tracker["attempts"] = 0
            tracker["candidate_signature"] = None
            if now >= float(tracker.get("blocked_until") or 0.0):
                tracker["blocked_until"] = 0.0
                tracker["blocked_signature"] = None
            return
        try:
            candidate_id = int(candidate_id)
        except Exception:
            tracker["candidate_id"] = None
            tracker["attempts"] = 0
            tracker["candidate_signature"] = None
            if now >= float(tracker.get("blocked_until") or 0.0):
                tracker["blocked_until"] = 0.0
                tracker["blocked_signature"] = None
            return
        if (
            tracker["candidate_id"] != candidate_id
            or tracker.get("candidate_signature") != candidate_signature
        ):
            tracker["candidate_id"] = candidate_id
            tracker["attempts"] = 0
            tracker["candidate_signature"] = candidate_signature
            if (
                now >= float(tracker.get("blocked_until") or 0.0)
                or tracker.get("blocked_signature") != candidate_signature
            ):
                tracker["blocked_until"] = 0.0
                tracker["blocked_signature"] = None

    @staticmethod
    def is_signature_blocked(
        tracker: dict[str, Any],
        *,
        candidate_signature: Any,
        now: float,
    ) -> bool:
        return (
            candidate_signature is not None
            and now < float(tracker.get("blocked_until") or 0.0)
            and tracker.get("blocked_signature") is not None
            and tracker.get("blocked_signature") == candidate_signature
        )

    @staticmethod
    def log_upgrade_blockers(
        *,
        log: Any,
        last_signature: Any,
        snapshot: dict[str, Any] | None,
        upgrade_diag: dict[str, Any],
        blockers: list[str],
    ) -> Any:
        signature = (
            upgrade_diag.get("candidate_id"),
            tuple(blockers),
            snapshot.get("store", {}).get("buyMode") if isinstance(snapshot, dict) else None,
            snapshot.get("store", {}).get("buyBulk") if isinstance(snapshot, dict) else None,
        )
        if signature == last_signature:
            return last_signature
        log.info(
            f"Upgrade candidate blocked name={upgrade_diag.get('candidate')} "
            f"id={upgrade_diag.get('candidate_id')} "
            f"price={0.0 if upgrade_diag.get('candidate_price') is None else float(upgrade_diag.get('candidate_price')):.1f} "
            f"cookies={0.0 if snapshot is None else float(snapshot.get('cookies') or 0.0):.1f} "
            f"store_mode={snapshot.get('store', {}).get('buyMode') if isinstance(snapshot, dict) and isinstance(snapshot.get('store'), dict) else None} "
            f"store_bulk={snapshot.get('store', {}).get('buyBulk') if isinstance(snapshot, dict) and isinstance(snapshot.get('store'), dict) else None} "
            f"reasons={'; '.join(blockers)}"
        )
        return signature


class DomStagePolicy:
    """Encapsulates loop-stage gating and cooldown checks."""

    @staticmethod
    def can_plan_upgrade(
        *,
        upgrade_autobuy_enabled: bool,
        pause_non_click_actions: bool,
        allow_upgrade_during_pause: bool,
        combo_pending: bool,
        shimmers_present: bool,
        upgrade_signature_blocked: bool,
        now: float,
        upgrade_blocked_until: float,
        last_upgrade_action: float,
        upgrade_action_cooldown: float,
        upgrade_diag: dict[str, Any],
    ) -> bool:
        return (
            upgrade_autobuy_enabled
            and (not pause_non_click_actions or allow_upgrade_during_pause)
            and not combo_pending
            and not shimmers_present
            and not upgrade_signature_blocked
            and now >= upgrade_blocked_until
            and (now - last_upgrade_action) >= upgrade_action_cooldown
            and bool(upgrade_diag.get("candidate_can_buy"))
            and upgrade_diag.get("candidate_id") is not None
        )

    @staticmethod
    def build_upgrade_blockers(
        *,
        upgrade_autobuy_enabled: bool,
        pause_non_click_actions: bool,
        pause_reasons: tuple[str, ...] | list[str],
        allow_upgrade_during_pause: bool,
        upgrade_diag: dict[str, Any],
        combo_pending: bool,
        combo_phase: Any,
        shimmers_present: bool,
        shimmer_count: int,
        now: float,
        upgrade_blocked_until: float,
        upgrade_signature_blocked: bool,
        cookies_after_reserve: bool,
        global_cookie_reserve: float,
        garden_cookie_reserve: float,
        lucky_cookie_reserve: float,
        last_upgrade_action: float,
        upgrade_action_cooldown: float,
    ) -> list[str]:
        blockers = []
        if not upgrade_autobuy_enabled:
            blockers.append("upgrade_autobuy_disabled")
        if pause_non_click_actions:
            blockers.append(
                f"pause_non_click_actions "
                f"reasons={tuple(pause_reasons)} "
                f"allow_upgrade_during_pause={allow_upgrade_during_pause} "
                f"buff_window_seconds={upgrade_diag.get('buff_window_seconds')} "
                f"estimated_live_delta_cps={upgrade_diag.get('estimated_live_delta_cps')} "
                f"estimated_buff_window_gain={upgrade_diag.get('estimated_buff_window_gain')} "
                f"window_reason={upgrade_diag.get('pause_window_reason')}"
            )
        if combo_pending:
            blockers.append(f"combo_pending phase={combo_phase}")
        if shimmers_present:
            blockers.append(f"shimmers_present count={shimmer_count}")
        if now < upgrade_blocked_until:
            blockers.append(
                f"stuck_candidate_backoff_remaining={max(0.0, upgrade_blocked_until - now):.3f}s"
            )
        elif upgrade_signature_blocked:
            blockers.append("stuck_candidate_signature_unchanged")
        if not cookies_after_reserve:
            blockers.append(
                f"global_reserve={global_cookie_reserve:.1f} "
                f"(garden={garden_cookie_reserve:.1f} lucky={lucky_cookie_reserve:.1f})"
            )
        cooldown_remaining = upgrade_action_cooldown - (now - last_upgrade_action)
        if (now - last_upgrade_action) < upgrade_action_cooldown:
            blockers.append(f"cooldown_remaining={max(0.0, cooldown_remaining):.3f}s")
        if not blockers:
            blockers.append("plan_buy_returned_none")
        return blockers

    @staticmethod
    def can_plan_wrinkler(
        *,
        combo_pending: bool,
        shimmers_present: bool,
        now: float,
        last_wrinkler_action: float,
        wrinkler_action_cooldown: float,
        post_upgrade_wrinkler_cooldown_until: float,
        purchase_goal: dict[str, Any] | None,
    ) -> bool:
        return (
            not combo_pending
            and not shimmers_present
            and (now - last_wrinkler_action) >= wrinkler_action_cooldown
            and not (
                now < post_upgrade_wrinkler_cooldown_until
                and isinstance(purchase_goal, dict)
                and purchase_goal.get("kind") == "upgrade"
            )
        )

    @staticmethod
    def can_plan_dragon(
        *,
        dragon_diag: dict[str, Any],
        pause_non_click_actions: bool,
        allow_non_click_actions_during_pause: bool,
        combo_pending: bool,
        shimmers_present: bool,
        now: float,
        last_dragon_action: float,
        dragon_action_cooldown: float,
    ) -> bool:
        return (
            dragon_diag.get("available")
            and (not pause_non_click_actions or allow_non_click_actions_during_pause)
            and not combo_pending
            and not shimmers_present
            and (now - last_dragon_action) >= dragon_action_cooldown
        )

    @staticmethod
    def can_plan_santa(
        *,
        pause_non_click_actions: bool,
        allow_non_click_actions_during_pause: bool,
        combo_pending: bool,
        shimmers_present: bool,
    ) -> bool:
        return (
            not pause_non_click_actions or allow_non_click_actions_during_pause
        ) and not combo_pending and not shimmers_present

    @staticmethod
    def allow_dragon_aura_actions(
        *,
        now: float,
        last_dragon_action: float,
        dragon_aura_action_cooldown: float,
    ) -> bool:
        return (now - last_dragon_action) >= dragon_aura_action_cooldown

    @staticmethod
    def can_plan_ascension(
        *,
        ascension_prep_enabled: bool,
        pause_non_click_actions: bool,
        allow_non_click_actions_during_pause: bool,
        combo_pending: bool,
        shimmers_present: bool,
        now: float,
        last_building_action: float,
        building_action_cooldown: float,
    ) -> bool:
        return (
            ascension_prep_enabled
            and (not pause_non_click_actions or allow_non_click_actions_during_pause)
            and not combo_pending
            and not shimmers_present
            and (now - last_building_action) >= building_action_cooldown
        )

    @staticmethod
    def can_plan_trade(
        *,
        ascension_prep_enabled: bool,
        stock_management_active: bool,
        pause_non_click_actions: bool,
        allow_non_click_actions_during_pause: bool,
        pause_stock_trading: bool,
        defer_stock_for_upgrade_live: bool,
        shimmers_present: bool,
        now: float,
        last_trade_action: float,
        trade_action_cooldown: float,
    ) -> bool:
        return (
            not ascension_prep_enabled
            and stock_management_active
            and (not pause_non_click_actions or allow_non_click_actions_during_pause)
            and not pause_stock_trading
            and not defer_stock_for_upgrade_live
            and not shimmers_present
            and (now - last_trade_action) >= trade_action_cooldown
        )

    @staticmethod
    def can_plan_building(
        *,
        ascension_prep_enabled: bool,
        building_autobuy_enabled: bool,
        pause_non_click_actions: bool,
        allow_non_click_actions_during_pause: bool,
        shimmers_present: bool,
        now: float,
        last_building_action: float,
        building_action_cooldown: float,
    ) -> bool:
        return (
            not ascension_prep_enabled
            and building_autobuy_enabled
            and (not pause_non_click_actions or allow_non_click_actions_during_pause)
            and not shimmers_present
            and (now - last_building_action) >= building_action_cooldown
        )


class DomLoopLateStagePreparer:
    """Computes late-stage loop state before execution stages run."""

    def __init__(
        self,
        *,
        action_planner: DomActionPlanner,
        attempt_tracker: DomAttemptTracker,
        stage_policy: DomStagePolicy,
        update_upgrade_attempt_tracking: Callable[[dict[str, Any] | None, dict[str, Any], float], None],
        build_upgrade_attempt_signature: Callable[[dict[str, Any] | None, dict[str, Any]], Any],
        should_defer_stock_actions_for_upgrade: Callable[..., bool],
        has_cookies_after_reserve: Callable[[dict[str, Any] | None, Any, float], bool],
        to_screen_point: Callable[[int, int], tuple[int, int]],
        upgrade_action_cooldown: float,
    ):
        self._action_planner = action_planner
        self._attempt_tracker = attempt_tracker
        self._stage_policy = stage_policy
        self._update_upgrade_attempt_tracking = update_upgrade_attempt_tracking
        self._build_upgrade_attempt_signature = build_upgrade_attempt_signature
        self._should_defer_stock_actions_for_upgrade = should_defer_stock_actions_for_upgrade
        self._has_cookies_after_reserve = has_cookies_after_reserve
        self._to_screen_point = to_screen_point
        self._upgrade_action_cooldown = upgrade_action_cooldown

    def prepare(
        self,
        *,
        snapshot: dict[str, Any] | None,
        upgrade_diag: dict[str, Any],
        shimmers: list[dict[str, Any]],
        now: float,
        upgrade_attempt_tracker: dict[str, Any],
        upgrade_autobuy_enabled: bool,
        pause_non_click_actions: bool,
        allow_non_click_actions_during_pause: bool,
        global_cookie_reserve: float,
        last_upgrade_action: float,
        combo_pending: bool,
    ) -> DomLoopLateStagePreparation:
        allow_upgrade_during_pause = (
            bool(upgrade_diag.get("allow_during_pause")) or allow_non_click_actions_during_pause
        )
        self._update_upgrade_attempt_tracking(snapshot, upgrade_diag, now)
        upgrade_signature = self._build_upgrade_attempt_signature(snapshot, upgrade_diag)
        upgrade_blocked_until = float(upgrade_attempt_tracker.get("blocked_until") or 0.0)
        upgrade_signature_blocked = self._attempt_tracker.is_signature_blocked(
            upgrade_attempt_tracker,
            candidate_signature=upgrade_signature,
            now=now,
        )
        defer_stock_for_upgrade_live = self._should_defer_stock_actions_for_upgrade(
            snapshot,
            upgrade_diag,
            upgrade_autobuy_enabled=upgrade_autobuy_enabled,
            pause_non_click_actions=pause_non_click_actions,
            allow_upgrade_during_pause=allow_upgrade_during_pause,
            global_cookie_reserve=global_cookie_reserve,
            shimmers_present=bool(shimmers),
            combo_pending=combo_pending,
            upgrade_signature_blocked=upgrade_signature_blocked,
            now=now,
            upgrade_blocked_until=upgrade_blocked_until,
        )
        cookies_after_upgrade_reserve = self._has_cookies_after_reserve(
            snapshot,
            upgrade_diag.get("candidate_price"),
            global_cookie_reserve,
        )
        upgrade_action = None
        upgrade_store_action = None
        if self._stage_policy.can_plan_upgrade(
            upgrade_autobuy_enabled=upgrade_autobuy_enabled,
            pause_non_click_actions=pause_non_click_actions,
            allow_upgrade_during_pause=allow_upgrade_during_pause,
            combo_pending=combo_pending,
            shimmers_present=bool(shimmers),
            upgrade_signature_blocked=upgrade_signature_blocked,
            now=now,
            upgrade_blocked_until=upgrade_blocked_until,
            last_upgrade_action=last_upgrade_action,
            upgrade_action_cooldown=self._upgrade_action_cooldown,
            upgrade_diag=upgrade_diag,
        ) and cookies_after_upgrade_reserve:
            upgrade_plan = self._action_planner.plan_upgrade(
                snapshot=snapshot,
                to_screen_point=self._to_screen_point,
                upgrade_diag=upgrade_diag,
                global_cookie_reserve=global_cookie_reserve,
            )
            upgrade_action = upgrade_plan.upgrade_action
            upgrade_store_action = upgrade_plan.upgrade_store_action
        return DomLoopLateStagePreparation(
            allow_upgrade_during_pause=allow_upgrade_during_pause,
            combo_pending=combo_pending,
            upgrade_signature=upgrade_signature,
            upgrade_blocked_until=upgrade_blocked_until,
            upgrade_signature_blocked=upgrade_signature_blocked,
            defer_stock_for_upgrade_live=defer_stock_for_upgrade_live,
            cookies_after_upgrade_reserve=cookies_after_upgrade_reserve,
            upgrade_action=upgrade_action,
            upgrade_store_action=upgrade_store_action,
        )


class DomShimmerHandler:
    """Owns shimmer tracking, resolution, and click dispatch."""

    _FORTUNE_STALE_AFTER_CLICK_SECONDS = 0.35

    def __init__(
        self,
        *,
        log: Any,
        click_lock: Any,
        click_shimmer: Callable[..., None],
        can_interact_with_game: Callable[[float], bool],
        sleep: SleepFn,
        monotonic: Callable[[], float],
        perf_counter: Callable[[], float],
        record_profile_ms: Callable[[str, float], None],
        should_skip_wrath_shimmer: Callable[..., bool],
        format_shimmer_id_list: Callable[..., str],
        reset_shimmer_tracking: Callable[..., None],
        record_shimmer_outcome: Callable[[dict[str, Any]], None],
        record_event: Callable[[str], None],
        record_shimmer_click_runtime: Callable[[int, str], None],
        record_shimmer_collect_runtime: Callable[[str, int, str, bool], None],
        overlay_event_sender: Callable[..., None] | None = None,
        get_pending_hand_shimmer: Callable[..., dict[str, Any] | None],
        clear_pending_hand_shimmer: Callable[[int], None],
        recent_shimmer_clicks: dict[int, float],
        shimmer_first_seen: dict[int, float],
        shimmer_click_attempts: dict[int, dict[str, Any]],
        pending_shimmer_results: dict[int, dict[str, Any]],
        main_click_suppress_seconds: float,
        bonus_click_hold: float,
        feed_poll_interval: float,
        shimmer_click_delay_seconds: float,
        shimmer_click_cooldown: float,
        overlay_click_delay_seconds: float = 1.0,
    ):
        self._log = log
        self._click_lock = click_lock
        self._click_shimmer = click_shimmer
        self._can_interact_with_game = can_interact_with_game
        self._sleep = sleep
        self._monotonic = monotonic
        self._perf_counter = perf_counter
        self._record_profile_ms = record_profile_ms
        self._should_skip_wrath_shimmer = should_skip_wrath_shimmer
        self._format_shimmer_id_list = format_shimmer_id_list
        self._reset_shimmer_tracking = reset_shimmer_tracking
        self._record_shimmer_outcome = record_shimmer_outcome
        self._record_event = record_event
        self._record_shimmer_click_runtime = record_shimmer_click_runtime
        self._record_shimmer_collect_runtime = record_shimmer_collect_runtime
        self._overlay_event_sender = overlay_event_sender
        self._get_pending_hand_shimmer = get_pending_hand_shimmer
        self._clear_pending_hand_shimmer = clear_pending_hand_shimmer
        self._recent_shimmer_clicks = recent_shimmer_clicks
        self._shimmer_first_seen = shimmer_first_seen
        self._shimmer_click_attempts = shimmer_click_attempts
        self._pending_shimmer_results = pending_shimmer_results
        self._main_click_suppress_seconds = main_click_suppress_seconds
        self._bonus_click_hold = bonus_click_hold
        self._feed_poll_interval = feed_poll_interval
        self._shimmer_click_delay_seconds = shimmer_click_delay_seconds
        self._shimmer_click_cooldown = shimmer_click_cooldown
        self._overlay_click_delay_seconds = float(overlay_click_delay_seconds)
        self._overlay_preview_started: dict[int, float] = {}
        self._ignored_fortune_ids: set[int] = set()

    def process(self, context: DomShimmerContext) -> DomShimmerResult:
        shimmer_started = self._perf_counter()
        raw_active_ids = {int(item["id"]) for item in context.shimmers}
        for shimmer_id in list(self._ignored_fortune_ids):
            if shimmer_id not in raw_active_ids:
                self._ignored_fortune_ids.discard(shimmer_id)
        self._mark_stale_clicked_fortunes_ignored(context)
        active_ids = {
            int(item["id"])
            for item in context.shimmers
            if int(item["id"]) not in self._ignored_fortune_ids
        }
        active_by_id = {
            int(item["id"]): item
            for item in context.shimmers
            if int(item["id"]) not in self._ignored_fortune_ids
        }
        shimmer_telemetry = context.snapshot.get("shimmerTelemetry") if isinstance(context.snapshot, dict) else None
        last_golden_decision = (
            shimmer_telemetry.get("lastGoldenDecision")
            if isinstance(shimmer_telemetry, dict) and isinstance(shimmer_telemetry.get("lastGoldenDecision"), dict)
            else None
        )
        last_seen_golden_decision = context.last_seen_golden_decision
        suppress_main_click_until = context.suppress_main_click_until

        for shimmer in context.shimmers:
            self._shimmer_first_seen.setdefault(shimmer["id"], context.now)
        for shimmer_id in list(self._recent_shimmer_clicks):
            if shimmer_id not in active_ids:
                self._recent_shimmer_clicks.pop(shimmer_id, None)
        for shimmer_id in list(self._shimmer_first_seen):
            if shimmer_id not in active_ids:
                self._shimmer_first_seen.pop(shimmer_id, None)
        for shimmer_id in list(self._shimmer_click_attempts):
            if shimmer_id not in active_ids:
                self._shimmer_click_attempts.pop(shimmer_id, None)
        for shimmer_id in list(self._overlay_preview_started):
            if shimmer_id not in active_ids:
                self._overlay_preview_started.pop(shimmer_id, None)

        active_buff_names = {buff["name"] for buff in context.buffs if isinstance(buff, dict) and buff.get("name")}
        if isinstance(last_golden_decision, dict):
            decision_id = last_golden_decision.get("shimmerId")
            decision_signature = (
                decision_id,
                last_golden_decision.get("choice"),
                last_golden_decision.get("appliedChoice"),
                last_golden_decision.get("blocked"),
                last_golden_decision.get("timestamp"),
            )
            if decision_signature != last_seen_golden_decision:
                last_seen_golden_decision = decision_signature
                if (
                    decision_id is not None
                    and decision_id not in self._pending_shimmer_results
                    and not bool(last_golden_decision.get("blocked"))
                ):
                    self._reset_shimmer_tracking("untracked_shimmer_resolution", clear_click_state=True)

        for shimmer_id in list(self._pending_shimmer_results):
            if shimmer_id in active_ids:
                continue
            pending = self._pending_shimmer_results.pop(shimmer_id, None)
            if pending is None:
                continue
            self._clear_pending_hand_shimmer(shimmer_id)
            pre_buffs = set(pending.get("buffs", ()))
            new_buffs = sorted(active_buff_names - pre_buffs)
            resolved_choice = None
            decision_blocked = False
            if isinstance(last_golden_decision, dict) and last_golden_decision.get("shimmerId") == shimmer_id:
                resolved_choice = last_golden_decision.get("choice")
                decision_blocked = bool(last_golden_decision.get("blocked"))
            outcome = str(resolved_choice or (", ".join(new_buffs) if new_buffs else "no_new_buff"))
            shimmer_type = str(pending.get("type") or "golden")
            shimmer_kind = "wrath" if shimmer_type == "golden" and pending.get("wrath") else shimmer_type
            clicked_seed = pending.get("seed")
            shimmer_result_entry = {
                "id": shimmer_id,
                "type": shimmer_kind,
                "wrath": pending.get("wrath"),
                "outcome": outcome,
                "new_buffs": new_buffs,
                "seed_at_click": clicked_seed,
                "spawn_lead": pending.get("spawn_lead"),
                "no_count": pending.get("no_count"),
                "force": pending.get("force"),
                "force_obj_type": pending.get("force_obj_type"),
            }
            if not decision_blocked:
                self._record_shimmer_outcome(shimmer_result_entry)
            self._record_shimmer_collect_runtime(shimmer_kind, shimmer_id, outcome, decision_blocked)
            if shimmer_kind == "wrath":
                telemetry_visible_total = None
                telemetry_visible_wrath = None
                telemetry_visible_ids = ()
                if isinstance(last_golden_decision, dict) and last_golden_decision.get("shimmerId") == shimmer_id:
                    telemetry_visible_total = last_golden_decision.get("visibleShimmerCount")
                    telemetry_visible_wrath = last_golden_decision.get("visibleWrathCount")
                    telemetry_visible_ids = tuple(last_golden_decision.get("visibleShimmerIds") or ())
                self._log.info(
                    f"Wrath gate {'BLOCK' if decision_blocked else 'ALLOW'} "
                    f"id={shimmer_id} rolled={outcome} "
                    f"applied={last_golden_decision.get('appliedChoice') if isinstance(last_golden_decision, dict) and last_golden_decision.get('shimmerId') == shimmer_id else outcome} "
                    f"source={pending.get('selection_mode') or 'scan'} "
                    f"clicked_visible={pending.get('visible_count')} "
                    f"clicked_wrath_visible={pending.get('visible_wrath_count')} "
                    f"clicked_ids={self._format_shimmer_id_list(pending.get('visible_ids'))} "
                    f"clicked_wrath_ids={self._format_shimmer_id_list(pending.get('visible_wrath_ids'))} "
                    f"telemetry_visible={telemetry_visible_total if telemetry_visible_total is not None else '-'} "
                    f"telemetry_wrath_visible={telemetry_visible_wrath if telemetry_visible_wrath is not None else '-'} "
                    f"telemetry_ids={self._format_shimmer_id_list(telemetry_visible_ids)} "
                    f"seed={clicked_seed}"
                )
            self._record_event(
                f"Shimmer collected id={shimmer_id} outcome={outcome} seed={clicked_seed}"
                + (" blocked=1" if decision_blocked else "")
            )

        priority_shimmer = self._get_pending_hand_shimmer(context.shimmers, now=context.now)
        should_skip_priority = (
            priority_shimmer is not None
            and priority_shimmer.get("wrath")
            and self._should_skip_wrath_shimmer(context.buffs)
        )
        self._emit_multi_shimmer_overlay_previews(context)
        if (
            context.shimmer_autoclick_enabled
            and priority_shimmer is not None
            and not context.pause_value_actions_during_clot
            and not should_skip_priority
        ):
            target_id = int(priority_shimmer["id"])
            first_seen = self._shimmer_first_seen.get(target_id, context.now)
            if (context.now - first_seen) >= 0.15:
                if not self._can_interact_with_game(context.now):
                    self._sleep(self._feed_poll_interval)
                    return DomShimmerResult(
                        handled=True,
                        last_seen_golden_decision=last_seen_golden_decision,
                        suppress_main_click_until=suppress_main_click_until,
                    )
                visible_ids = tuple(item["id"] for item in context.shimmers)
                visible_wrath_ids = tuple(item["id"] for item in context.shimmers if item.get("wrath"))
                selected_index = next(
                    (index for index, item in enumerate(context.shimmers) if int(item["id"]) == target_id),
                    -1,
                )
                suppress_main_click_until = max(
                    suppress_main_click_until,
                    context.now + self._main_click_suppress_seconds,
                )
                overlay_ready, overlay_pre_emitted = self._prepare_overlay_click_delay(
                    priority_shimmer,
                    context=context,
                    mode="planned",
                )
                if not overlay_ready:
                    self._sleep(self._feed_poll_interval)
                    return DomShimmerResult(
                        handled=True,
                        last_seen_golden_decision=last_seen_golden_decision,
                        suppress_main_click_until=suppress_main_click_until,
                    )
                self._log.info(
                    f"Clicking planned shimmer id={priority_shimmer['id']} type={priority_shimmer['type']} "
                    f"wrath={int(priority_shimmer['wrath'])} "
                    f"visible={len(visible_ids)} visible_wrath={len(visible_wrath_ids)} "
                    f"target_rank={selected_index + 1 if selected_index >= 0 else '-'} "
                    f"visible_ids={self._format_shimmer_id_list(visible_ids)} "
                    f"visible_wrath_ids={self._format_shimmer_id_list(visible_wrath_ids)} "
                    f"client=({priority_shimmer['client_x']},{priority_shimmer['client_y']}) "
                    f"screen=({priority_shimmer['screen_x']},{priority_shimmer['screen_y']})"
                )
                with self._click_lock:
                    self._click_shimmer(
                        priority_shimmer["screen_x"],
                        priority_shimmer["screen_y"],
                        hold=self._bonus_click_hold,
                    )
                click_time = self._monotonic()
                target_id = int(priority_shimmer["id"])
                self._overlay_preview_started.pop(target_id, None)
                self._emit_overlay_spawn(priority_shimmer, mode="planned", clicked_at=click_time)
                self._recent_shimmer_clicks[priority_shimmer["id"]] = click_time
                self._pending_shimmer_results[priority_shimmer["id"]] = self._build_pending_result(
                    shimmer=priority_shimmer,
                    buffs=context.buffs,
                    clicked_at=click_time,
                    selection_mode="planned",
                    visible_ids=visible_ids,
                    visible_wrath_ids=visible_wrath_ids,
                )
                self._shimmer_click_attempts[priority_shimmer["id"]] = {
                    "first_click": click_time,
                    "attempts": 1,
                    "last_logged": 0.0,
                }
                self._record_shimmer_click_runtime(int(priority_shimmer["id"]), "planned")
                self._sleep(self._feed_poll_interval)
                return DomShimmerResult(
                    handled=True,
                    last_seen_golden_decision=last_seen_golden_decision,
                    suppress_main_click_until=suppress_main_click_until,
                )

        for shimmer_id, attempt in list(self._shimmer_click_attempts.items()):
            last_log = float(attempt.get("last_logged", 0.0))
            first_click = float(attempt.get("first_click", 0.0))
            attempts = int(attempt.get("attempts", 0))
            if shimmer_id in active_by_id and attempts > 0 and (context.now - last_log) >= 0.20:
                shimmer = active_by_id[shimmer_id]
                age_since_first = context.now - first_click if first_click else 0.0
                self._log.warning(
                    f"Shimmer still present after click id={shimmer_id} attempts={attempts} "
                    f"age_since_first_click={age_since_first:.3f}s "
                    f"type={shimmer['type']} client=({shimmer['client_x']},{shimmer['client_y']}) "
                    f"life={shimmer['life']} dur={shimmer['dur']}"
                )
                attempt["last_logged"] = context.now

        clicked_shimmer = False
        should_skip_wrath = self._should_skip_wrath_shimmer(context.buffs)
        for shimmer in ([] if context.pause_value_actions_during_clot or not context.shimmer_autoclick_enabled else context.shimmers):
            shimmer_id = int(shimmer["id"])
            if shimmer_id in self._ignored_fortune_ids:
                continue
            if should_skip_wrath and shimmer.get("wrath"):
                self._emit_skipped_wrath_overlay(shimmer, context.now)
                continue
            if shimmer.get("type") == "fortune" and shimmer_id in self._pending_shimmer_results:
                continue
            first_seen = self._shimmer_first_seen.get(shimmer_id, context.now)
            click_delay = 0.15 if shimmer.get("type") == "fortune" else self._shimmer_click_delay_seconds
            if (context.now - first_seen) < click_delay:
                continue
            last_click = self._recent_shimmer_clicks.get(shimmer_id)
            if last_click is not None and (context.now - last_click) < self._shimmer_click_cooldown:
                continue
            if not self._can_interact_with_game(context.now):
                self._sleep(self._feed_poll_interval)
                return DomShimmerResult(
                    handled=True,
                    last_seen_golden_decision=last_seen_golden_decision,
                    suppress_main_click_until=suppress_main_click_until,
                )
            visible_ids = tuple(item["id"] for item in context.shimmers)
            visible_wrath_ids = tuple(item["id"] for item in context.shimmers if item.get("wrath"))
            selected_index = next(
                (index for index, item in enumerate(context.shimmers) if int(item["id"]) == int(shimmer["id"])),
                -1,
            )
            suppress_main_click_until = max(
                suppress_main_click_until,
                context.now + self._main_click_suppress_seconds,
            )
            overlay_ready, overlay_pre_emitted = self._prepare_overlay_click_delay(
                shimmer,
                context=context,
                mode="clicked",
            )
            if not overlay_ready:
                self._sleep(self._feed_poll_interval)
                return DomShimmerResult(
                    handled=True,
                    last_seen_golden_decision=last_seen_golden_decision,
                    suppress_main_click_until=suppress_main_click_until,
                )
            self._log.info(
                f"Clicking shimmer id={shimmer['id']} type={shimmer['type']} "
                f"wrath={int(shimmer['wrath'])} "
                f"spawn_lead={int(bool(shimmer.get('spawn_lead')))} "
                f"force={shimmer.get('force')} "
                f"visible={len(visible_ids)} visible_wrath={len(visible_wrath_ids)} "
                f"target_rank={selected_index + 1 if selected_index >= 0 else '-'} "
                f"visible_ids={self._format_shimmer_id_list(visible_ids)} "
                f"visible_wrath_ids={self._format_shimmer_id_list(visible_wrath_ids)} "
                f"client=({shimmer['client_x']},{shimmer['client_y']}) "
                f"screen=({shimmer['screen_x']},{shimmer['screen_y']})"
            )
            with self._click_lock:
                self._click_shimmer(
                    shimmer["screen_x"],
                    shimmer["screen_y"],
                    hold=self._bonus_click_hold,
                )
            click_time = self._monotonic()
            self._overlay_preview_started.pop(shimmer_id, None)
            self._emit_overlay_spawn(shimmer, mode="clicked", clicked_at=click_time)
            self._recent_shimmer_clicks[shimmer_id] = click_time
            self._pending_shimmer_results[shimmer_id] = self._build_pending_result(
                shimmer=shimmer,
                buffs=context.buffs,
                clicked_at=click_time,
                selection_mode="scan",
                visible_ids=visible_ids,
                visible_wrath_ids=visible_wrath_ids,
            )
            previous_attempt = self._shimmer_click_attempts.get(shimmer_id)
            self._shimmer_click_attempts[shimmer_id] = {
                "first_click": click_time if previous_attempt is None else previous_attempt.get("first_click", click_time),
                "attempts": 1 if previous_attempt is None else int(previous_attempt.get("attempts", 0)) + 1,
                "last_logged": 0.0,
            }
            self._record_shimmer_click_runtime(int(shimmer["id"]), "clicked")
            clicked_shimmer = True
            break

        self._record_profile_ms(
            "dom_shimmer",
            (self._perf_counter() - shimmer_started) * 1000.0,
            spike_ms=20.0,
        )
        if clicked_shimmer:
            self._sleep(self._feed_poll_interval)
        return DomShimmerResult(
            handled=clicked_shimmer,
            last_seen_golden_decision=last_seen_golden_decision,
            suppress_main_click_until=suppress_main_click_until,
        )

    def _mark_stale_clicked_fortunes_ignored(self, context: DomShimmerContext) -> None:
        for shimmer in context.shimmers:
            if shimmer.get("type") != "fortune":
                continue
            shimmer_id = int(shimmer["id"])
            if shimmer_id not in self._pending_shimmer_results:
                continue
            attempt = self._shimmer_click_attempts.get(shimmer_id)
            first_click = 0.0 if not isinstance(attempt, dict) else float(attempt.get("first_click", 0.0))
            if not first_click or (context.now - first_click) < self._FORTUNE_STALE_AFTER_CLICK_SECONDS:
                continue
            self._ignored_fortune_ids.add(shimmer_id)

    def _prepare_overlay_click_delay(
        self,
        shimmer: dict[str, Any],
        *,
        context: DomShimmerContext,
        mode: str,
    ) -> tuple[bool, bool]:
        if not self._should_delay_for_overlay(context, shimmer):
            return True, False
        shimmer_id = int(shimmer["id"])
        started_at = self._overlay_preview_started.get(shimmer_id)
        if started_at is None:
            self._emit_overlay_spawn(shimmer, mode=f"{mode}_preview", clicked_at=context.now)
            self._overlay_preview_started[shimmer_id] = context.now
            return False, True
        return (context.now - started_at) >= self._overlay_click_delay_seconds, True

    def _should_delay_for_overlay(self, context: DomShimmerContext, shimmer: dict[str, Any]) -> bool:
        if self._overlay_event_sender is None:
            return False
        if self._overlay_click_delay_seconds <= 0:
            return False
        if shimmer.get("type") == "fortune":
            return False
        if len(context.shimmers) > 1:
            return False
        return True

    def _emit_multi_shimmer_overlay_previews(self, context: DomShimmerContext) -> None:
        if self._overlay_event_sender is None:
            return
        if len(context.shimmers) <= 1:
            return
        for shimmer in context.shimmers:
            shimmer_id = int(shimmer["id"])
            if shimmer_id in self._overlay_preview_started:
                continue
            self._emit_overlay_spawn(shimmer, mode="visible_preview", clicked_at=context.now)
            self._overlay_preview_started[shimmer_id] = context.now

    def _emit_overlay_spawn(self, shimmer: dict[str, Any], *, mode: str, clicked_at: float) -> None:
        if self._overlay_event_sender is None:
            return
        try:
            self._overlay_event_sender(shimmer, mode=mode, clicked_at=clicked_at)
        except Exception as exc:
            try:
                self._log.debug(f"Overlay event ignored after shimmer click: {exc}")
            except Exception:
                pass

    def _emit_skipped_wrath_overlay(self, shimmer: dict[str, Any], now: float) -> None:
        if self._overlay_event_sender is None:
            return
        shimmer_id = int(shimmer["id"])
        if shimmer_id in self._overlay_preview_started:
            return
        self._emit_overlay_spawn(shimmer, mode="wrath_skipped_preview", clicked_at=now)
        self._overlay_preview_started[shimmer_id] = now

    @staticmethod
    def _build_pending_result(
        *,
        shimmer: dict[str, Any],
        buffs: list[dict[str, Any]],
        clicked_at: float,
        selection_mode: str,
        visible_ids: tuple[Any, ...],
        visible_wrath_ids: tuple[Any, ...],
    ) -> dict[str, Any]:
        return {
            "buffs": tuple(
                buff["name"] for buff in buffs if isinstance(buff, dict) and buff.get("name")
            ),
            "clicked_at": clicked_at,
            "type": shimmer["type"],
            "wrath": shimmer["wrath"],
            "seed": shimmer.get("seed"),
            "selection_mode": selection_mode,
            "visible_count": len(visible_ids),
            "visible_wrath_count": len(visible_wrath_ids),
            "visible_ids": visible_ids,
            "visible_wrath_ids": visible_wrath_ids,
            "spawn_lead": shimmer.get("spawn_lead"),
            "no_count": shimmer.get("no_count"),
            "force": shimmer.get("force"),
            "force_obj_type": shimmer.get("force_obj_type"),
            "effect_kind": shimmer.get("effect_kind"),
            "effect_name": shimmer.get("effect_name"),
            "effect_id": shimmer.get("effect_id"),
            "text": shimmer.get("text"),
        }


class DomLoopOutcomeHandler:
    """Applies stage outcomes back onto loop state and handles idle fallthrough."""

    def __init__(
        self,
        *,
        perf_counter: Callable[[], float],
        record_profile_ms: Callable[[str, float], None],
        sleep: SleepFn,
        feed_poll_interval: float,
    ):
        self._perf_counter = perf_counter
        self._record_profile_ms = record_profile_ms
        self._sleep = sleep
        self._feed_poll_interval = feed_poll_interval

    @staticmethod
    def apply_early_outcome(
        outcome: DomLoopActionOutcome,
        state: DomLoopEarlyStageState,
    ) -> DomLoopEarlyStageState:
        updates = outcome.updates or {}
        return DomLoopEarlyStageState(
            last_lump_action=updates.get("last_lump_action", state.last_lump_action),
            last_note_dismiss_action=updates.get(
                "last_note_dismiss_action",
                state.last_note_dismiss_action,
            ),
            last_combo_action_click=updates.get(
                "last_combo_action_click",
                state.last_combo_action_click,
            ),
            last_spell_click=updates.get("last_spell_click", state.last_spell_click),
        )

    @staticmethod
    def apply_late_outcome(
        outcome: DomLoopActionOutcome,
        state: DomLoopLateStageState,
    ) -> DomLoopLateStageState:
        updates = outcome.updates or {}
        post_upgrade_wrinkler_cooldown_until = state.post_upgrade_wrinkler_cooldown_until
        if updates.get("post_upgrade_wrinkler_cooldown_until") is not None:
            post_upgrade_wrinkler_cooldown_until = updates["post_upgrade_wrinkler_cooldown_until"]
        return DomLoopLateStageState(
            last_upgrade_action=updates.get("last_upgrade_action", state.last_upgrade_action),
            last_upgrade_skip_signature=updates.get(
                "last_upgrade_skip_signature",
                state.last_upgrade_skip_signature,
            ),
            post_upgrade_wrinkler_cooldown_until=post_upgrade_wrinkler_cooldown_until,
            last_upgrade_focus_signature=updates.get(
                "last_upgrade_focus_signature",
                state.last_upgrade_focus_signature,
            ),
            last_upgrade_focus_at=updates.get("last_upgrade_focus_at", state.last_upgrade_focus_at),
            last_upgrade_focus_point=updates.get(
                "last_upgrade_focus_point",
                state.last_upgrade_focus_point,
            ),
            last_wrinkler_action=updates.get("last_wrinkler_action", state.last_wrinkler_action),
            last_dragon_action=updates.get("last_dragon_action", state.last_dragon_action),
            last_trade_action=updates.get("last_trade_action", state.last_trade_action),
            last_building_action=updates.get("last_building_action", state.last_building_action),
        )

    def handle_idle_fallthrough(self, action_started: float) -> None:
        self._record_profile_ms(
            "dom_action",
            (self._perf_counter() - action_started) * 1000.0,
            spike_ms=25.0,
        )
        self._sleep(self._feed_poll_interval)


class DomLoopCoordinator:
    """Runs one dom_loop cycle using the extracted loop services."""

    def __init__(
        self,
        *,
        cycle_preparer: "DomLoopCyclePreparer",
        feed_logger: "DomLoopFeedLogger",
        shimmer_handler: DomShimmerHandler,
        stage_runner: "DomLoopStageRunner",
        late_stage_preparer: DomLoopLateStagePreparer,
        outcome_handler: DomLoopOutcomeHandler,
        combo_pending_getter: Callable[[], bool],
        perf_counter: Callable[[], float],
    ):
        self._cycle_preparer = cycle_preparer
        self._feed_logger = feed_logger
        self._shimmer_handler = shimmer_handler
        self._stage_runner = stage_runner
        self._late_stage_preparer = late_stage_preparer
        self._outcome_handler = outcome_handler
        self._combo_pending_getter = combo_pending_getter
        self._perf_counter = perf_counter

    def run_cycle(
        self,
        *,
        state: DomLoopState,
        build_options: DomLoopBuildOptions,
        upgrade_attempt_tracker: dict[str, Any],
        building_attempt_tracker: dict[str, Any],
        shimmer_autoclick_enabled: bool,
        auto_cast_hand_of_fate: bool,
    ) -> DomLoopState:
        cycle_state = self._cycle_preparer.prepare_cycle(
            build_options=build_options,
            bank_diag_cache=state.bank_diag_cache,
        )
        prepared = cycle_state.prepared
        diagnostics = cycle_state.diagnostics
        state = replace(
            state,
            bank_diag_cache=cycle_state.bank_diag_cache,
        )
        last_feed_signature, last_feed_debug_at = self._feed_logger.log_if_changed(
            prepared=prepared,
            diagnostics=diagnostics,
            last_feed_signature=state.last_feed_signature,
            last_feed_debug_at=state.last_feed_debug_at,
        )
        state = replace(
            state,
            last_feed_signature=last_feed_signature,
            last_feed_debug_at=last_feed_debug_at,
        )

        shimmer_result = self._shimmer_handler.process(
            DomShimmerContext(
                snapshot=prepared.snapshot,
                shimmers=prepared.shimmers,
                buffs=prepared.buffs,
                now=cycle_state.now,
                pause_value_actions_during_clot=cycle_state.pause_value_actions_during_clot,
                shimmer_autoclick_enabled=shimmer_autoclick_enabled,
                last_seen_golden_decision=state.last_seen_golden_decision,
                suppress_main_click_until=state.suppress_main_click_until,
            )
        )
        state = replace(
            state,
            last_seen_golden_decision=shimmer_result.last_seen_golden_decision,
            suppress_main_click_until=shimmer_result.suppress_main_click_until,
        )
        if shimmer_result.handled:
            return state

        action_started = self._perf_counter()
        early_outcome = self._stage_runner.run_early(
            DomLoopEarlyStageContext(
                snapshot=prepared.snapshot,
                shimmers=prepared.shimmers,
                lump_diag=diagnostics.lump_diag,
                garden_diag=diagnostics.garden_diag,
                building_diag=diagnostics.building_diag,
                now=cycle_state.now,
                action_started=action_started,
                last_lump_action=state.last_lump_action,
                last_note_dismiss_action=state.last_note_dismiss_action,
                last_combo_action_click=state.last_combo_action_click,
                last_spell_click=state.last_spell_click,
                pause_non_click_actions=diagnostics.pause_non_click_actions,
                allow_non_click_actions_during_pause=diagnostics.allow_non_click_actions_during_pause,
                pause_value_actions_during_clot=cycle_state.pause_value_actions_during_clot,
                garden_automation_enabled=build_options.garden_automation_enabled,
                auto_cast_hand_of_fate=auto_cast_hand_of_fate,
            )
        )
        early_state = self._outcome_handler.apply_early_outcome(
            early_outcome,
            DomLoopEarlyStageState(
                last_lump_action=state.last_lump_action,
                last_note_dismiss_action=state.last_note_dismiss_action,
                last_combo_action_click=state.last_combo_action_click,
                last_spell_click=state.last_spell_click,
            ),
        )
        state = replace(
            state,
            last_lump_action=early_state.last_lump_action,
            last_note_dismiss_action=early_state.last_note_dismiss_action,
            last_combo_action_click=early_state.last_combo_action_click,
            last_spell_click=early_state.last_spell_click,
        )
        if early_outcome.handled:
            return state

        combo_pending = self._combo_pending_getter()
        reserve_budget = diagnostics.reserve_budget
        late_stage_prep = self._late_stage_preparer.prepare(
            snapshot=prepared.snapshot,
            upgrade_diag=diagnostics.upgrade_diag,
            shimmers=prepared.shimmers,
            now=cycle_state.now,
            upgrade_attempt_tracker=upgrade_attempt_tracker,
            upgrade_autobuy_enabled=build_options.upgrade_autobuy_enabled,
            pause_non_click_actions=diagnostics.pause_non_click_actions,
            allow_non_click_actions_during_pause=diagnostics.allow_non_click_actions_during_pause,
            global_cookie_reserve=reserve_budget["total_reserve"],
            last_upgrade_action=state.last_upgrade_action,
            combo_pending=combo_pending,
        )
        late_outcome = self._stage_runner.run_late(
            DomLoopLateStageContext(
                snapshot=prepared.snapshot,
                shimmers=prepared.shimmers,
                upgrade_diag=diagnostics.upgrade_diag,
                dragon_diag=diagnostics.dragon_diag,
                combo_diag=diagnostics.combo_diag,
                spell_diag=diagnostics.spell_diag,
                purchase_goal=diagnostics.purchase_goal,
                stock_buy_controls=diagnostics.stock_buy_controls,
                stock_management_active=diagnostics.stock_management_active,
                bank_diag=diagnostics.bank_diag,
                garden_diag=diagnostics.garden_diag,
                building_diag=diagnostics.building_diag,
                building_cookie_reserve=reserve_budget["building_total_reserve"],
                garden_cookie_reserve=reserve_budget["garden_reserve"],
                lucky_cookie_reserve=reserve_budget["lucky_reserve"],
                global_cookie_reserve=reserve_budget["total_reserve"],
                pause_non_click_actions=diagnostics.pause_non_click_actions,
                allow_non_click_actions_during_pause=diagnostics.allow_non_click_actions_during_pause,
                pause_stock_trading=diagnostics.pause_stock_trading,
                pause_reasons=diagnostics.pause_reasons,
                upgrade_autobuy_enabled=build_options.upgrade_autobuy_enabled,
                ascension_prep_enabled=build_options.ascension_prep_enabled,
                stock_trading_enabled=build_options.stock_trading_enabled,
                building_autobuy_enabled=build_options.building_autobuy_enabled,
                combo_pending=late_stage_prep.combo_pending,
                combo_phase=diagnostics.combo_stats.get("pending_phase"),
                now=cycle_state.now,
                action_started=action_started,
                upgrade_action=late_stage_prep.upgrade_action,
                upgrade_store_action=late_stage_prep.upgrade_store_action,
                upgrade_signature=late_stage_prep.upgrade_signature,
                upgrade_blocked_until=late_stage_prep.upgrade_blocked_until,
                upgrade_signature_blocked=late_stage_prep.upgrade_signature_blocked,
                cookies_after_upgrade_reserve=late_stage_prep.cookies_after_upgrade_reserve,
                defer_stock_for_upgrade_live=late_stage_prep.defer_stock_for_upgrade_live,
                last_upgrade_action=state.last_upgrade_action,
                last_upgrade_skip_signature=state.last_upgrade_skip_signature,
                last_upgrade_focus_signature=state.last_upgrade_focus_signature,
                last_upgrade_focus_at=state.last_upgrade_focus_at,
                last_upgrade_focus_point=state.last_upgrade_focus_point,
                last_wrinkler_action=state.last_wrinkler_action,
                post_upgrade_wrinkler_cooldown_until=state.post_upgrade_wrinkler_cooldown_until,
                last_dragon_action=state.last_dragon_action,
                last_building_action=state.last_building_action,
                last_trade_action=state.last_trade_action,
                upgrade_attempt_tracker=upgrade_attempt_tracker,
                building_attempt_tracker=building_attempt_tracker,
            )
        )
        late_state = self._outcome_handler.apply_late_outcome(
            late_outcome,
            DomLoopLateStageState(
                last_upgrade_action=state.last_upgrade_action,
                last_upgrade_skip_signature=state.last_upgrade_skip_signature,
                post_upgrade_wrinkler_cooldown_until=state.post_upgrade_wrinkler_cooldown_until,
                last_upgrade_focus_signature=state.last_upgrade_focus_signature,
                last_upgrade_focus_at=state.last_upgrade_focus_at,
                last_upgrade_focus_point=state.last_upgrade_focus_point,
                last_wrinkler_action=state.last_wrinkler_action,
                last_dragon_action=state.last_dragon_action,
                last_trade_action=state.last_trade_action,
                last_building_action=state.last_building_action,
            ),
        )
        state = replace(
            state,
            last_upgrade_skip_signature=late_state.last_upgrade_skip_signature,
        )
        if late_outcome.handled:
            return replace(
                state,
                last_upgrade_action=late_state.last_upgrade_action,
                post_upgrade_wrinkler_cooldown_until=late_state.post_upgrade_wrinkler_cooldown_until,
                last_upgrade_focus_signature=late_state.last_upgrade_focus_signature,
                last_upgrade_focus_at=late_state.last_upgrade_focus_at,
                last_upgrade_focus_point=late_state.last_upgrade_focus_point,
                last_wrinkler_action=late_state.last_wrinkler_action,
                last_dragon_action=late_state.last_dragon_action,
                last_trade_action=late_state.last_trade_action,
                last_building_action=late_state.last_building_action,
            )

        self._outcome_handler.handle_idle_fallthrough(action_started)
        return state


class DomLoopStateBridge:
    """Bridges legacy loop globals to and from structured DomLoopState."""

    @staticmethod
    def create_state(
        *,
        suppress_main_click_until: float,
        last_spell_click: float,
        last_trade_action: float,
        last_building_action: float,
        last_upgrade_action: float,
        last_combo_action_click: float,
        last_wrinkler_action: float,
        last_dragon_action: float,
        last_note_dismiss_action: float,
        last_lump_action: float,
        last_upgrade_skip_signature: Any,
        post_upgrade_wrinkler_cooldown_until: float,
        last_upgrade_focus_signature: Any,
        last_upgrade_focus_at: float,
        last_upgrade_focus_point: Any,
        last_seen_golden_decision: Any,
    ) -> DomLoopState:
        return DomLoopState(
            suppress_main_click_until=suppress_main_click_until,
            last_spell_click=last_spell_click,
            last_trade_action=last_trade_action,
            last_building_action=last_building_action,
            last_upgrade_action=last_upgrade_action,
            last_combo_action_click=last_combo_action_click,
            last_wrinkler_action=last_wrinkler_action,
            last_dragon_action=last_dragon_action,
            last_note_dismiss_action=last_note_dismiss_action,
            last_lump_action=last_lump_action,
            last_upgrade_skip_signature=last_upgrade_skip_signature,
            post_upgrade_wrinkler_cooldown_until=post_upgrade_wrinkler_cooldown_until,
            last_upgrade_focus_signature=last_upgrade_focus_signature,
            last_upgrade_focus_at=last_upgrade_focus_at,
            last_upgrade_focus_point=last_upgrade_focus_point,
            last_seen_golden_decision=last_seen_golden_decision,
            last_feed_signature=None,
            last_feed_debug_at=0.0,
            bank_diag_cache=BankDiagCache(),
        )

    @staticmethod
    def sync_before_cycle(
        state: DomLoopState,
        *,
        suppress_main_click_until: float,
    ) -> DomLoopState:
        return replace(
            state,
            suppress_main_click_until=max(
                float(suppress_main_click_until or 0.0),
                float(state.suppress_main_click_until or 0.0),
            ),
        )

    @staticmethod
    def export_state(
        state: DomLoopState,
        *,
        suppress_main_click_until: float,
    ) -> dict[str, Any]:
        return {
            "suppress_main_click_until": max(
                float(suppress_main_click_until or 0.0),
                float(state.suppress_main_click_until or 0.0),
            ),
            "last_seen_golden_decision": state.last_seen_golden_decision,
            "last_spell_click": state.last_spell_click,
            "last_trade_action": state.last_trade_action,
            "last_building_action": state.last_building_action,
            "last_upgrade_action": state.last_upgrade_action,
            "last_combo_action_click": state.last_combo_action_click,
            "last_wrinkler_action": state.last_wrinkler_action,
            "last_dragon_action": state.last_dragon_action,
            "last_note_dismiss_action": state.last_note_dismiss_action,
            "last_lump_action": state.last_lump_action,
            "last_upgrade_skip_signature": state.last_upgrade_skip_signature,
            "post_upgrade_wrinkler_cooldown_until": state.post_upgrade_wrinkler_cooldown_until,
            "last_upgrade_focus_signature": state.last_upgrade_focus_signature,
            "last_upgrade_focus_at": state.last_upgrade_focus_at,
            "last_upgrade_focus_point": state.last_upgrade_focus_point,
        }


class DomLoopStageRunner:
    """Builds and runs the remaining dom_loop stage closures outside clicker.py."""

    def __init__(
        self,
        *,
        coordinator: DomActionCoordinator,
        action_executor: Any,
        action_planner: DomActionPlanner,
        attempt_tracker: DomAttemptTracker,
        stage_policy: DomStagePolicy,
        note_target_getter: Callable[[dict[str, Any] | None, Callable[[int, int], tuple[int, int]]], Any],
        should_allow_garden_action: Callable[[dict[str, Any] | None, dict[str, Any]], bool],
        update_building_attempt_tracking: Callable[[dict[str, Any] | None, Any, float], None],
        to_screen_point: Callable[[int, int], tuple[int, int]],
        build_building_attempt_signature: Callable[[dict[str, Any] | None, Any], Any],
        extract_building_target_debug: Callable[[dict[str, Any] | None, Any], Any],
        format_store_planner_context: Callable[[Any], str],
        extract_upgrade_target_debug: Callable[[dict[str, Any] | None, Any], Any],
        format_upgrade_planner_context: Callable[[Any], str],
        combo_controller: Any,
        spell_controller: Any,
        garden_controller: Any,
        wrinkler_controller: Any,
        ascension_controller: Any,
        santa_controller: Any,
        stock_trader: Any,
        building_autobuyer: Any,
        log: Any,
        sleep: SleepFn,
        lump_action_cooldown: float,
        note_dismiss_cooldown: float,
        combo_action_cooldown: float,
        spell_click_cooldown: float,
        wrinkler_action_cooldown: float,
        trade_action_cooldown: float,
        building_action_cooldown: float,
        upgrade_action_cooldown: float,
        dragon_action_cooldown: float,
        dragon_aura_action_cooldown: float,
        post_upgrade_wrinkler_cooldown_seconds: float,
        bonus_click_hold: float,
        trade_click_hold: float,
        building_stuck_attempt_limit: int,
        building_stuck_signature_suppress_seconds: float,
        upgrade_stuck_attempt_limit: int,
        upgrade_stuck_signature_suppress_seconds: float,
        store_scroll_wheel_multiplier: int,
        feed_poll_interval: float,
    ):
        self._coordinator = coordinator
        self._action_executor = action_executor
        self._action_planner = action_planner
        self._attempt_tracker = attempt_tracker
        self._stage_policy = stage_policy
        self._note_target_getter = note_target_getter
        self._should_allow_garden_action = should_allow_garden_action
        self._update_building_attempt_tracking = update_building_attempt_tracking
        self._to_screen_point = to_screen_point
        self._build_building_attempt_signature = build_building_attempt_signature
        self._extract_building_target_debug = extract_building_target_debug
        self._format_store_planner_context = format_store_planner_context
        self._extract_upgrade_target_debug = extract_upgrade_target_debug
        self._format_upgrade_planner_context = format_upgrade_planner_context
        self._combo_controller = combo_controller
        self._spell_controller = spell_controller
        self._garden_controller = garden_controller
        self._wrinkler_controller = wrinkler_controller
        self._ascension_controller = ascension_controller
        self._santa_controller = santa_controller
        self._stock_trader = stock_trader
        self._building_autobuyer = building_autobuyer
        self._log = log
        self._sleep = sleep
        self._lump_action_cooldown = lump_action_cooldown
        self._note_dismiss_cooldown = note_dismiss_cooldown
        self._combo_action_cooldown = combo_action_cooldown
        self._spell_click_cooldown = spell_click_cooldown
        self._wrinkler_action_cooldown = wrinkler_action_cooldown
        self._trade_action_cooldown = trade_action_cooldown
        self._building_action_cooldown = building_action_cooldown
        self._upgrade_action_cooldown = upgrade_action_cooldown
        self._dragon_action_cooldown = dragon_action_cooldown
        self._dragon_aura_action_cooldown = dragon_aura_action_cooldown
        self._post_upgrade_wrinkler_cooldown_seconds = post_upgrade_wrinkler_cooldown_seconds
        self._bonus_click_hold = bonus_click_hold
        self._trade_click_hold = trade_click_hold
        self._building_stuck_attempt_limit = building_stuck_attempt_limit
        self._building_stuck_signature_suppress_seconds = building_stuck_signature_suppress_seconds
        self._upgrade_stuck_attempt_limit = upgrade_stuck_attempt_limit
        self._upgrade_stuck_signature_suppress_seconds = upgrade_stuck_signature_suppress_seconds
        self._store_scroll_wheel_multiplier = store_scroll_wheel_multiplier
        self._feed_poll_interval = feed_poll_interval

    def run_early(self, context: DomLoopEarlyStageContext) -> DomLoopActionOutcome:
        def _lump_stage():
            lump_action_ready = (
                not context.shimmers
                and context.lump_diag.get("can_click")
                and (context.now - context.last_lump_action) >= self._lump_action_cooldown
            )
            if not lump_action_ready:
                return DomLoopActionOutcome()
            handled_at = self._action_executor.execute_lump_action(context.lump_diag, context.now)
            if handled_at is None:
                return DomLoopActionOutcome()
            return DomLoopActionOutcome(handled=True, updates={"last_lump_action": handled_at})

        def _note_stage():
            if context.shimmers or (context.now - context.last_note_dismiss_action) < self._note_dismiss_cooldown:
                return DomLoopActionOutcome()
            note_action = self._note_target_getter(context.snapshot, self._to_screen_point)
            if note_action is None:
                return DomLoopActionOutcome()
            handled_at = self._action_executor.execute_note_action(note_action, context.now)
            if handled_at is None:
                return DomLoopActionOutcome()
            return DomLoopActionOutcome(handled=True, updates={"last_note_dismiss_action": handled_at})

        def _pending_combo_stage():
            if (
                context.pause_value_actions_during_clot
                or not self._combo_controller.has_pending()
                or (context.now - context.last_combo_action_click) < self._combo_action_cooldown
            ):
                return DomLoopActionOutcome()
            combo_action = self._combo_controller.get_action(context.snapshot, self._to_screen_point, now=context.now)
            if combo_action is None:
                return DomLoopActionOutcome()
            handled_at = self._action_executor.execute_combo_action(
                combo_action,
                context.now,
                context.action_started,
                self._combo_controller,
            )
            if handled_at is None:
                return DomLoopActionOutcome()
            return DomLoopActionOutcome(handled=True, updates={"last_combo_action_click": handled_at})

        def _spell_stage():
            if (
                not context.auto_cast_hand_of_fate
                or context.pause_value_actions_during_clot
                or self._combo_controller.owns_spellcasting(context.snapshot, self._to_screen_point)
                or self._combo_controller.has_pending()
                or context.shimmers
                or (context.now - context.last_spell_click) < self._spell_click_cooldown
            ):
                return DomLoopActionOutcome()
            spell_action = self._spell_controller.get_action(
                context.snapshot,
                self._to_screen_point,
                now=context.now,
                building_diag=context.building_diag,
            )
            if spell_action is None:
                return DomLoopActionOutcome()
            handled_at = self._action_executor.execute_spell_action(
                spell_action,
                context.now,
                context.action_started,
                self._spell_controller,
            )
            if handled_at is None:
                return DomLoopActionOutcome()
            return DomLoopActionOutcome(handled=True, updates={"last_spell_click": handled_at})

        def _opportunistic_combo_stage():
            if (
                context.pause_value_actions_during_clot
                or self._combo_controller.has_pending()
                or (context.now - context.last_combo_action_click) < self._combo_action_cooldown
            ):
                return DomLoopActionOutcome()
            combo_action = self._combo_controller.get_action(context.snapshot, self._to_screen_point, now=context.now)
            if combo_action is None:
                return DomLoopActionOutcome()
            handled_at = self._action_executor.execute_combo_action(
                combo_action,
                context.now,
                context.action_started,
                self._combo_controller,
            )
            if handled_at is None:
                return DomLoopActionOutcome()
            return DomLoopActionOutcome(handled=True, updates={"last_combo_action_click": handled_at})

        def _garden_stage():
            if (
                not context.garden_automation_enabled
                or (context.pause_non_click_actions and not context.allow_non_click_actions_during_pause)
                or not self._should_allow_garden_action(context.snapshot, context.garden_diag)
                or self._combo_controller.has_pending()
                or context.shimmers
            ):
                return DomLoopActionOutcome()
            garden_action = self._garden_controller.get_action(context.snapshot, self._to_screen_point, now=context.now)
            if garden_action is None:
                return DomLoopActionOutcome()
            handled = self._action_executor.execute_garden_action(
                garden_action,
                context.now,
                context.action_started,
                self._garden_controller,
            )
            return DomLoopActionOutcome(handled=handled)

        return self._coordinator.run(
            (
                _lump_stage,
                _note_stage,
                _pending_combo_stage,
                _spell_stage,
                _opportunistic_combo_stage,
                _garden_stage,
            )
        )

    def run_late(self, context: DomLoopLateStageContext) -> DomLoopActionOutcome:
        last_upgrade_skip_signature = context.last_upgrade_skip_signature

        def _upgrade_stage():
            nonlocal last_upgrade_skip_signature
            if context.upgrade_action is not None or context.upgrade_store_action is not None:
                result = self._action_executor.execute_upgrade_action(
                    now=context.now,
                    action_started=context.action_started,
                    snapshot=context.snapshot,
                    upgrade_diag=context.upgrade_diag,
                    upgrade_action=context.upgrade_action,
                    upgrade_store_action=context.upgrade_store_action,
                    upgrade_signature=context.upgrade_signature,
                    last_upgrade_focus_signature=context.last_upgrade_focus_signature,
                    last_upgrade_focus_at=context.last_upgrade_focus_at,
                    last_upgrade_focus_point=context.last_upgrade_focus_point,
                    upgrade_attempt_tracker=context.upgrade_attempt_tracker,
                    upgrade_stuck_attempt_limit=self._upgrade_stuck_attempt_limit,
                    upgrade_stuck_signature_suppress_seconds=self._upgrade_stuck_signature_suppress_seconds,
                    post_upgrade_wrinkler_cooldown_seconds=self._post_upgrade_wrinkler_cooldown_seconds,
                    extract_upgrade_target_debug=self._extract_upgrade_target_debug,
                    format_upgrade_planner_context=self._format_upgrade_planner_context,
                )
                if result is None:
                    return DomLoopActionOutcome()
                return DomLoopActionOutcome(
                    handled=True,
                    updates={
                        "last_upgrade_action": result["action_at"],
                        "last_upgrade_skip_signature": result["last_upgrade_skip_signature"],
                        "post_upgrade_wrinkler_cooldown_until": result["post_upgrade_wrinkler_cooldown_until"],
                        "last_upgrade_focus_signature": result["last_upgrade_focus_signature"],
                        "last_upgrade_focus_at": result["last_upgrade_focus_at"],
                        "last_upgrade_focus_point": result["last_upgrade_focus_point"],
                    },
                )

            if bool(context.upgrade_diag.get("candidate_can_buy")) and context.upgrade_diag.get("candidate_id") is not None:
                blockers = self._stage_policy.build_upgrade_blockers(
                    upgrade_autobuy_enabled=context.upgrade_autobuy_enabled,
                    pause_non_click_actions=context.pause_non_click_actions,
                    pause_reasons=context.pause_reasons,
                    allow_upgrade_during_pause=(
                        bool(context.upgrade_diag.get("allow_during_pause"))
                        or context.allow_non_click_actions_during_pause
                    ),
                    upgrade_diag=context.upgrade_diag,
                    combo_pending=context.combo_pending,
                    combo_phase=context.combo_phase,
                    shimmers_present=bool(context.shimmers),
                    shimmer_count=len(context.shimmers),
                    now=context.now,
                    upgrade_blocked_until=context.upgrade_blocked_until,
                    upgrade_signature_blocked=context.upgrade_signature_blocked,
                    cookies_after_reserve=context.cookies_after_upgrade_reserve,
                    global_cookie_reserve=context.global_cookie_reserve,
                    garden_cookie_reserve=context.garden_cookie_reserve,
                    lucky_cookie_reserve=context.lucky_cookie_reserve,
                    last_upgrade_action=context.last_upgrade_action,
                    upgrade_action_cooldown=self._upgrade_action_cooldown,
                )
                last_upgrade_skip_signature = self._attempt_tracker.log_upgrade_blockers(
                    log=self._log,
                    last_signature=last_upgrade_skip_signature,
                    snapshot=context.snapshot,
                    upgrade_diag=context.upgrade_diag,
                    blockers=blockers,
                )
            return DomLoopActionOutcome()

        def _wrinkler_stage():
            wrinkler_action = None
            if self._stage_policy.can_plan_wrinkler(
                combo_pending=context.combo_pending,
                shimmers_present=bool(context.shimmers),
                now=context.now,
                last_wrinkler_action=context.last_wrinkler_action,
                wrinkler_action_cooldown=self._wrinkler_action_cooldown,
                post_upgrade_wrinkler_cooldown_until=context.post_upgrade_wrinkler_cooldown_until,
                purchase_goal=context.purchase_goal,
            ):
                wrinkler_action = self._action_planner.plan_wrinkler(
                    snapshot=context.snapshot,
                    to_screen_point=self._to_screen_point,
                    now=context.now,
                    purchase_goal=context.purchase_goal,
                )
            if wrinkler_action is None:
                return DomLoopActionOutcome()
            handled_at = self._action_executor.execute_wrinkler_action(
                wrinkler_action,
                context.now,
                context.action_started,
                self._wrinkler_controller,
                self._bonus_click_hold,
            )
            if handled_at is None:
                return DomLoopActionOutcome()
            return DomLoopActionOutcome(handled=True, updates={"last_wrinkler_action": handled_at})

        def _dragon_stage():
            dragon_action = None
            if self._stage_policy.can_plan_dragon(
                dragon_diag=context.dragon_diag,
                pause_non_click_actions=context.pause_non_click_actions,
                allow_non_click_actions_during_pause=context.allow_non_click_actions_during_pause,
                combo_pending=context.combo_pending,
                shimmers_present=bool(context.shimmers),
                now=context.now,
                last_dragon_action=context.last_dragon_action,
                dragon_action_cooldown=self._dragon_action_cooldown,
            ):
                dragon_action = self._action_planner.plan_dragon(
                    dragon_diag=context.dragon_diag,
                    combo_diag=context.combo_diag,
                    spell_diag=context.spell_diag,
                    allow_aura_actions=self._stage_policy.allow_dragon_aura_actions(
                        now=context.now,
                        last_dragon_action=context.last_dragon_action,
                        dragon_aura_action_cooldown=self._dragon_aura_action_cooldown,
                    ),
                )
            if dragon_action is None:
                return DomLoopActionOutcome()
            handled_at = self._action_executor.execute_dragon_action(
                dragon_action,
                context.dragon_diag,
                context.now,
                context.action_started,
            )
            if handled_at is None:
                return DomLoopActionOutcome()
            return DomLoopActionOutcome(handled=True, updates={"last_dragon_action": handled_at})

        def _santa_stage():
            if not self._stage_policy.can_plan_santa(
                pause_non_click_actions=context.pause_non_click_actions,
                allow_non_click_actions_during_pause=context.allow_non_click_actions_during_pause,
                combo_pending=context.combo_pending,
                shimmers_present=bool(context.shimmers),
            ):
                return DomLoopActionOutcome()
            santa_action = self._santa_controller.get_action(
                context.snapshot,
                self._to_screen_point,
                now=context.now,
            )
            if santa_action is None:
                return DomLoopActionOutcome()
            handled_at = self._action_executor.execute_santa_action(
                santa_action,
                context.now,
                context.action_started,
                self._santa_controller,
            )
            if handled_at is None:
                return DomLoopActionOutcome()
            return DomLoopActionOutcome(handled=True)

        def _ascension_stage():
            ascension_prep_action = None
            ascension_prep_store_action = None
            if self._stage_policy.can_plan_ascension(
                ascension_prep_enabled=context.ascension_prep_enabled,
                pause_non_click_actions=context.pause_non_click_actions,
                allow_non_click_actions_during_pause=context.allow_non_click_actions_during_pause,
                combo_pending=context.combo_pending,
                shimmers_present=bool(context.shimmers),
                now=context.now,
                last_building_action=context.last_building_action,
                building_action_cooldown=self._building_action_cooldown,
            ):
                ascension_plan = self._action_planner.plan_ascension_prep(
                    snapshot=context.snapshot,
                    to_screen_point=self._to_screen_point,
                    now=context.now,
                )
                ascension_prep_action = ascension_plan.action
                ascension_prep_store_action = ascension_plan.store_action
            if ascension_prep_action is None or ascension_prep_store_action is None:
                return DomLoopActionOutcome()
            handled_at = self._action_executor.execute_ascension_prep_action(
                ascension_prep_action,
                ascension_prep_store_action,
                context.now,
                context.action_started,
                self._ascension_controller,
            )
            if handled_at is None:
                return DomLoopActionOutcome()
            return DomLoopActionOutcome(handled=True, updates={"last_building_action": handled_at})

        def _trade_stage():
            trade_action = None
            if self._stage_policy.can_plan_trade(
                ascension_prep_enabled=context.ascension_prep_enabled,
                stock_management_active=context.stock_management_active,
                pause_non_click_actions=context.pause_non_click_actions,
                allow_non_click_actions_during_pause=context.allow_non_click_actions_during_pause,
                pause_stock_trading=context.pause_stock_trading,
                defer_stock_for_upgrade_live=context.defer_stock_for_upgrade_live,
                shimmers_present=bool(context.shimmers),
                now=context.now,
                last_trade_action=context.last_trade_action,
                trade_action_cooldown=self._trade_action_cooldown,
            ):
                trade_action = self._action_planner.plan_trade(
                    snapshot=context.snapshot,
                    to_screen_point=self._to_screen_point,
                    now=context.now,
                    stock_trading_enabled=context.stock_trading_enabled,
                    stock_buy_controls=context.stock_buy_controls,
                )
            if trade_action is None:
                return DomLoopActionOutcome()
            handled_at = self._action_executor.execute_trade_action(
                trade_action,
                context.now,
                context.action_started,
                self._stock_trader,
                self._trade_click_hold,
            )
            if handled_at is None:
                return DomLoopActionOutcome()
            return DomLoopActionOutcome(handled=True, updates={"last_trade_action": handled_at})

        def _building_stage():
            building_plan = None
            if self._stage_policy.can_plan_building(
                ascension_prep_enabled=context.ascension_prep_enabled,
                building_autobuy_enabled=context.building_autobuy_enabled,
                pause_non_click_actions=context.pause_non_click_actions,
                allow_non_click_actions_during_pause=context.allow_non_click_actions_during_pause,
                shimmers_present=bool(context.shimmers),
                now=context.now,
                last_building_action=context.last_building_action,
                building_action_cooldown=self._building_action_cooldown,
            ):
                building_blocked_until = float(context.building_attempt_tracker.get("blocked_until") or 0.0)
                building_blocked_signature = context.building_attempt_tracker.get("blocked_signature")
                building_plan = self._action_planner.plan_building(
                    snapshot=context.snapshot,
                    to_screen_point=self._to_screen_point,
                    now=context.now,
                    building_diag=context.building_diag,
                    building_cookie_reserve=context.building_cookie_reserve,
                    build_signature=lambda action: self._build_building_attempt_signature(context.snapshot, action),
                    blocked_signature=building_blocked_signature,
                    blocked_until=building_blocked_until,
                )
                building_action = building_plan.building_action
            else:
                building_action = None
            self._update_building_attempt_tracking(context.snapshot, building_action, context.now)
            if building_plan is None:
                return DomLoopActionOutcome()
            if building_plan.building_action is None and building_plan.store_action is None:
                return DomLoopActionOutcome()
            store_action = building_plan.store_action
            if store_action is None:
                return DomLoopActionOutcome()
            if building_plan.signature_blocked:
                self._sleep(self._feed_poll_interval)
                return DomLoopActionOutcome(handled=True)
            handled_at = self._action_executor.execute_building_action(
                building_action=building_action,
                store_action=store_action,
                snapshot=context.snapshot,
                now=context.now,
                action_started=context.action_started,
                building_signature=building_plan.signature,
                building_attempt_tracker=context.building_attempt_tracker,
                building_stuck_attempt_limit=self._building_stuck_attempt_limit,
                building_stuck_signature_suppress_seconds=self._building_stuck_signature_suppress_seconds,
                building_recorder=self._building_autobuyer,
                extract_building_target_debug=self._extract_building_target_debug,
                format_store_planner_context=self._format_store_planner_context,
                store_scroll_wheel_multiplier=self._store_scroll_wheel_multiplier,
            )
            if handled_at is None:
                return DomLoopActionOutcome()
            return DomLoopActionOutcome(handled=True, updates={"last_building_action": handled_at})

        def _minigame_stage():
            minigame_plan = self._action_planner.plan_minigame_store_access(
                snapshot=context.snapshot,
                spell_diag=context.spell_diag,
                bank_diag=context.bank_diag,
                garden_diag=context.garden_diag,
            )
            if minigame_plan.store_action is None:
                return DomLoopActionOutcome()
            handled = self._action_executor.execute_minigame_store_action(
                minigame_plan.owner,
                minigame_plan.store_action,
                context.now,
                context.action_started,
            )
            return DomLoopActionOutcome(handled=handled)

        outcome = self._coordinator.run(
            (
                _upgrade_stage,
                _wrinkler_stage,
                _dragon_stage,
                _santa_stage,
                _ascension_stage,
                _trade_stage,
                _building_stage,
                _minigame_stage,
            )
        )
        updates = dict(outcome.updates or {})
        updates["last_upgrade_skip_signature"] = updates.get(
            "last_upgrade_skip_signature",
            last_upgrade_skip_signature,
        )
        return DomLoopActionOutcome(handled=outcome.handled, updates=updates)


class DomSnapshotPreparer:
    """Loads the latest feed snapshot and derived top-level objects."""

    def __init__(
        self,
        *,
        load_feed_snapshot: Callable[[], dict[str, Any] | None],
        update_latest_snapshot: Callable[[dict[str, Any] | None], None],
        extract_shimmers: Callable[[dict[str, Any] | None], list[dict[str, Any]]],
        extract_buffs: Callable[[dict[str, Any] | None], list[dict[str, Any]]],
        extract_spell: Callable[[dict[str, Any] | None], dict[str, Any] | None],
        get_latest_big_cookie: Callable[[], dict[str, Any] | None],
    ):
        self._load_feed_snapshot = load_feed_snapshot
        self._update_latest_snapshot = update_latest_snapshot
        self._extract_shimmers = extract_shimmers
        self._extract_buffs = extract_buffs
        self._extract_spell = extract_spell
        self._get_latest_big_cookie = get_latest_big_cookie

    def prepare(
        self,
        *,
        building_autobuy_enabled: bool,
        lucky_reserve_enabled: bool,
    ) -> PreparedSnapshot:
        snapshot = self._load_feed_snapshot()
        if isinstance(snapshot, dict):
            snapshot["_building_autobuy_enabled"] = building_autobuy_enabled
            snapshot["_lucky_reserve_enabled"] = lucky_reserve_enabled
        self._update_latest_snapshot(snapshot)
        return PreparedSnapshot(
            snapshot=snapshot,
            shimmers=self._extract_shimmers(snapshot),
            buffs=self._extract_buffs(snapshot),
            spell=self._extract_spell(snapshot),
            big_cookie=self._get_latest_big_cookie(),
        )


class DomLoopFeedLogger:
    """Logs feed/debug state only when the loop signature changes."""

    def __init__(
        self,
        *,
        log: Any,
        monotonic: Callable[[], float],
        feed_debug_log_interval: float,
    ):
        self._log = log
        self._monotonic = monotonic
        self._feed_debug_log_interval = feed_debug_log_interval

    def log_if_changed(
        self,
        *,
        prepared: PreparedSnapshot,
        diagnostics: "DomLoopDiagnostics",
        last_feed_signature: Any,
        last_feed_debug_at: float,
    ) -> tuple[Any, float]:
        signature = DomDiagnosticsBuilder.build_feed_signature(prepared, diagnostics)
        now = self._monotonic()
        if signature == last_feed_signature or (now - last_feed_debug_at) < self._feed_debug_log_interval:
            return last_feed_signature, last_feed_debug_at
        snapshot = prepared.snapshot
        age = snapshot["_age"] if snapshot else None
        age_text = "none" if age is None else f"{age:.3f}"
        big_cookie = prepared.big_cookie
        spell = prepared.spell
        self._log.debug(
            f"dom_feed: age={age_text} shimmers={len(prepared.shimmers)} "
            f"big_cookie={None if big_cookie is None else (big_cookie['client_x'], big_cookie['client_y'])} "
            f"spell={None if spell is None else {'ready': spell['ready'], 'on_minigame': spell['on_minigame'], 'client': (spell['client_x'], spell['client_y'])}}"
        )
        self._log.debug(f"spell_feed: {diagnostics.spell_diag}")
        self._log.debug(f"bank_feed: {diagnostics.bank_diag}")
        self._log.debug(f"garden_feed: {diagnostics.garden_diag}")
        self._log.debug(f"upgrade_feed: {diagnostics.upgrade_diag}")
        self._log.debug(f"dragon_feed: {diagnostics.dragon_diag}")
        self._log.debug(f"wrinkler_feed: {diagnostics.wrinkler_diag}")
        self._log.debug(f"building_feed: {diagnostics.building_diag}")
        self._log.debug(f"combo_feed: {diagnostics.combo_diag}")
        return signature, now


class DomDiagnosticsBuilder:
    """Builds the structured diagnostics consumed by dom_loop action stages."""

    def __init__(
        self,
        *,
        to_screen_point: Callable[[int, int], tuple[int, int]],
        monotonic: Callable[[], float],
        garden_get_diagnostics: Callable[[dict[str, Any] | None, Callable[[int, int], tuple[int, int]]], dict[str, Any]],
        extract_lump_diag: Callable[[dict[str, Any] | None, Callable[[int, int], tuple[int, int]]], dict[str, Any]],
        building_get_diagnostics: Callable[[dict[str, Any] | None, Callable[[int, int], tuple[int, int]]], dict[str, Any]],
        ascension_get_diagnostics: Callable[[dict[str, Any] | None], dict[str, Any]],
        extract_upgrade_diag: Callable[[dict[str, Any] | None], dict[str, Any]],
        extract_dragon_diag: Callable[[dict[str, Any] | None, Callable[[int, int], tuple[int, int]]], dict[str, Any]],
        extract_golden_cookie_diag: Callable[[dict[str, Any] | None], dict[str, Any]],
        spell_get_diagnostics: Callable[..., dict[str, Any]],
        get_global_cookie_reserve: Callable[..., dict[str, Any]],
        get_next_purchase_goal: Callable[..., dict[str, Any] | None],
        apply_building_burst_purchase_goal: Callable[..., dict[str, Any] | None],
        get_stock_buy_controls: Callable[..., dict[str, Any]],
        stock_trade_management_active: Callable[[], bool],
        stock_get_diagnostics: Callable[..., dict[str, Any]],
        extract_bank_diag_disabled: Callable[[dict[str, Any] | None], dict[str, Any]],
        wrinkler_get_diagnostics: Callable[..., dict[str, Any]],
        combo_get_diagnostics: Callable[..., dict[str, Any]],
        stock_get_runtime_stats: Callable[[], dict[str, Any]],
        spell_get_runtime_stats: Callable[[], dict[str, Any]],
        combo_get_runtime_stats: Callable[[], dict[str, Any]],
        track_combo_run: Callable[..., None],
        get_non_click_pause_reasons: Callable[..., tuple[str, ...] | list[str]],
        should_pause_stock_trading: Callable[[list[dict[str, Any]]], bool],
        should_allow_non_click_actions_during_pause: Callable[..., bool],
        evaluate_upgrade_buff_window: Callable[..., dict[str, Any]],
        should_defer_stock_actions_for_upgrade: Callable[..., bool],
        set_runtime: Callable[..., None],
    ):
        self._to_screen_point = to_screen_point
        self._monotonic = monotonic
        self._garden_get_diagnostics = garden_get_diagnostics
        self._extract_lump_diag = extract_lump_diag
        self._building_get_diagnostics = building_get_diagnostics
        self._ascension_get_diagnostics = ascension_get_diagnostics
        self._extract_upgrade_diag = extract_upgrade_diag
        self._extract_dragon_diag = extract_dragon_diag
        self._extract_golden_cookie_diag = extract_golden_cookie_diag
        self._spell_get_diagnostics = spell_get_diagnostics
        self._get_global_cookie_reserve = get_global_cookie_reserve
        self._get_next_purchase_goal = get_next_purchase_goal
        self._apply_building_burst_purchase_goal = apply_building_burst_purchase_goal
        self._get_stock_buy_controls = get_stock_buy_controls
        self._stock_trade_management_active = stock_trade_management_active
        self._stock_get_diagnostics = stock_get_diagnostics
        self._extract_bank_diag_disabled = extract_bank_diag_disabled
        self._wrinkler_get_diagnostics = wrinkler_get_diagnostics
        self._combo_get_diagnostics = combo_get_diagnostics
        self._stock_get_runtime_stats = stock_get_runtime_stats
        self._spell_get_runtime_stats = spell_get_runtime_stats
        self._combo_get_runtime_stats = combo_get_runtime_stats
        self._track_combo_run = track_combo_run
        self._get_non_click_pause_reasons = get_non_click_pause_reasons
        self._should_pause_stock_trading = should_pause_stock_trading
        self._should_allow_non_click_actions_during_pause = should_allow_non_click_actions_during_pause
        self._evaluate_upgrade_buff_window = evaluate_upgrade_buff_window
        self._should_defer_stock_actions_for_upgrade = should_defer_stock_actions_for_upgrade
        self._set_runtime = set_runtime

    def build(
        self,
        prepared: PreparedSnapshot,
        bank_diag_cache: BankDiagCache,
        options: DomLoopBuildOptions,
    ) -> tuple[DomLoopDiagnostics, BankDiagCache]:
        snapshot = prepared.snapshot
        buffs = prepared.buffs

        garden_diag = self._garden_get_diagnostics(snapshot, self._to_screen_point)
        lump_diag = self._extract_lump_diag(snapshot, self._to_screen_point)
        building_diag = self._building_get_diagnostics(snapshot, self._to_screen_point)
        ascension_prep_diag = self._ascension_get_diagnostics(snapshot)
        upgrade_diag = self._extract_upgrade_diag(snapshot)
        dragon_diag = self._extract_dragon_diag(snapshot, self._to_screen_point)
        golden_diag = self._extract_golden_cookie_diag(snapshot)
        spell_diag = self._spell_get_diagnostics(
            snapshot,
            self._to_screen_point,
            building_diag=building_diag,
        )

        reserve_budget = self._get_global_cookie_reserve(
            snapshot,
            garden_diag,
            building_diag=building_diag,
            spell_diag=spell_diag,
        )
        purchase_goal = self._get_next_purchase_goal(
            snapshot,
            building_diag=building_diag,
            upgrade_diag=upgrade_diag,
        )
        purchase_goal = self._apply_building_burst_purchase_goal(
            snapshot,
            building_diag,
            purchase_goal,
            reserve_budget["burst_window"],
        )
        stock_buy_controls = self._get_stock_buy_controls(
            building_diag,
            options.building_autobuy_enabled,
            reserve_budget["total_reserve"],
        )
        stock_management_active = self._stock_trade_management_active()

        refreshed_cache = bank_diag_cache
        if stock_management_active:
            now = self._monotonic()
            if (
                bank_diag_cache.diag is None
                or (now - bank_diag_cache.captured_at) >= options.stock_diag_refresh_interval
            ):
                refreshed_cache = BankDiagCache(
                    diag=self._stock_get_diagnostics(
                        snapshot,
                        self._to_screen_point,
                        allow_buy_actions=(
                            options.stock_trading_enabled and stock_buy_controls["allow_buy_actions"]
                        ),
                        allow_sell_actions=True,
                        buy_reserve_cookies=stock_buy_controls["buy_reserve_cookies"],
                    ),
                    captured_at=now,
                )
            bank_diag = dict(refreshed_cache.diag or {})
            bank_diag["buy_actions_enabled"] = bool(
                options.stock_trading_enabled and stock_buy_controls["allow_buy_actions"]
            )
            bank_diag["sell_actions_enabled"] = True
            bank_diag["buy_reserve_cookies"] = stock_buy_controls["buy_reserve_cookies"]
            bank_diag["buy_cookies_available"] = max(
                0.0,
                float(bank_diag.get("cookies") or 0.0) - float(stock_buy_controls["buy_reserve_cookies"]),
            )
            if not bank_diag["buy_actions_enabled"] and bank_diag.get("reason") == "buy_ready":
                bank_diag["reason"] = "buy_blocked"
        else:
            bank_diag = self._extract_bank_diag_disabled(snapshot)

        wrinkler_diag = self._wrinkler_get_diagnostics(
            snapshot,
            self._to_screen_point,
            pop_goal=purchase_goal,
        )
        santa_controller = getattr(self, "_santa_controller", None)
        santa_diag = (
            santa_controller.get_diagnostics(snapshot, self._to_screen_point)
            if santa_controller is not None
            else {}
        )
        combo_diag = self._combo_get_diagnostics(snapshot, self._to_screen_point)
        trade_stats = self._stock_get_runtime_stats()
        spell_stats = self._spell_get_runtime_stats()
        combo_stats = self._combo_get_runtime_stats()
        self._track_combo_run(snapshot, buffs, spell_stats, combo_stats)

        pause_reasons = tuple(
            self._get_non_click_pause_reasons(
                buffs,
                spell_diag=spell_diag,
                combo_diag=combo_diag,
            )
        )
        pause_non_click_actions = bool(pause_reasons)
        pause_stock_trading = self._should_pause_stock_trading(buffs)
        allow_non_click_actions_during_pause = self._should_allow_non_click_actions_during_pause(
            snapshot,
            pause_reasons,
        )
        upgrade_pause_eval = self._evaluate_upgrade_buff_window(
            snapshot,
            buffs,
            upgrade_diag,
            pause_reasons,
        )

        self._decorate_diagnostics(
            options=options,
            building_diag=building_diag,
            ascension_prep_diag=ascension_prep_diag,
            upgrade_diag=upgrade_diag,
            dragon_diag=dragon_diag,
            santa_diag=santa_diag,
            bank_diag=bank_diag,
            reserve_budget=reserve_budget,
            pause_stock_trading=pause_stock_trading,
        )

        upgrade_diag["pause_reasons"] = pause_reasons
        upgrade_diag["allow_during_pause"] = bool(upgrade_pause_eval.get("allow_during_pause"))
        upgrade_diag["buff_window_seconds"] = upgrade_pause_eval.get("buff_window_seconds")
        upgrade_diag["estimated_live_delta_cps"] = upgrade_pause_eval.get("estimated_delta_cps")
        upgrade_diag["estimated_buff_window_gain"] = upgrade_pause_eval.get("estimated_window_gain")
        upgrade_diag["pause_window_reason"] = upgrade_pause_eval.get("reason")

        defer_stock_for_upgrade = self._should_defer_stock_actions_for_upgrade(
            snapshot,
            upgrade_diag,
            upgrade_autobuy_enabled=options.upgrade_autobuy_enabled,
            pause_non_click_actions=pause_non_click_actions,
            allow_upgrade_during_pause=(
                bool(upgrade_diag.get("allow_during_pause")) or allow_non_click_actions_during_pause
            ),
            global_cookie_reserve=reserve_budget["total_reserve"],
        )

        bank_diag["paused_for_upgrade_priority"] = defer_stock_for_upgrade
        if pause_stock_trading:
            bank_diag["buy_actions_enabled"] = False
            bank_diag["sell_actions_enabled"] = False
            bank_diag["enabled"] = False
            bank_diag["reason"] = "paused_for_production_buff"
        elif defer_stock_for_upgrade:
            bank_diag["buy_actions_enabled"] = False
            bank_diag["sell_actions_enabled"] = False
            bank_diag["enabled"] = False
            bank_diag["reason"] = "paused_for_upgrade_priority"

        diagnostics = DomLoopDiagnostics(
            garden_diag=garden_diag,
            lump_diag=lump_diag,
            building_diag=building_diag,
            ascension_prep_diag=ascension_prep_diag,
            upgrade_diag=upgrade_diag,
            dragon_diag=dragon_diag,
            santa_diag=santa_diag,
            golden_diag=golden_diag,
            spell_diag=spell_diag,
            reserve_budget=reserve_budget,
            purchase_goal=purchase_goal,
            stock_buy_controls=stock_buy_controls,
            stock_management_active=stock_management_active,
            bank_diag=bank_diag,
            wrinkler_diag=wrinkler_diag,
            combo_diag=combo_diag,
            trade_stats=trade_stats,
            spell_stats=spell_stats,
            combo_stats=combo_stats,
            pause_reasons=pause_reasons,
            pause_non_click_actions=pause_non_click_actions,
            pause_stock_trading=pause_stock_trading,
            allow_non_click_actions_during_pause=allow_non_click_actions_during_pause,
            defer_stock_for_upgrade=defer_stock_for_upgrade,
        )
        return diagnostics, refreshed_cache

    def publish_runtime(
        self,
        prepared: PreparedSnapshot,
        diagnostics: DomLoopDiagnostics,
        options: DomLoopBuildOptions,
    ) -> None:
        snapshot = prepared.snapshot
        self._set_runtime(
            last_feed_age="none" if snapshot is None else f"{snapshot.get('_age', 0.0):.3f}s",
            last_big_cookie=None
            if prepared.big_cookie is None
            else f"({prepared.big_cookie['client_x']},{prepared.big_cookie['client_y']})",
            last_buffs=tuple(buff["name"] for buff in prepared.buffs),
            last_shimmer_telemetry=(
                snapshot.get("shimmerTelemetry")
                if isinstance(snapshot, dict) and isinstance(snapshot.get("shimmerTelemetry"), dict)
                else {}
            ),
            last_spell_diag=diagnostics.spell_diag,
            last_bank_diag=diagnostics.bank_diag,
            last_garden_diag=diagnostics.garden_diag,
            last_building_diag=diagnostics.building_diag,
            last_upgrade_diag=diagnostics.upgrade_diag,
            last_dragon_diag=diagnostics.dragon_diag,
            last_santa_diag=diagnostics.santa_diag,
            last_ascension_prep_diag=diagnostics.ascension_prep_diag,
            last_ascension=(
                snapshot.get("ascension")
                if isinstance(snapshot, dict) and isinstance(snapshot.get("ascension"), dict)
                else {}
            ),
            last_lump_diag=diagnostics.lump_diag,
            last_golden_diag=diagnostics.golden_diag,
            last_purchase_goal=diagnostics.purchase_goal,
            last_wrinkler_diag=diagnostics.wrinkler_diag,
            last_combo_diag=diagnostics.combo_diag,
            stock_trading_enabled=options.stock_trading_enabled,
            lucky_reserve_enabled=options.lucky_reserve_enabled,
            building_autobuy_enabled=options.building_autobuy_enabled,
            upgrade_autobuy_enabled=options.upgrade_autobuy_enabled,
            ascension_prep_enabled=options.ascension_prep_enabled,
            garden_automation_enabled=options.garden_automation_enabled,
            snapshot_profile=(
                snapshot.get("profile")
                if isinstance(snapshot, dict) and isinstance(snapshot.get("profile"), dict)
                else {}
            ),
            stock_profile=diagnostics.trade_stats.get("profile", {}),
            db_profile=diagnostics.trade_stats.get("db_profile", {}),
        )

    @staticmethod
    def build_feed_signature(
        prepared: PreparedSnapshot,
        diagnostics: DomLoopDiagnostics,
    ) -> tuple[Any, ...]:
        return (
            len(prepared.shimmers),
            tuple((item["id"], item["wrath"]) for item in prepared.shimmers[:4]),
            None if prepared.spell is None else (prepared.spell["ready"], prepared.spell["on_minigame"]),
            diagnostics.spell_diag.get("reason"),
            diagnostics.spell_diag.get("candidate"),
            diagnostics.bank_diag.get("reason"),
            diagnostics.bank_diag.get("buy_candidate"),
            diagnostics.bank_diag.get("sell_candidate"),
            diagnostics.garden_diag.get("reason"),
            diagnostics.garden_diag.get("soil"),
            diagnostics.garden_diag.get("selected_seed"),
            diagnostics.garden_diag.get("next_locked_seed"),
            diagnostics.upgrade_diag.get("reason"),
            diagnostics.upgrade_diag.get("candidate"),
            diagnostics.dragon_diag.get("reason"),
            diagnostics.dragon_diag.get("next_action"),
            diagnostics.wrinkler_diag.get("reason"),
            diagnostics.wrinkler_diag.get("candidate_id"),
            diagnostics.building_diag.get("reason"),
            diagnostics.building_diag.get("candidate"),
            diagnostics.ascension_prep_diag.get("reason"),
            diagnostics.ascension_prep_diag.get("building"),
            diagnostics.ascension_prep_diag.get("kind"),
            diagnostics.combo_diag.get("reason"),
            diagnostics.combo_diag.get("candidate_building"),
            diagnostics.combo_diag.get("candidate_quantity"),
            diagnostics.lump_diag.get("reason"),
            diagnostics.lump_diag.get("stage"),
            diagnostics.lump_diag.get("current_type_name"),
            diagnostics.lump_diag.get("is_ripe"),
        )

    @staticmethod
    def _decorate_diagnostics(
        *,
        options: DomLoopBuildOptions,
        building_diag: dict[str, Any],
        ascension_prep_diag: dict[str, Any],
        upgrade_diag: dict[str, Any],
        dragon_diag: dict[str, Any],
        santa_diag: dict[str, Any],
        bank_diag: dict[str, Any],
        reserve_budget: dict[str, Any],
        pause_stock_trading: bool,
    ) -> None:
        garden_cookie_reserve = reserve_budget["garden_reserve"]
        lucky_cookie_reserve = reserve_budget["lucky_reserve"]
        hard_lucky_cookie_reserve = reserve_budget["hard_lucky_reserve"]
        live_lucky_cookie_reserve = reserve_budget["live_lucky_reserve"]
        soft_lucky_cookie_reserve = reserve_budget["soft_lucky_delta"]
        global_cookie_reserve = reserve_budget["total_reserve"]
        building_cookie_reserve = reserve_budget["building_total_reserve"]
        burst_window = reserve_budget["burst_window"]

        bank_diag["buying_enabled"] = options.stock_trading_enabled
        bank_diag["selling_enabled"] = True
        bank_diag["enabled"] = bool(bank_diag.get("buy_actions_enabled") or bank_diag.get("sell_actions_enabled"))
        bank_diag["lucky_cookie_reserve"] = lucky_cookie_reserve
        bank_diag["hard_lucky_cookie_reserve"] = hard_lucky_cookie_reserve
        bank_diag["live_lucky_cookie_reserve"] = live_lucky_cookie_reserve
        bank_diag["soft_lucky_cookie_reserve"] = soft_lucky_cookie_reserve
        bank_diag["global_cookie_reserve"] = global_cookie_reserve
        bank_diag["paused_for_production_buff"] = pause_stock_trading

        building_diag["enabled"] = options.building_autobuy_enabled
        building_diag["garden_cookie_reserve"] = garden_cookie_reserve
        building_diag["lucky_cookie_reserve"] = lucky_cookie_reserve
        building_diag["hard_lucky_cookie_reserve"] = hard_lucky_cookie_reserve
        building_diag["live_lucky_cookie_reserve"] = live_lucky_cookie_reserve
        building_diag["soft_lucky_cookie_reserve"] = soft_lucky_cookie_reserve
        building_diag["global_cookie_reserve"] = global_cookie_reserve
        building_diag["building_cookie_reserve"] = building_cookie_reserve
        building_diag["building_buff_burst_window"] = burst_window
        building_diag["autobuyer_reserve"] = building_diag.get("reserve")
        building_diag["reserve"] = max(
            float(building_diag.get("reserve") or 0.0),
            float(building_cookie_reserve),
        )
        building_diag["spendable"] = max(
            0.0,
            float(building_diag.get("cookies") or 0.0) - float(building_diag["reserve"]),
        )

        for diag in (upgrade_diag, dragon_diag):
            diag["garden_cookie_reserve"] = garden_cookie_reserve
            diag["lucky_cookie_reserve"] = lucky_cookie_reserve
            diag["hard_lucky_cookie_reserve"] = hard_lucky_cookie_reserve
            diag["live_lucky_cookie_reserve"] = live_lucky_cookie_reserve
            diag["global_cookie_reserve"] = global_cookie_reserve
        upgrade_diag["soft_lucky_cookie_reserve"] = soft_lucky_cookie_reserve
        upgrade_diag["building_cookie_reserve"] = building_cookie_reserve
        upgrade_diag["building_buff_burst_window"] = burst_window
        ascension_prep_diag["enabled"] = options.ascension_prep_enabled


class DomLoopCyclePreparer:
    """Builds one dom_loop cycle snapshot/diagnostics bundle."""

    def __init__(
        self,
        *,
        snapshot_preparer: DomSnapshotPreparer,
        diagnostics_builder: DomDiagnosticsBuilder,
        should_pause_value_actions_during_clot: Callable[[list[dict[str, Any]]], bool],
        perf_counter: Callable[[], float],
        monotonic: Callable[[], float],
        record_profile_ms: Callable[[str, float], None],
    ):
        self._snapshot_preparer = snapshot_preparer
        self._diagnostics_builder = diagnostics_builder
        self._should_pause_value_actions_during_clot = should_pause_value_actions_during_clot
        self._perf_counter = perf_counter
        self._monotonic = monotonic
        self._record_profile_ms = record_profile_ms

    def prepare_cycle(
        self,
        *,
        build_options: DomLoopBuildOptions,
        bank_diag_cache: BankDiagCache,
    ) -> DomLoopCycleState:
        extract_started = self._perf_counter()
        prepared = self._snapshot_preparer.prepare(
            building_autobuy_enabled=build_options.building_autobuy_enabled,
            lucky_reserve_enabled=build_options.lucky_reserve_enabled,
        )
        self._record_profile_ms(
            "dom_extract",
            (self._perf_counter() - extract_started) * 1000.0,
            spike_ms=20.0,
        )
        diag_started = self._perf_counter()
        diagnostics, bank_diag_cache = self._diagnostics_builder.build(
            prepared,
            bank_diag_cache,
            build_options,
        )
        self._record_profile_ms(
            "dom_diag",
            (self._perf_counter() - diag_started) * 1000.0,
            spike_ms=25.0,
        )
        self._diagnostics_builder.publish_runtime(prepared, diagnostics, build_options)
        return DomLoopCycleState(
            build_options=build_options,
            prepared=prepared,
            diagnostics=diagnostics,
            bank_diag_cache=bank_diag_cache,
            now=self._monotonic(),
            pause_value_actions_during_clot=self._should_pause_value_actions_during_clot(
                prepared.buffs
            ),
        )


class DomActionExecutor:
    """Executes low-level dom loop actions while leaving planning in clicker.py."""

    def __init__(
        self,
        *,
        log: Any,
        click_lock: Any,
        click: Callable[..., None],
        scroll: Callable[..., None],
        can_interact_with_game: Callable[[float], bool],
        ui_owner_conflicts: Callable[[str, float], bool],
        should_throttle_ui_action: Callable[[str, int, int, float], bool],
        claim_ui_owner: Callable[[str, float], None],
        move_mouse: Callable[..., None],
        record_profile_ms: Callable[[str, float, float | None], None],
        set_runtime: Callable[..., None],
        record_event: Callable[[str], None],
        time_monotonic: Callable[[], float],
        perf_counter: Callable[[], float],
        sleep: SleepFn,
        building_click_hold: float,
        spell_click_hold: float,
        feed_poll_interval: float,
        main_click_suppress_seconds: float,
        suppress_main_click_until_getter: Callable[[], float],
        suppress_main_click_until_setter: Callable[[float], None],
    ):
        self._log = log
        self._click_lock = click_lock
        self._click = click
        self._scroll = scroll
        self._can_interact_with_game = can_interact_with_game
        self._ui_owner_conflicts = ui_owner_conflicts
        self._should_throttle_ui_action = should_throttle_ui_action
        self._claim_ui_owner = claim_ui_owner
        self._move_mouse = move_mouse
        self._record_profile_ms = record_profile_ms
        self._set_runtime = set_runtime
        self._record_event = record_event
        self._time_monotonic = time_monotonic
        self._perf_counter = perf_counter
        self._sleep = sleep
        self._building_click_hold = building_click_hold
        self._spell_click_hold = spell_click_hold
        self._feed_poll_interval = feed_poll_interval
        self._main_click_suppress_seconds = main_click_suppress_seconds
        self._get_suppress_main_click_until = suppress_main_click_until_getter
        self._set_suppress_main_click_until = suppress_main_click_until_setter

    def execute_lump_action(self, lump_diag: dict[str, Any], now: float) -> float | None:
        if not self._can_interact_with_game(now):
            self._sleep(self._feed_poll_interval)
            return None
        self._suppress_main_click(now)
        self._log.info(
            f"Harvesting sugar lump stage={lump_diag.get('stage')} "
            f"type={lump_diag.get('current_type_name')} "
            f"lumps={lump_diag.get('lumps')} "
            f"screen=({lump_diag.get('screen_x')},{lump_diag.get('screen_y')})"
        )
        with self._click_lock:
            self._click(
                lump_diag["screen_x"],
                lump_diag["screen_y"],
                hold=self._building_click_hold,
            )
        action_at = self._time_monotonic()
        self._set_runtime(
            last_lump_action=(
                f"harvest {lump_diag.get('current_type_name')} "
                f"({lump_diag.get('stage')})"
            )
        )
        self._record_event(
            f"Sugar lump harvest {lump_diag.get('current_type_name')} "
            f"stage={lump_diag.get('stage')}"
        )
        self._sleep(self._feed_poll_interval)
        return action_at

    def execute_note_action(self, note_action: dict[str, Any], now: float) -> float | None:
        if not self._can_interact_with_game(now):
            self._sleep(self._feed_poll_interval)
            return None
        self._suppress_main_click(now)
        self._log.info(
            f"Dismissing note kind={note_action['kind']} "
            f"title={note_action['title']!r} count={note_action['count']} "
            f"screen=({note_action['screen_x']},{note_action['screen_y']})"
        )
        with self._click_lock:
            self._click(
                note_action["screen_x"],
                note_action["screen_y"],
                hold=self._building_click_hold,
            )
        action_at = self._time_monotonic()
        self._set_runtime(
            last_note_action=(
                note_action["kind"]
                if not note_action.get("title")
                else f"{note_action['kind']} {note_action['title']}"
            )
        )
        self._record_event(
            "Notification dismissed "
            f"{note_action['kind']}"
            + ("" if not note_action.get("title") else f" {note_action['title']}")
            + f" (count={note_action['count']})"
        )
        self._sleep(self._feed_poll_interval)
        return action_at

    def execute_combo_action(self, combo_action: Any, now: float, action_started: float, combo_recorder: Any) -> float | None:
        if not self._can_interact_with_game(now):
            self._sleep(self._feed_poll_interval)
            return None
        self._record_profile_ms("dom_action", (self._perf_counter() - action_started) * 1000.0, spike_ms=25.0)
        self._suppress_main_click(now)
        self._log.info(
            f"Executing combo action kind={combo_action.kind} building={combo_action.building_name} "
            f"quantity={combo_action.quantity} detail={combo_action.detail} "
            f"screen=({combo_action.screen_x},{combo_action.screen_y})"
        )
        with self._click_lock:
            if combo_action.kind == "scroll_store":
                self._scroll(combo_action.screen_x, combo_action.screen_y, combo_action.scroll_steps or 0)
            else:
                self._click(combo_action.screen_x, combo_action.screen_y, hold=self._building_click_hold)
        combo_recorder.record_action(combo_action)
        self._set_runtime(last_combo_action=f"{combo_action.detail} {combo_action.building_name or ''}".strip())
        action_at = self._time_monotonic()
        self._sleep(self._feed_poll_interval)
        return action_at

    def execute_spell_action(self, spell_action: Any, now: float, action_started: float, spell_recorder: Any) -> float | None:
        if not self._can_interact_with_game(now):
            self._sleep(self._feed_poll_interval)
            return None
        if self._ui_owner_conflicts("grimoire", now):
            self._sleep(self._feed_poll_interval)
            return None
        if spell_action.kind == "open_grimoire" and self._should_throttle_ui_action(
            spell_action.kind,
            spell_action.screen_x,
            spell_action.screen_y,
            now,
        ):
            self._sleep(self._feed_poll_interval)
            return None
        self._record_profile_ms("dom_action", (self._perf_counter() - action_started) * 1000.0, spike_ms=25.0)
        self._suppress_main_click(now)
        if spell_action.kind == "open_grimoire":
            self._log.info(
                f"Opening grimoire screen=({spell_action.screen_x},{spell_action.screen_y}) "
                f"magic={0.0 if spell_action.magic is None else spell_action.magic:.1f}/"
                f"{0.0 if spell_action.max_magic is None else spell_action.max_magic:.1f}"
            )
        else:
            self._log.info(
                f"Casting spell key={spell_action.key} name={spell_action.name} "
                f"screen=({spell_action.screen_x},{spell_action.screen_y}) "
                f"magic={0.0 if spell_action.magic is None else spell_action.magic:.1f}/"
                f"{0.0 if spell_action.max_magic is None else spell_action.max_magic:.1f} "
                f"cost={0.0 if spell_action.cost is None else spell_action.cost:.1f} "
                f"reason={spell_action.reason}"
            )
        with self._click_lock:
            self._click(spell_action.screen_x, spell_action.screen_y, hold=self._spell_click_hold)
        self._claim_ui_owner("grimoire", now)
        spell_recorder.record_action(spell_action)
        if spell_action.kind == "open_grimoire":
            self._set_runtime(last_spell_cast="Open Grimoire")
            self._record_event("Spellbook open requested")
        else:
            self._set_runtime(last_spell_cast=f"{spell_action.name} ({spell_action.reason})")
            self._record_event(f"Spell cast {spell_action.name} reason={spell_action.reason}")
        action_at = self._time_monotonic()
        self._sleep(self._feed_poll_interval)
        return action_at

    def execute_garden_action(self, garden_action: Any, now: float, action_started: float, garden_recorder: Any) -> bool:
        if not self._can_interact_with_game(now):
            self._sleep(self._feed_poll_interval)
            return False
        if self._ui_owner_conflicts("garden", now):
            self._sleep(self._feed_poll_interval)
            return False
        if garden_action.kind in {"open_garden", "focus_garden"} and self._should_throttle_ui_action(
            garden_action.kind,
            garden_action.screen_x,
            garden_action.screen_y,
            now,
        ):
            self._sleep(self._feed_poll_interval)
            return False
        self._record_profile_ms("dom_action", (self._perf_counter() - action_started) * 1000.0, spike_ms=25.0)
        self._suppress_main_click(now)
        self._log.info(
            f"Executing garden action kind={garden_action.kind} "
            f"detail={garden_action.detail} "
            f"screen=({garden_action.screen_x},{garden_action.screen_y})"
        )
        with self._click_lock:
            self._click(garden_action.screen_x, garden_action.screen_y, hold=self._building_click_hold)
        self._claim_ui_owner("garden", now)
        garden_recorder.record_action(garden_action)
        self._set_runtime(last_garden_action=garden_action.detail or garden_action.kind)
        self._record_event(f"Garden action {garden_action.detail or garden_action.kind}")
        self._sleep(self._feed_poll_interval)
        return True

    def execute_upgrade_action(
        self,
        *,
        now: float,
        action_started: float,
        snapshot: dict[str, Any] | None,
        upgrade_diag: dict[str, Any],
        upgrade_action: Any,
        upgrade_store_action: Any,
        upgrade_signature: Any,
        last_upgrade_focus_signature: Any,
        last_upgrade_focus_at: float,
        last_upgrade_focus_point: tuple[int, int] | None,
        upgrade_attempt_tracker: dict[str, Any],
        upgrade_stuck_attempt_limit: int,
        upgrade_stuck_signature_suppress_seconds: float,
        post_upgrade_wrinkler_cooldown_seconds: float,
        extract_upgrade_target_debug: Callable[[dict[str, Any] | None, Any], Any],
        format_upgrade_planner_context: Callable[[Any], str],
    ) -> dict[str, Any] | None:
        if not self._can_interact_with_game(now):
            self._sleep(self._feed_poll_interval)
            return None
        if self._ui_owner_conflicts("upgrade_store", now):
            self._sleep(self._feed_poll_interval)
            return None
        self._record_profile_ms("dom_action", (self._perf_counter() - action_started) * 1000.0, spike_ms=25.0)
        self._suppress_main_click(now)
        upgrade_target_debug = extract_upgrade_target_debug(snapshot, upgrade_diag.get("candidate_id"))
        snapshot_age = None if not isinstance(snapshot, dict) else snapshot.get("_age")
        store_state = snapshot.get("store") if isinstance(snapshot, dict) else None
        if upgrade_store_action is not None:
            self._log.info(
                f"Executing upgrade store prep kind={upgrade_store_action.kind} "
                f"store_mode={upgrade_store_action.current_store_mode}->{upgrade_store_action.store_mode} "
                f"store_bulk={upgrade_store_action.current_store_bulk}->{upgrade_store_action.store_bulk} "
                f"screen=({upgrade_store_action.screen_x},{upgrade_store_action.screen_y})"
            )
        else:
            self._log.info(
                f"Executing upgrade action kind={upgrade_action.kind} "
                f"name={upgrade_diag.get('candidate')} id={upgrade_diag.get('candidate_id')} "
                f"price={0.0 if upgrade_diag.get('candidate_price') is None else float(upgrade_diag.get('candidate_price')):.1f} "
                f"screen=({upgrade_action.screen_x},{upgrade_action.screen_y})"
                f"{format_upgrade_planner_context(getattr(upgrade_action, 'planner_context', None))}"
            )
            self._log.debug(
                "Upgrade action debug "
                f"snapshot_age={None if snapshot_age is None else round(float(snapshot_age), 4)} "
                f"store_mode={store_state.get('buyMode') if isinstance(store_state, dict) else None} "
                f"store_bulk={store_state.get('buyBulk') if isinstance(store_state, dict) else None} "
                f"feed_target_click={None if not upgrade_target_debug else upgrade_target_debug.get('target_click')} "
                f"feed_target_center={None if not upgrade_target_debug else upgrade_target_debug.get('target_center')} "
                f"feed_target_raw_center={None if not upgrade_target_debug else upgrade_target_debug.get('target_raw_center')} "
                f"feed_target_bounds={None if not upgrade_target_debug else upgrade_target_debug.get('target_bounds')} "
                f"feed_row_click={None if not upgrade_target_debug else upgrade_target_debug.get('row_click')} "
                f"feed_row_center={None if not upgrade_target_debug else upgrade_target_debug.get('row_center')} "
                f"feed_row_raw_center={None if not upgrade_target_debug else upgrade_target_debug.get('row_raw_center')} "
                f"chosen_screen=({upgrade_action.screen_x},{upgrade_action.screen_y})"
            )
        with self._click_lock:
            if upgrade_store_action is not None:
                self._click(upgrade_store_action.screen_x, upgrade_store_action.screen_y, hold=self._building_click_hold)
            elif upgrade_action.kind == "focus_store_section":
                self._move_mouse(upgrade_action.screen_x, upgrade_action.screen_y)
            else:
                smooth_upgrade_click = (
                    upgrade_action.kind == "click_upgrade"
                    and upgrade_signature == last_upgrade_focus_signature
                    and (now - last_upgrade_focus_at) <= 2.0
                )
                if smooth_upgrade_click and last_upgrade_focus_point is not None:
                    self._move_mouse(last_upgrade_focus_point[0], last_upgrade_focus_point[1])
                    self._sleep(0.06)
                self._click(
                    upgrade_action.screen_x,
                    upgrade_action.screen_y,
                    hold=self._building_click_hold,
                    move_duration=0.14 if smooth_upgrade_click else 0,
                )
        self._claim_ui_owner("upgrade_store", now)
        action_at = self._time_monotonic()
        result = {
            "action_at": action_at,
            "last_upgrade_skip_signature": None,
            "post_upgrade_wrinkler_cooldown_until": None,
            "last_upgrade_focus_signature": last_upgrade_focus_signature,
            "last_upgrade_focus_at": last_upgrade_focus_at,
            "last_upgrade_focus_point": last_upgrade_focus_point,
        }
        if upgrade_store_action is not None:
            self._set_runtime(last_trade_action=f"prepare upgrades {upgrade_store_action.kind}")
        elif upgrade_action.kind == "click_upgrade":
            upgrade_attempt_tracker["candidate_id"] = int(upgrade_diag.get("candidate_id"))
            upgrade_attempt_tracker["candidate_signature"] = upgrade_signature
            upgrade_attempt_tracker["attempts"] = int(upgrade_attempt_tracker.get("attempts") or 0) + 1
            if upgrade_attempt_tracker["attempts"] >= upgrade_stuck_attempt_limit:
                upgrade_attempt_tracker["blocked_until"] = action_at + upgrade_stuck_signature_suppress_seconds
                upgrade_attempt_tracker["blocked_signature"] = upgrade_signature
                self._log.warning(
                    f"Upgrade candidate appears stuck name={upgrade_diag.get('candidate')} "
                    f"id={upgrade_diag.get('candidate_id')} "
                    f"attempts={upgrade_attempt_tracker['attempts']} "
                    f"backoff_seconds={upgrade_stuck_signature_suppress_seconds:.1f}"
                )
            result["post_upgrade_wrinkler_cooldown_until"] = (
                action_at + post_upgrade_wrinkler_cooldown_seconds
            )
            self._set_runtime(last_trade_action=f"upgrade {upgrade_diag.get('candidate')}")
            self._record_event(f"Upgrade buy {upgrade_diag.get('candidate')}")
        elif upgrade_action.kind == "focus_store_section":
            result["last_upgrade_focus_signature"] = upgrade_signature
            result["last_upgrade_focus_at"] = action_at
            result["last_upgrade_focus_point"] = (upgrade_action.screen_x, upgrade_action.screen_y)
            self._set_runtime(last_trade_action=f"focus upgrades {upgrade_diag.get('candidate')}")
        self._sleep(self._feed_poll_interval)
        return result

    def execute_wrinkler_action(self, wrinkler_action: Any, now: float, action_started: float, wrinkler_recorder: Any, bonus_click_hold: float) -> float | None:
        if not self._can_interact_with_game(now):
            self._sleep(self._feed_poll_interval)
            return None
        self._record_profile_ms("dom_action", (self._perf_counter() - action_started) * 1000.0, spike_ms=25.0)
        self._suppress_main_click(now)
        self._log.info(
            f"Clicking wrinkler id={wrinkler_action.wrinkler_id} "
            f"type={wrinkler_action.wrinkler_type} "
            f"reward={wrinkler_action.estimated_reward:.1f} "
            f"screen=({wrinkler_action.screen_x},{wrinkler_action.screen_y}) "
            f"reason={wrinkler_action.reason}"
        )
        with self._click_lock:
            self._click(wrinkler_action.screen_x, wrinkler_action.screen_y, hold=bonus_click_hold)
        wrinkler_recorder.record_action(wrinkler_action)
        self._set_runtime(last_wrinkler_action=f"id={wrinkler_action.wrinkler_id} reason={wrinkler_action.reason}")
        self._record_event(f"Wrinkler click id={wrinkler_action.wrinkler_id} reason={wrinkler_action.reason}")
        action_at = self._time_monotonic()
        self._sleep(self._feed_poll_interval)
        return action_at

    def execute_dragon_action(self, dragon_action: dict[str, Any], dragon_diag: dict[str, Any], now: float, action_started: float) -> float | None:
        if not self._can_interact_with_game(now):
            self._sleep(self._feed_poll_interval)
            return None
        if self._ui_owner_conflicts("dragon", now):
            self._sleep(self._feed_poll_interval)
            return None
        if dragon_action["kind"] == "open_dragon" and self._should_throttle_ui_action(
            dragon_action["kind"],
            dragon_action["screen_x"],
            dragon_action["screen_y"],
            now,
        ):
            self._sleep(self._feed_poll_interval)
            return None
        self._record_profile_ms("dom_action", (self._perf_counter() - action_started) * 1000.0, spike_ms=25.0)
        self._suppress_main_click(now)
        self._log.info(
            f"Executing dragon action kind={dragon_action['kind']} "
            f"level={dragon_diag.get('level')}/{dragon_diag.get('max_level')} "
            f"name={dragon_diag.get('current_name')} "
            f"next={dragon_diag.get('next_action')} "
            f"cost={dragon_diag.get('next_cost_text')} "
            f"aura_primary={dragon_diag.get('aura_primary')} "
            f"aura_secondary={dragon_diag.get('aura_secondary')} "
            f"detail={dragon_action.get('detail')} "
            f"screen=({dragon_action['screen_x']},{dragon_action['screen_y']})"
        )
        with self._click_lock:
            self._click(dragon_action["screen_x"], dragon_action["screen_y"], hold=self._building_click_hold)
        self._claim_ui_owner("dragon", now)
        action_at = self._time_monotonic()
        self._set_runtime(
            last_dragon_action=(
                f"{dragon_action['kind']} {dragon_diag.get('next_action') or dragon_diag.get('current_name')}"
            )
        )
        self._record_event(
            f"Dragon {dragon_action['kind']} "
            f"{dragon_diag.get('next_action') or dragon_diag.get('current_name')}"
        )
        self._sleep(self._feed_poll_interval)
        return action_at

    def execute_santa_action(self, santa_action: Any, now: float, action_started: float, santa_recorder: Any) -> float | None:
        if not self._can_interact_with_game(now):
            self._sleep(self._feed_poll_interval)
            return None
        if self._ui_owner_conflicts("santa", now):
            self._sleep(self._feed_poll_interval)
            return None
        self._record_profile_ms("dom_action", (self._perf_counter() - action_started) * 1000.0, spike_ms=25.0)
        self._suppress_main_click(now)
        self._log.info(
            f"Clicking santa level={santa_action.level}/{santa_action.max_level} "
            f"current={santa_action.current_name} next={santa_action.next_name} "
            f"target={santa_action.target_level} "
            f"screen=({santa_action.screen_x},{santa_action.screen_y}) "
            f"reason={santa_action.reason}"
        )
        with self._click_lock:
            self._click(santa_action.screen_x, santa_action.screen_y, hold=self._building_click_hold)
        self._claim_ui_owner("santa", now)
        santa_recorder.record_action(santa_action)
        self._set_runtime(
            last_santa_action=(
                f"{santa_action.current_name or 'Santa'} -> {santa_action.next_name or santa_action.target_level}"
            )
        )
        self._record_event(
            f"Santa level-up level={santa_action.level} "
            f"current={santa_action.current_name} next={santa_action.next_name}"
        )
        action_at = self._time_monotonic()
        self._sleep(self._feed_poll_interval)
        return action_at

    def execute_ascension_prep_action(self, ascension_prep_action: Any, store_action: Any, now: float, action_started: float, ascension_recorder: Any) -> float | None:
        if not self._can_interact_with_game(now):
            self._sleep(self._feed_poll_interval)
            return None
        if self._ui_owner_conflicts("ascension_store", now):
            self._sleep(self._feed_poll_interval)
            return None
        self._record_profile_ms("dom_action", (self._perf_counter() - action_started) * 1000.0, spike_ms=25.0)
        self._suppress_main_click(now)
        self._log.info(
            f"Executing ascension prep kind={ascension_prep_action.kind} "
            f"name={ascension_prep_action.building_name} id={ascension_prep_action.building_id} "
            f"quantity={ascension_prep_action.quantity} threshold={ascension_prep_action.threshold} "
            f"phase={ascension_prep_action.phase} "
            f"store_mode={store_action.current_store_mode}->{store_action.store_mode} "
            f"store_bulk={store_action.current_store_bulk}->{store_action.store_bulk} "
            f"screen=({store_action.screen_x},{store_action.screen_y})"
        )
        with self._click_lock:
            if store_action.kind == "scroll_store":
                self._scroll(store_action.screen_x, store_action.screen_y, store_action.scroll_steps or 0)
            else:
                self._click(store_action.screen_x, store_action.screen_y, hold=self._building_click_hold)
        self._claim_ui_owner("ascension_store", now)
        action_at = self._time_monotonic()
        if store_action.kind == "click_building":
            ascension_recorder.record_action(ascension_prep_action)
            self._set_runtime(
                last_ascension_prep_action=(
                    f"{ascension_prep_action.kind} {ascension_prep_action.quantity} "
                    f"{ascension_prep_action.building_name} to {ascension_prep_action.threshold}"
                )
            )
            self._record_event(
                f"Ascension prep {ascension_prep_action.kind} {ascension_prep_action.quantity} "
                f"{ascension_prep_action.building_name}"
            )
        elif store_action.kind in {"set_store_mode", "set_store_bulk"}:
            self._set_runtime(last_ascension_prep_action=f"prepare store {store_action.kind}")
        self._sleep(self._feed_poll_interval)
        return action_at

    def execute_trade_action(self, trade_action: Any, now: float, action_started: float, stock_recorder: Any, trade_click_hold: float) -> float | None:
        if not self._can_interact_with_game(now):
            self._sleep(self._feed_poll_interval)
            return None
        if self._ui_owner_conflicts("bank", now):
            self._sleep(self._feed_poll_interval)
            return None
        if trade_action.kind == "open_bank" and self._should_throttle_ui_action(
            trade_action.kind,
            trade_action.screen_x,
            trade_action.screen_y,
            now,
        ):
            self._sleep(self._feed_poll_interval)
            return None
        self._record_profile_ms("dom_action", (self._perf_counter() - action_started) * 1000.0, spike_ms=25.0)
        self._suppress_main_click(now)
        if trade_action.kind == "open_bank":
            self._log.info(
                f"Opening bank minigame screen=({trade_action.screen_x},{trade_action.screen_y}) "
                f"cookies={0.0 if trade_action.cookies is None else trade_action.cookies:.1f}"
            )
        elif trade_action.kind == "hire_broker":
            self._log.info(
                f"Hiring broker screen=({trade_action.screen_x},{trade_action.screen_y}) "
                f"cookies={0.0 if trade_action.cookies is None else trade_action.cookies:.1f}"
            )
        elif trade_action.kind == "upgrade_office":
            self._log.info(
                f"Upgrading bank office screen=({trade_action.screen_x},{trade_action.screen_y}) "
                f"cookies={0.0 if trade_action.cookies is None else trade_action.cookies:.1f}"
            )
        else:
            self._log.info(
                f"Executing stock action kind={trade_action.kind} good={trade_action.good_name} "
                f"id={trade_action.good_id} price={0.0 if trade_action.price is None else trade_action.price:.2f} "
                f"screen=({trade_action.screen_x},{trade_action.screen_y})"
            )
        with self._click_lock:
            self._click(trade_action.screen_x, trade_action.screen_y, hold=trade_click_hold)
        self._claim_ui_owner("bank", now)
        stock_recorder.record_action(trade_action)
        self._set_runtime(
            last_trade_action=(
                "open bank"
                if trade_action.kind == "open_bank"
                else "hire broker"
                if trade_action.kind == "hire_broker"
                else "upgrade office"
                if trade_action.kind == "upgrade_office"
                else f"{trade_action.kind} {trade_action.good_name}"
            )
        )
        action_at = self._time_monotonic()
        self._sleep(self._feed_poll_interval)
        return action_at

    def execute_building_action(
        self,
        *,
        building_action: Any,
        store_action: Any,
        snapshot: dict[str, Any] | None,
        now: float,
        action_started: float,
        building_signature: Any,
        building_attempt_tracker: dict[str, Any],
        building_stuck_attempt_limit: int,
        building_stuck_signature_suppress_seconds: float,
        building_recorder: Any,
        extract_building_target_debug: Callable[[dict[str, Any] | None, Any], Any],
        format_store_planner_context: Callable[[Any], str],
        store_scroll_wheel_multiplier: int,
    ) -> float | None:
        if self._ui_owner_conflicts("building_store", now):
            self._sleep(self._feed_poll_interval)
            return None
        self._record_profile_ms("dom_action", (self._perf_counter() - action_started) * 1000.0, spike_ms=25.0)
        self._suppress_main_click(now)
        self._log.info(
            f"Executing building action kind={store_action.kind} name={None if building_action is None else building_action.building_name} "
            f"id={None if building_action is None else building_action.building_id} price={0.0 if building_action is None or building_action.price is None else building_action.price:.1f} "
            f"quantity={1 if building_action is None or building_action.quantity is None else building_action.quantity} "
            f"delta_cps={0.0 if building_action is None or building_action.delta_cps is None else building_action.delta_cps:.4f} "
            f"payback={0.0 if building_action is None or building_action.payback_seconds is None else building_action.payback_seconds:.1f}s "
            f"store_mode={store_action.current_store_mode}->{store_action.store_mode} "
            f"store_bulk={store_action.current_store_bulk}->{store_action.store_bulk} "
            f"screen=({store_action.screen_x},{store_action.screen_y})"
            f"{format_store_planner_context(store_action.planner_context)}"
        )
        with self._click_lock:
            if store_action.kind == "scroll_store":
                self._scroll(store_action.screen_x, store_action.screen_y, store_action.scroll_steps or 0)
                self._log.debug(
                    f"Building store scroll dispatched name={None if building_action is None else building_action.building_name} "
                    f"id={None if building_action is None else building_action.building_id} "
                    f"steps={store_action.scroll_steps or 0} "
                    f"wheel_delta={(store_action.scroll_steps or 0) * store_scroll_wheel_multiplier} "
                    f"anchor=({store_action.screen_x},{store_action.screen_y})"
                )
            else:
                building_target_debug = extract_building_target_debug(
                    snapshot,
                    None if building_action is None else building_action.building_id,
                )
                snapshot_age = None if not isinstance(snapshot, dict) else snapshot.get("_age")
                self._click(store_action.screen_x, store_action.screen_y, hold=self._building_click_hold, debug=True)
                self._log.debug(
                    f"Building action debug snapshot_age={None if snapshot_age is None else round(float(snapshot_age), 4)} "
                    f"feed_target_click={None if not building_target_debug else building_target_debug.get('target_click')} "
                    f"feed_target_center={None if not building_target_debug else building_target_debug.get('target_center')} "
                    f"feed_target_raw_center={None if not building_target_debug else building_target_debug.get('target_raw_center')} "
                    f"feed_target_bounds={None if not building_target_debug else building_target_debug.get('target_bounds')} "
                    f"feed_row_click={None if not building_target_debug else building_target_debug.get('row_click')} "
                    f"feed_row_center={None if not building_target_debug else building_target_debug.get('row_center')} "
                    f"feed_row_raw_center={None if not building_target_debug else building_target_debug.get('row_raw_center')} "
                    f"chosen_screen=({store_action.screen_x},{store_action.screen_y})"
                )
        self._claim_ui_owner("building_store", now)
        action_at = self._time_monotonic()
        if store_action.kind == "click_building":
            building_recorder.record_action(building_action)
            building_attempt_tracker["candidate_id"] = int(building_action.building_id)
            building_attempt_tracker["candidate_signature"] = building_signature
            building_attempt_tracker["attempts"] = int(building_attempt_tracker.get("attempts") or 0) + 1
            if building_attempt_tracker["attempts"] >= building_stuck_attempt_limit:
                building_attempt_tracker["blocked_until"] = action_at + building_stuck_signature_suppress_seconds
                building_attempt_tracker["blocked_signature"] = building_signature
                self._log.warning(
                    f"Building candidate appears stuck name={building_action.building_name} "
                    f"id={building_action.building_id} "
                    f"attempts={building_attempt_tracker['attempts']} "
                    f"backoff_seconds={building_stuck_signature_suppress_seconds:.1f}"
                )
            self._set_runtime(last_building_action=f"{building_action.building_name}")
        elif store_action.kind in {"set_store_mode", "set_store_bulk"}:
            self._set_runtime(last_building_action=f"prepare store {store_action.kind}")
        self._sleep(self._feed_poll_interval)
        return action_at

    def execute_minigame_store_action(self, owner: str, store_action: Any, now: float, action_started: float) -> bool:
        if not self._can_interact_with_game(now):
            self._sleep(self._feed_poll_interval)
            return False
        if self._ui_owner_conflicts(owner, now):
            self._sleep(self._feed_poll_interval)
            return False
        self._record_profile_ms("dom_action", (self._perf_counter() - action_started) * 1000.0, spike_ms=25.0)
        self._suppress_main_click(now)
        self._log.info(
            f"Preparing {owner} access kind={store_action.kind} "
            f"building_id={store_action.building_id} "
            f"building_name={store_action.building_name} "
            f"screen=({store_action.screen_x},{store_action.screen_y})"
        )
        with self._click_lock:
            if store_action.kind == "scroll_store":
                self._scroll(store_action.screen_x, store_action.screen_y, store_action.scroll_steps or 0)
            else:
                self._click(store_action.screen_x, store_action.screen_y, hold=self._building_click_hold)
        self._claim_ui_owner(owner, now)
        self._set_runtime(last_trade_action=f"prepare {owner} access")
        self._sleep(self._feed_poll_interval)
        return True

    def _suppress_main_click(self, now: float) -> None:
        self._set_suppress_main_click_until(
            max(
                self._get_suppress_main_click_until(),
                now + self._main_click_suppress_seconds,
            )
        )
