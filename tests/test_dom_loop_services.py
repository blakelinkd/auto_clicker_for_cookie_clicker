import unittest
from types import SimpleNamespace

from clicker_bot.dom_loop_services import (
    DomLoopServiceFactory,
    build_default_dom_loop_service_factory,
)


class DomLoopServiceFactoryTests(unittest.TestCase):
    def test_lazy_getters_cache_services_and_share_dependencies(self):
        calls = []

        def build(name, **kwargs):
            calls.append(name)
            return SimpleNamespace(name=name, kwargs=kwargs)

        factory = DomLoopServiceFactory(
            snapshot_preparer_builder=lambda: build("snapshot_preparer"),
            diagnostics_builder_builder=lambda: build("diagnostics_builder"),
            cycle_preparer_builder=lambda snapshot_preparer, diagnostics_builder: build(
                "cycle_preparer",
                snapshot_preparer=snapshot_preparer,
                diagnostics_builder=diagnostics_builder,
            ),
            feed_logger_builder=lambda: build("feed_logger"),
            action_executor_builder=lambda: build("action_executor"),
            action_planner_builder=lambda: build("action_planner"),
            attempt_tracker_builder=lambda: build("attempt_tracker"),
            stage_policy_builder=lambda: build("stage_policy"),
            late_stage_preparer_builder=lambda action_planner, attempt_tracker, stage_policy: build(
                "late_stage_preparer",
                action_planner=action_planner,
                attempt_tracker=attempt_tracker,
                stage_policy=stage_policy,
            ),
            action_coordinator_builder=lambda: build("action_coordinator"),
            stage_runner_builder=lambda coordinator, action_executor, action_planner, attempt_tracker, stage_policy: build(
                "stage_runner",
                coordinator=coordinator,
                action_executor=action_executor,
                action_planner=action_planner,
                attempt_tracker=attempt_tracker,
                stage_policy=stage_policy,
            ),
            outcome_handler_builder=lambda: build("outcome_handler"),
            shimmer_handler_builder=lambda: build("shimmer_handler"),
            coordinator_builder=lambda cycle_preparer, feed_logger, shimmer_handler, stage_runner, late_stage_preparer, outcome_handler: build(
                "coordinator",
                cycle_preparer=cycle_preparer,
                feed_logger=feed_logger,
                shimmer_handler=shimmer_handler,
                stage_runner=stage_runner,
                late_stage_preparer=late_stage_preparer,
                outcome_handler=outcome_handler,
            ),
            state_bridge_builder=lambda: build("state_bridge"),
        )

        coordinator = factory.coordinator()
        self.assertIs(coordinator, factory.coordinator())
        self.assertIs(factory.state_bridge(), factory.state_bridge())

        stage_runner = factory.stage_runner()
        late_stage_preparer = factory.late_stage_preparer()
        self.assertIs(stage_runner.kwargs["attempt_tracker"], late_stage_preparer.kwargs["attempt_tracker"])
        self.assertIs(stage_runner.kwargs["action_planner"], late_stage_preparer.kwargs["action_planner"])
        self.assertEqual(calls.count("action_planner"), 1)
        self.assertEqual(calls.count("attempt_tracker"), 1)
        self.assertEqual(calls.count("stage_policy"), 1)
        self.assertEqual(calls.count("coordinator"), 1)
        self.assertEqual(calls.count("state_bridge"), 1)


