from dataclasses import dataclass, field
from typing import Any, Callable

from .dom_loop import (
    DomActionCoordinator,
    DomActionExecutor,
    DomActionPlanner,
    DomAttemptTracker,
    DomDiagnosticsBuilder,
    DomLoopCoordinator,
    DomLoopCyclePreparer,
    DomLoopFeedLogger,
    DomLoopLateStagePreparer,
    DomLoopOutcomeHandler,
    DomLoopStageRunner,
    DomLoopStateBridge,
    DomShimmerHandler,
    DomSnapshotPreparer,
    DomStagePolicy,
)


@dataclass
class DomLoopServiceFactory:
    snapshot_preparer_builder: Callable[[], Any]
    diagnostics_builder_builder: Callable[[], Any]
    cycle_preparer_builder: Callable[[Any, Any], Any]
    feed_logger_builder: Callable[[], Any]
    action_executor_builder: Callable[[], Any]
    action_planner_builder: Callable[[], Any]
    attempt_tracker_builder: Callable[[], Any] = DomAttemptTracker
    stage_policy_builder: Callable[[], Any] = DomStagePolicy
    late_stage_preparer_builder: Callable[[Any, Any, Any], Any] | None = None
    action_coordinator_builder: Callable[[], Any] = DomActionCoordinator
    stage_runner_builder: Callable[[Any, Any, Any, Any, Any], Any] | None = None
    outcome_handler_builder: Callable[[], Any] | None = None
    shimmer_handler_builder: Callable[[], Any] | None = None
    coordinator_builder: Callable[[Any, Any, Any, Any, Any, Any], Any] | None = None
    state_bridge_builder: Callable[[], Any] = DomLoopStateBridge
    _services: dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def snapshot_preparer(self) -> Any:
        return self._get_or_create("snapshot_preparer", self.snapshot_preparer_builder)

    def diagnostics_builder(self) -> Any:
        return self._get_or_create("diagnostics_builder", self.diagnostics_builder_builder)

    def cycle_preparer(self) -> Any:
        return self._get_or_create(
            "cycle_preparer",
            lambda: self.cycle_preparer_builder(
                self.snapshot_preparer(),
                self.diagnostics_builder(),
            ),
        )

    def feed_logger(self) -> Any:
        return self._get_or_create("feed_logger", self.feed_logger_builder)

    def action_executor(self) -> Any:
        return self._get_or_create("action_executor", self.action_executor_builder)

    def action_planner(self) -> Any:
        return self._get_or_create("action_planner", self.action_planner_builder)

    def attempt_tracker(self) -> Any:
        return self._get_or_create("attempt_tracker", self.attempt_tracker_builder)

    def stage_policy(self) -> Any:
        return self._get_or_create("stage_policy", self.stage_policy_builder)

    def late_stage_preparer(self) -> Any:
        if self.late_stage_preparer_builder is None:
            raise ValueError("late_stage_preparer_builder is required")
        return self._get_or_create(
            "late_stage_preparer",
            lambda: self.late_stage_preparer_builder(
                self.action_planner(),
                self.attempt_tracker(),
                self.stage_policy(),
            ),
        )

    def action_coordinator(self) -> Any:
        return self._get_or_create("action_coordinator", self.action_coordinator_builder)

    def stage_runner(self) -> Any:
        if self.stage_runner_builder is None:
            raise ValueError("stage_runner_builder is required")
        return self._get_or_create(
            "stage_runner",
            lambda: self.stage_runner_builder(
                self.action_coordinator(),
                self.action_executor(),
                self.action_planner(),
                self.attempt_tracker(),
                self.stage_policy(),
            ),
        )

    def outcome_handler(self) -> Any:
        if self.outcome_handler_builder is None:
            raise ValueError("outcome_handler_builder is required")
        return self._get_or_create("outcome_handler", self.outcome_handler_builder)

    def shimmer_handler(self) -> Any:
        if self.shimmer_handler_builder is None:
            raise ValueError("shimmer_handler_builder is required")
        return self._get_or_create("shimmer_handler", self.shimmer_handler_builder)

    def coordinator(self) -> Any:
        if self.coordinator_builder is None:
            raise ValueError("coordinator_builder is required")
        return self._get_or_create(
            "coordinator",
            lambda: self.coordinator_builder(
                self.cycle_preparer(),
                self.feed_logger(),
                self.shimmer_handler(),
                self.stage_runner(),
                self.late_stage_preparer(),
                self.outcome_handler(),
            ),
        )

    def state_bridge(self) -> Any:
        return self._get_or_create("state_bridge", self.state_bridge_builder)

    def _get_or_create(self, key: str, builder: Callable[[], Any]) -> Any:
        service = self._services.get(key)
        if service is None:
            service = builder()
            self._services[key] = service
        return service