class BuildDefaultDomLoopServiceFactoryTests(unittest.TestCase):
    def _build_factory(self):
        def noop(*args, **kwargs):
            return None

        def false(*args, **kwargs):
            return False

        def recorder(name):
            def _factory(*args, **kwargs):
                return SimpleNamespace(name=name, kwargs=kwargs)

            return _factory

        return build_default_dom_loop_service_factory(
            load_feed_snapshot=lambda: {},
            update_latest_snapshot=noop,
            extract_shimmers=lambda snapshot: [],
            extract_buffs=lambda snapshot: [],
            extract_spell=lambda snapshot: None,
            get_latest_big_cookie=lambda: None,
            to_screen_point=lambda *args: args,
            monotonic=lambda: 1.0,
            garden_get_diagnostics=lambda *args, **kwargs: {},
            extract_lump_diag=lambda *args, **kwargs: {},
            building_get_diagnostics=lambda *args, **kwargs: {},
            ascension_get_diagnostics=lambda *args, **kwargs: {},
            extract_upgrade_diag=lambda *args, **kwargs: {},
            extract_dragon_diag=lambda *args, **kwargs: {},
            extract_golden_cookie_diag=lambda *args, **kwargs: {},
            spell_get_diagnostics=lambda *args, **kwargs: {},
            get_global_cookie_reserve=lambda *args, **kwargs: {},
            get_next_purchase_goal=lambda *args, **kwargs: None,
            apply_building_burst_purchase_goal=lambda *args, **kwargs: None,
            get_stock_buy_controls=lambda *args, **kwargs: {},
            stock_trade_management_active=lambda: False,
            stock_get_diagnostics=lambda *args, **kwargs: {},
            extract_bank_diag_disabled=lambda *args, **kwargs: {},
            wrinkler_get_diagnostics=lambda *args, **kwargs: {},
            combo_get_diagnostics=lambda *args, **kwargs: {},
            stock_get_runtime_stats=lambda: {},
            spell_get_runtime_stats=lambda: {},
            combo_get_runtime_stats=lambda: {},
            track_combo_run=noop,
            get_non_click_pause_reasons=lambda *args, **kwargs: (),
            should_pause_stock_trading=false,
            should_allow_non_click_actions_during_pause=false,
            evaluate_upgrade_buff_window=lambda *args, **kwargs: {},
            should_defer_stock_actions_for_upgrade=false,
            set_runtime=noop,
            should_pause_value_actions_during_clot=false,
            perf_counter=lambda: 2.0,
            record_profile_ms=noop,
            feed_debug_log_interval=3.5,
            log=SimpleNamespace(info=noop, warning=noop, debug=noop),
            click_lock=object(),
            click=noop,
            scroll=noop,
            can_interact_with_game=false,
            ui_owner_conflicts=false,
            should_throttle_ui_action=false,
            claim_ui_owner=noop,
            move_mouse=noop,
            record_event=noop,
            time_monotonic=lambda: 4.0,
            sleep=noop,
            building_click_hold=0.1,
            spell_click_hold=0.2,
            feed_poll_interval=0.3,
            main_click_suppress_seconds=0.4,
            suppress_main_click_until_getter=lambda: 0.0,
            suppress_main_click_until_setter=noop,
            plan_reset_store_to_default=noop,
            plan_upgrade_buy=noop,
            get_wrinkler_action=noop,
            get_desired_dragon_auras=noop,
            plan_dragon_aura_action=noop,
            is_dragon_aura_unlocked=false,
            get_ascension_action=noop,
            plan_building_buy=noop,
            plan_building_sell=noop,
            get_trade_action=noop,
            get_building_action=noop,
            has_cookies_after_reserve=false,
            plan_minigame_store_access=noop,
            update_upgrade_attempt_tracking=noop,
            build_upgrade_attempt_signature=noop,
            upgrade_action_cooldown=0.5,
            note_target_getter=lambda: None,
            should_allow_garden_action=false,
            update_building_attempt_tracking=noop,
            build_building_attempt_signature=noop,
            extract_building_target_debug=noop,
            format_store_planner_context=lambda value: str(value),
            extract_upgrade_target_debug=noop,
            format_upgrade_planner_context=lambda value: str(value),
            combo_controller=object(),
            spell_controller=SimpleNamespace(get_pending_hand_shimmer=lambda: None, clear_pending_hand_shimmer=noop),
            garden_controller=object(),
            wrinkler_controller=object(),
            ascension_controller=object(),
            stock_trader=object(),
            building_autobuyer=object(),
            lump_action_cooldown=0.6,
            note_dismiss_cooldown=0.7,
            combo_action_cooldown=0.8,
            spell_click_cooldown=0.9,
            wrinkler_action_cooldown=1.0,
            trade_action_cooldown=1.1,
            building_action_cooldown=1.2,
            dragon_action_cooldown=1.3,
            dragon_aura_action_cooldown=1.4,
            post_upgrade_wrinkler_cooldown_seconds=1.5,
            bonus_click_hold=1.6,
            trade_click_hold=1.7,
            building_stuck_attempt_limit=2,
            building_stuck_signature_suppress_seconds=1.8,
            upgrade_stuck_attempt_limit=3,
            upgrade_stuck_signature_suppress_seconds=1.9,
            store_scroll_wheel_multiplier=2.0,
            click_shimmer=noop,
            should_skip_wrath_shimmer=false,
            format_shimmer_id_list=lambda *args, **kwargs: "",
            reset_shimmer_tracking=noop,
            record_shimmer_outcome=noop,
            record_shimmer_click_runtime=noop,
            record_shimmer_collect_runtime=noop,
            get_pending_hand_shimmer=lambda: None,
            clear_pending_hand_shimmer=noop,
            recent_shimmer_clicks={},
            shimmer_first_seen={},
            shimmer_click_attempts={},
            pending_shimmer_results={},
            shimmer_click_delay_seconds=2.1,
            shimmer_click_cooldown=2.2,
            combo_pending_getter=false,
            dom_snapshot_preparer_cls=recorder("snapshot_preparer"),
            dom_diagnostics_builder_cls=recorder("diagnostics_builder"),
            dom_loop_cycle_preparer_cls=recorder("cycle_preparer"),
            dom_loop_feed_logger_cls=recorder("feed_logger"),
            dom_action_executor_cls=recorder("action_executor"),
            dom_action_planner_cls=recorder("action_planner"),
            dom_attempt_tracker_cls=recorder("attempt_tracker"),
            dom_stage_policy_cls=recorder("stage_policy"),
            dom_loop_late_stage_preparer_cls=recorder("late_stage_preparer"),
            dom_action_coordinator_cls=recorder("action_coordinator"),
            dom_loop_stage_runner_cls=recorder("stage_runner"),
            dom_loop_outcome_handler_cls=recorder("outcome_handler"),
            dom_shimmer_handler_cls=recorder("shimmer_handler"),
            dom_loop_coordinator_cls=recorder("coordinator"),
            dom_loop_state_bridge_cls=recorder("state_bridge"),
        )

    def test_default_builder_wires_dependencies_through_lazy_graph(self):
        factory = self._build_factory()

        coordinator = factory.coordinator()
        cycle_preparer = factory.cycle_preparer()
        feed_logger = factory.feed_logger()
        stage_runner = factory.stage_runner()
        late_stage_preparer = factory.late_stage_preparer()

        self.assertIs(coordinator.kwargs["cycle_preparer"], cycle_preparer)
        self.assertIs(coordinator.kwargs["feed_logger"], feed_logger)
        self.assertIs(stage_runner.kwargs["action_planner"], late_stage_preparer.kwargs["action_planner"])
        self.assertIs(stage_runner.kwargs["attempt_tracker"], late_stage_preparer.kwargs["attempt_tracker"])
        self.assertEqual(feed_logger.kwargs["feed_debug_log_interval"], 3.5)
        self.assertIs(factory.state_bridge(), factory.state_bridge())


if __name__ == "__main__":
    unittest.main()