def build_default_dom_loop_service_factory(
    *,
    load_feed_snapshot: Callable[[], Any],
    update_latest_snapshot: Callable[[Any], None],
    extract_shimmers: Callable[[Any], Any],
    extract_buffs: Callable[[Any], Any],
    extract_spell: Callable[[Any], Any],
    get_latest_big_cookie: Callable[[], Any],
    to_screen_point: Callable[..., Any],
    monotonic: Callable[[], float],
    garden_get_diagnostics: Callable[..., Any],
    extract_lump_diag: Callable[..., Any],
    building_get_diagnostics: Callable[..., Any],
    ascension_get_diagnostics: Callable[..., Any],
    extract_upgrade_diag: Callable[..., Any],
    extract_dragon_diag: Callable[..., Any],
    extract_golden_cookie_diag: Callable[..., Any],
    spell_get_diagnostics: Callable[..., Any],
    get_global_cookie_reserve: Callable[..., Any],
    get_next_purchase_goal: Callable[..., Any],
    apply_building_burst_purchase_goal: Callable[..., Any],
    get_stock_buy_controls: Callable[..., Any],
    stock_trade_management_active: Callable[[], bool],
    stock_get_diagnostics: Callable[..., Any],
    extract_bank_diag_disabled: Callable[..., Any],
    wrinkler_get_diagnostics: Callable[..., Any],
    combo_get_diagnostics: Callable[..., Any],
    stock_get_runtime_stats: Callable[[], Any],
    spell_get_runtime_stats: Callable[[], Any],
    combo_get_runtime_stats: Callable[[], Any],
    track_combo_run: Callable[..., None],
    get_non_click_pause_reasons: Callable[..., Any],
    should_pause_stock_trading: Callable[..., bool],
    should_allow_non_click_actions_during_pause: Callable[..., bool],
    evaluate_upgrade_buff_window: Callable[..., Any],
    should_defer_stock_actions_for_upgrade: Callable[..., bool],
    set_runtime: Callable[..., None],
    should_pause_value_actions_during_clot: Callable[..., bool],
    perf_counter: Callable[[], float],
    record_profile_ms: Callable[..., None],
    feed_debug_log_interval: float,
    log: Any,
    click_lock: Any,
    click: Callable[..., None],
    scroll: Callable[..., None],
    can_interact_with_game: Callable[..., bool],
    ui_owner_conflicts: Callable[..., bool],
    should_throttle_ui_action: Callable[..., bool],
    claim_ui_owner: Callable[..., None],
    move_mouse: Callable[..., None],
    record_event: Callable[..., None],
    time_monotonic: Callable[[], float],
    sleep: Callable[[float], None],
    building_click_hold: float,
    spell_click_hold: float,
    feed_poll_interval: float,
    main_click_suppress_seconds: float,
    suppress_main_click_until_getter: Callable[[], float],
    suppress_main_click_until_setter: Callable[[float], None],
    plan_reset_store_to_default: Callable[..., Any],
    plan_upgrade_buy: Callable[..., Any],
    get_wrinkler_action: Callable[..., Any],
    get_desired_dragon_auras: Callable[..., Any],
    plan_dragon_aura_action: Callable[..., Any],
    is_dragon_aura_unlocked: Callable[..., bool],
    get_ascension_action: Callable[..., Any],
    plan_building_buy: Callable[..., Any],
    plan_building_sell: Callable[..., Any],
    get_trade_action: Callable[..., Any],
    get_building_action: Callable[..., Any],
    has_cookies_after_reserve: Callable[..., bool],
    plan_minigame_store_access: Callable[..., Any],
    update_upgrade_attempt_tracking: Callable[..., Any],
    build_upgrade_attempt_signature: Callable[..., Any],
    upgrade_action_cooldown: float,
    note_target_getter: Callable[[], Any],
    should_allow_garden_action: Callable[..., bool],
    update_building_attempt_tracking: Callable[..., Any],
    build_building_attempt_signature: Callable[..., Any],
    extract_building_target_debug: Callable[..., Any],
    format_store_planner_context: Callable[[Any], str],
    extract_upgrade_target_debug: Callable[..., Any],
    format_upgrade_planner_context: Callable[[Any], str],
    combo_controller: Any,
    spell_controller: Any,
    garden_controller: Any,
    wrinkler_controller: Any,
    ascension_controller: Any,
    santa_controller: Any,
    stock_trader: Any,
    building_autobuyer: Any,
    lump_action_cooldown: float,
    note_dismiss_cooldown: float,
    combo_action_cooldown: float,
    spell_click_cooldown: float,
    wrinkler_action_cooldown: float,
    trade_action_cooldown: float,
    building_action_cooldown: float,
    dragon_action_cooldown: float,
    dragon_aura_action_cooldown: float,
    post_upgrade_wrinkler_cooldown_seconds: float,
    bonus_click_hold: float,
    trade_click_hold: float,
    building_stuck_attempt_limit: int,
    building_stuck_signature_suppress_seconds: float,
    upgrade_stuck_attempt_limit: int,
    upgrade_stuck_signature_suppress_seconds: float,
    store_scroll_wheel_multiplier: float,
    click_shimmer: Callable[..., Any],
    should_skip_wrath_shimmer: Callable[..., bool],
    format_shimmer_id_list: Callable[..., str],
    reset_shimmer_tracking: Callable[..., None],
    record_shimmer_outcome: Callable[..., None],
    record_shimmer_click_runtime: Callable[..., None],
    record_shimmer_collect_runtime: Callable[..., None],
    overlay_event_sender: Callable[..., None] | None = None,
    get_pending_hand_shimmer: Callable[[], Any],
    clear_pending_hand_shimmer: Callable[[], None],
    recent_shimmer_clicks: dict[Any, Any],
    shimmer_first_seen: dict[Any, Any],
    shimmer_click_attempts: dict[Any, Any],
    pending_shimmer_results: dict[Any, Any],
    shimmer_click_delay_seconds: float,
    shimmer_click_cooldown: float,
    combo_pending_getter: Callable[[], bool],
    overlay_click_delay_seconds: float = 1.0,
    dom_snapshot_preparer_cls: Callable[..., Any] = DomSnapshotPreparer,
    dom_diagnostics_builder_cls: Callable[..., Any] = DomDiagnosticsBuilder,
    dom_loop_cycle_preparer_cls: Callable[..., Any] = DomLoopCyclePreparer,
    dom_loop_feed_logger_cls: Callable[..., Any] = DomLoopFeedLogger,
    dom_action_executor_cls: Callable[..., Any] = DomActionExecutor,
    dom_action_planner_cls: Callable[..., Any] = DomActionPlanner,
    dom_attempt_tracker_cls: Callable[..., Any] = DomAttemptTracker,
    dom_stage_policy_cls: Callable[..., Any] = DomStagePolicy,
    dom_loop_late_stage_preparer_cls: Callable[..., Any] = DomLoopLateStagePreparer,
    dom_action_coordinator_cls: Callable[..., Any] = DomActionCoordinator,
    dom_loop_stage_runner_cls: Callable[..., Any] = DomLoopStageRunner,
    dom_loop_outcome_handler_cls: Callable[..., Any] = DomLoopOutcomeHandler,
    dom_shimmer_handler_cls: Callable[..., Any] = DomShimmerHandler,
    dom_loop_coordinator_cls: Callable[..., Any] = DomLoopCoordinator,
    dom_loop_state_bridge_cls: Callable[..., Any] = DomLoopStateBridge,
) -> DomLoopServiceFactory:
    return DomLoopServiceFactory(
        snapshot_preparer_builder=lambda: dom_snapshot_preparer_cls(
            load_feed_snapshot=load_feed_snapshot,
            update_latest_snapshot=update_latest_snapshot,
            extract_shimmers=extract_shimmers,
            extract_buffs=extract_buffs,
            extract_spell=extract_spell,
            get_latest_big_cookie=get_latest_big_cookie,
        ),
        diagnostics_builder_builder=lambda: dom_diagnostics_builder_cls(
            to_screen_point=to_screen_point,
            monotonic=monotonic,
            garden_get_diagnostics=garden_get_diagnostics,
            extract_lump_diag=extract_lump_diag,
            building_get_diagnostics=building_get_diagnostics,
            ascension_get_diagnostics=ascension_get_diagnostics,
            extract_upgrade_diag=extract_upgrade_diag,
            extract_dragon_diag=extract_dragon_diag,
            extract_golden_cookie_diag=extract_golden_cookie_diag,
            spell_get_diagnostics=spell_get_diagnostics,
            get_global_cookie_reserve=get_global_cookie_reserve,
            get_next_purchase_goal=get_next_purchase_goal,
            apply_building_burst_purchase_goal=apply_building_burst_purchase_goal,
            get_stock_buy_controls=get_stock_buy_controls,
            stock_trade_management_active=stock_trade_management_active,
            stock_get_diagnostics=stock_get_diagnostics,
            extract_bank_diag_disabled=extract_bank_diag_disabled,
            wrinkler_get_diagnostics=wrinkler_get_diagnostics,
            combo_get_diagnostics=combo_get_diagnostics,
            stock_get_runtime_stats=stock_get_runtime_stats,
            spell_get_runtime_stats=spell_get_runtime_stats,
            combo_get_runtime_stats=combo_get_runtime_stats,
            track_combo_run=track_combo_run,
            get_non_click_pause_reasons=get_non_click_pause_reasons,
            should_pause_stock_trading=should_pause_stock_trading,
            should_allow_non_click_actions_during_pause=should_allow_non_click_actions_during_pause,
            evaluate_upgrade_buff_window=evaluate_upgrade_buff_window,
            should_defer_stock_actions_for_upgrade=should_defer_stock_actions_for_upgrade,
            set_runtime=set_runtime,
        ),
        cycle_preparer_builder=lambda snapshot_preparer, diagnostics_builder: dom_loop_cycle_preparer_cls(
            snapshot_preparer=snapshot_preparer,
            diagnostics_builder=diagnostics_builder,
            should_pause_value_actions_during_clot=should_pause_value_actions_during_clot,
            perf_counter=perf_counter,
            monotonic=monotonic,
            record_profile_ms=record_profile_ms,
        ),
        feed_logger_builder=lambda: dom_loop_feed_logger_cls(
            log=log,
            monotonic=monotonic,
            feed_debug_log_interval=feed_debug_log_interval,
        ),
        action_executor_builder=lambda: dom_action_executor_cls(
            log=log,
            click_lock=click_lock,
            click=click,
            scroll=scroll,
            can_interact_with_game=can_interact_with_game,
            ui_owner_conflicts=ui_owner_conflicts,
            should_throttle_ui_action=should_throttle_ui_action,
            claim_ui_owner=claim_ui_owner,
            move_mouse=move_mouse,
            record_profile_ms=record_profile_ms,
            set_runtime=set_runtime,
            record_event=record_event,
            time_monotonic=time_monotonic,
            perf_counter=perf_counter,
            sleep=sleep,
            building_click_hold=building_click_hold,
            spell_click_hold=spell_click_hold,
            feed_poll_interval=feed_poll_interval,
            main_click_suppress_seconds=main_click_suppress_seconds,
            suppress_main_click_until_getter=suppress_main_click_until_getter,
            suppress_main_click_until_setter=suppress_main_click_until_setter,
        ),
        action_planner_builder=lambda: dom_action_planner_cls(
            plan_reset_store_to_default=plan_reset_store_to_default,
            plan_upgrade_buy=plan_upgrade_buy,
            get_wrinkler_action=get_wrinkler_action,
            get_desired_dragon_auras=get_desired_dragon_auras,
            plan_dragon_aura_action=plan_dragon_aura_action,
            is_dragon_aura_unlocked=is_dragon_aura_unlocked,
            get_ascension_action=get_ascension_action,
            plan_building_buy=plan_building_buy,
            plan_building_sell=plan_building_sell,
            get_trade_action=get_trade_action,
            get_building_action=get_building_action,
            has_cookies_after_reserve=has_cookies_after_reserve,
            plan_minigame_store_access=plan_minigame_store_access,
        ),
        attempt_tracker_builder=dom_attempt_tracker_cls,
        stage_policy_builder=dom_stage_policy_cls,
        late_stage_preparer_builder=lambda action_planner, attempt_tracker, stage_policy: dom_loop_late_stage_preparer_cls(
            action_planner=action_planner,
            attempt_tracker=attempt_tracker,
            stage_policy=stage_policy,
            update_upgrade_attempt_tracking=update_upgrade_attempt_tracking,
            build_upgrade_attempt_signature=build_upgrade_attempt_signature,
            should_defer_stock_actions_for_upgrade=should_defer_stock_actions_for_upgrade,
            has_cookies_after_reserve=has_cookies_after_reserve,
            to_screen_point=to_screen_point,
            upgrade_action_cooldown=upgrade_action_cooldown,
        ),
        action_coordinator_builder=dom_action_coordinator_cls,
        stage_runner_builder=lambda coordinator, action_executor, action_planner, attempt_tracker, stage_policy: dom_loop_stage_runner_cls(
            coordinator=coordinator,
            action_executor=action_executor,
            action_planner=action_planner,
            attempt_tracker=attempt_tracker,
            stage_policy=stage_policy,
            note_target_getter=note_target_getter,
            should_allow_garden_action=should_allow_garden_action,
            update_building_attempt_tracking=update_building_attempt_tracking,
            to_screen_point=to_screen_point,
            build_building_attempt_signature=build_building_attempt_signature,
            extract_building_target_debug=extract_building_target_debug,
            format_store_planner_context=format_store_planner_context,
            extract_upgrade_target_debug=extract_upgrade_target_debug,
            format_upgrade_planner_context=format_upgrade_planner_context,
            combo_controller=combo_controller,
            spell_controller=spell_controller,
            garden_controller=garden_controller,
            wrinkler_controller=wrinkler_controller,
            ascension_controller=ascension_controller,
            santa_controller=santa_controller,
            stock_trader=stock_trader,
            building_autobuyer=building_autobuyer,
            log=log,
            sleep=sleep,
            lump_action_cooldown=lump_action_cooldown,
            note_dismiss_cooldown=note_dismiss_cooldown,
            combo_action_cooldown=combo_action_cooldown,
            spell_click_cooldown=spell_click_cooldown,
            wrinkler_action_cooldown=wrinkler_action_cooldown,
            trade_action_cooldown=trade_action_cooldown,
            building_action_cooldown=building_action_cooldown,
            upgrade_action_cooldown=upgrade_action_cooldown,
            dragon_action_cooldown=dragon_action_cooldown,
            dragon_aura_action_cooldown=dragon_aura_action_cooldown,
            post_upgrade_wrinkler_cooldown_seconds=post_upgrade_wrinkler_cooldown_seconds,
            bonus_click_hold=bonus_click_hold,
            trade_click_hold=trade_click_hold,
            building_stuck_attempt_limit=building_stuck_attempt_limit,
            building_stuck_signature_suppress_seconds=building_stuck_signature_suppress_seconds,
            upgrade_stuck_attempt_limit=upgrade_stuck_attempt_limit,
            upgrade_stuck_signature_suppress_seconds=upgrade_stuck_signature_suppress_seconds,
            store_scroll_wheel_multiplier=store_scroll_wheel_multiplier,
            feed_poll_interval=feed_poll_interval,
        ),
        outcome_handler_builder=lambda: dom_loop_outcome_handler_cls(
            perf_counter=perf_counter,
            record_profile_ms=record_profile_ms,
            sleep=sleep,
            feed_poll_interval=feed_poll_interval,
        ),
        shimmer_handler_builder=lambda: dom_shimmer_handler_cls(
            log=log,
            click_lock=click_lock,
            click_shimmer=click_shimmer,
            can_interact_with_game=can_interact_with_game,
            sleep=sleep,
            monotonic=monotonic,
            perf_counter=perf_counter,
            record_profile_ms=record_profile_ms,
            should_skip_wrath_shimmer=should_skip_wrath_shimmer,
            format_shimmer_id_list=format_shimmer_id_list,
            reset_shimmer_tracking=reset_shimmer_tracking,
            record_shimmer_outcome=record_shimmer_outcome,
            record_event=record_event,
            record_shimmer_click_runtime=record_shimmer_click_runtime,
            record_shimmer_collect_runtime=record_shimmer_collect_runtime,
            overlay_event_sender=overlay_event_sender,
            get_pending_hand_shimmer=get_pending_hand_shimmer,
            clear_pending_hand_shimmer=clear_pending_hand_shimmer,
            recent_shimmer_clicks=recent_shimmer_clicks,
            shimmer_first_seen=shimmer_first_seen,
            shimmer_click_attempts=shimmer_click_attempts,
            pending_shimmer_results=pending_shimmer_results,
            main_click_suppress_seconds=main_click_suppress_seconds,
            bonus_click_hold=bonus_click_hold,
            feed_poll_interval=feed_poll_interval,
            shimmer_click_delay_seconds=shimmer_click_delay_seconds,
            shimmer_click_cooldown=shimmer_click_cooldown,
            overlay_click_delay_seconds=overlay_click_delay_seconds,
        ),
        coordinator_builder=lambda cycle_preparer, feed_logger, shimmer_handler, stage_runner, late_stage_preparer, outcome_handler: dom_loop_coordinator_cls(
            cycle_preparer=cycle_preparer,
            feed_logger=feed_logger,
            shimmer_handler=shimmer_handler,
            stage_runner=stage_runner,
            late_stage_preparer=late_stage_preparer,
            outcome_handler=outcome_handler,
            combo_pending_getter=combo_pending_getter,
            perf_counter=perf_counter,
        ),
        state_bridge_builder=dom_loop_state_bridge_cls,
    )
