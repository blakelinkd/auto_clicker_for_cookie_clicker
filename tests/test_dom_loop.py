import unittest
from types import SimpleNamespace

from clicker_bot.dom_loop import (
    BankDiagCache,
    DomActionExecutor,
    DomActionPlanner,
    DomAttemptTracker,
    DomStagePolicy,
    DomActionCoordinator,
    DomLoopLateStagePreparer,
    DomShimmerHandler,
    DomShimmerContext,
    DomLoopOutcomeHandler,
    DomLoopCoordinator,
    DomLoopCyclePreparer,
    DomLoopFeedLogger,
    DomLoopStageRunner,
    DomLoopStateBridge,
    DomLoopEarlyStageContext,
    DomLoopLateStageContext,
    DomLoopEarlyStageState,
    DomLoopLateStageState,
    DomLoopActionOutcome,
    BuildingStagePlan,
    DomLoopCycleState,
    DomLoopState,
    DomLoopDiagnostics,
    MinigameStorePlan,
    AscensionStagePlan,
    DomDiagnosticsBuilder,
    DomLoopBuildOptions,
    DomSnapshotPreparer,
    PreparedSnapshot,
    UpgradeStagePlan,
)


class DomSnapshotPreparerTests(unittest.TestCase):
    def test_prepare_annotates_snapshot_and_collects_top_level_state(self):
        calls = []
        snapshot = {"cookies": 123.0}
        preparer = DomSnapshotPreparer(
            load_feed_snapshot=lambda: snapshot,
            update_latest_snapshot=lambda value: calls.append(("update_latest_snapshot", value)),
            extract_shimmers=lambda value: [{"id": 1}] if value is snapshot else [],
            extract_buffs=lambda value: [{"name": "Frenzy"}] if value is snapshot else [],
            extract_spell=lambda value: {"ready": True, "on_minigame": False} if value is snapshot else None,
            get_latest_big_cookie=lambda: {"client_x": 10, "client_y": 20},
        )

        prepared = preparer.prepare(
            building_autobuy_enabled=True,
            lucky_reserve_enabled=False,
        )

        self.assertEqual(prepared.shimmers, [{"id": 1}])
        self.assertEqual(prepared.buffs, [{"name": "Frenzy"}])
        self.assertEqual(prepared.spell, {"ready": True, "on_minigame": False})
        self.assertEqual(prepared.big_cookie, {"client_x": 10, "client_y": 20})
        self.assertTrue(snapshot["_building_autobuy_enabled"])
        self.assertFalse(snapshot["_lucky_reserve_enabled"])
        self.assertEqual(calls, [("update_latest_snapshot", snapshot)])


class DomDiagnosticsBuilderTests(unittest.TestCase):
    def _builder(self, set_runtime):
        return DomDiagnosticsBuilder(
            to_screen_point=lambda x, y: (x, y),
            monotonic=lambda: 50.0,
            garden_get_diagnostics=lambda snapshot, to_screen: {"reason": "garden_ready"},
            extract_lump_diag=lambda snapshot, to_screen: {"reason": "lump_wait", "stage": "ripe"},
            building_get_diagnostics=lambda snapshot, to_screen: {"reason": "building_ready", "cookies": 500.0, "reserve": 50.0},
            ascension_get_diagnostics=lambda snapshot: {"reason": "ascension_idle"},
            extract_upgrade_diag=lambda snapshot: {"reason": "upgrade_ready", "candidate": "Kitten"},
            extract_dragon_diag=lambda snapshot, to_screen: {"reason": "dragon_ready", "next_action": "Train"},
            extract_golden_cookie_diag=lambda snapshot: {"reason": "golden_none"},
            spell_get_diagnostics=lambda snapshot, to_screen, building_diag=None: {"reason": "spell_idle", "candidate": "FoF"},
            get_global_cookie_reserve=lambda snapshot, garden_diag, **kwargs: {
                "garden_reserve": 10.0,
                "lucky_reserve": 20.0,
                "hard_lucky_reserve": 30.0,
                "live_lucky_reserve": 40.0,
                "soft_lucky_delta": 5.0,
                "total_reserve": 60.0,
                "building_total_reserve": 70.0,
                "burst_window": 8.0,
            },
            get_next_purchase_goal=lambda snapshot, **kwargs: {"kind": "upgrade", "name": "Kitten"},
            apply_building_burst_purchase_goal=lambda snapshot, building_diag, purchase_goal, burst_window: purchase_goal,
            get_stock_buy_controls=lambda building_diag, enabled, reserve: {
                "allow_buy_actions": False,
                "buy_reserve_cookies": 125.0,
            },
            stock_trade_management_active=lambda: True,
            stock_get_diagnostics=lambda snapshot, to_screen, **kwargs: {
                "reason": "buy_ready",
                "cookies": 500.0,
                "buy_candidate": "Sugar",
            },
            extract_bank_diag_disabled=lambda snapshot: {"reason": "stock_disabled"},
            wrinkler_get_diagnostics=lambda snapshot, to_screen, pop_goal=None: {"reason": "wrinkler_idle", "candidate_id": 3},
            combo_get_diagnostics=lambda snapshot, to_screen: {"reason": "combo_idle", "candidate_building": None, "candidate_quantity": None},
            stock_get_runtime_stats=lambda: {"profile": {"ticks": 1}, "db_profile": {"writes": 2}},
            spell_get_runtime_stats=lambda: {"casts": 4},
            combo_get_runtime_stats=lambda: {"pending_phase": "idle"},
            track_combo_run=lambda snapshot, buffs, spell_stats, combo_stats: None,
            get_non_click_pause_reasons=lambda buffs, **kwargs: ("buff_pause",),
            should_pause_stock_trading=lambda buffs: True,
            should_allow_non_click_actions_during_pause=lambda snapshot, reasons: False,
            evaluate_upgrade_buff_window=lambda snapshot, buffs, upgrade_diag, reasons: {
                "allow_during_pause": True,
                "buff_window_seconds": 12.0,
                "estimated_delta_cps": 1.5,
                "estimated_window_gain": 18.0,
                "reason": "buff_window",
            },
            should_defer_stock_actions_for_upgrade=lambda snapshot, upgrade_diag, **kwargs: True,
            set_runtime=set_runtime,
        )

    def test_build_decorates_diagnostics_and_applies_pause_flags(self):
        runtime_updates = []
        builder = self._builder(lambda **kwargs: runtime_updates.append(kwargs))
        prepared = PreparedSnapshot(
            snapshot={"_age": 0.25, "profile": {"fps": 30}, "shimmerTelemetry": {}, "ascension": {}},
            shimmers=[{"id": 1, "wrath": False}],
            buffs=[{"name": "Frenzy"}],
            spell={"ready": True, "on_minigame": False},
            big_cookie={"client_x": 10, "client_y": 20},
        )
        options = DomLoopBuildOptions(
            building_autobuy_enabled=True,
            lucky_reserve_enabled=True,
            stock_trading_enabled=False,
            upgrade_autobuy_enabled=True,
            ascension_prep_enabled=False,
            garden_automation_enabled=True,
            stock_diag_refresh_interval=3.0,
        )

        diagnostics, cache = builder.build(prepared, BankDiagCache(), options)
        builder.publish_runtime(prepared, diagnostics, options)

        self.assertEqual(cache.diag["reason"], "buy_ready")
        self.assertEqual(diagnostics.bank_diag["reason"], "paused_for_production_buff")
        self.assertFalse(diagnostics.bank_diag["enabled"])
        self.assertEqual(diagnostics.bank_diag["buy_cookies_available"], 375.0)
        self.assertEqual(diagnostics.building_diag["reserve"], 70.0)
        self.assertEqual(diagnostics.building_diag["spendable"], 430.0)
        self.assertEqual(diagnostics.upgrade_diag["pause_reasons"], ("buff_pause",))
        self.assertTrue(diagnostics.defer_stock_for_upgrade)
        self.assertEqual(runtime_updates[0]["last_trade_action"] if "last_trade_action" in runtime_updates[0] else None, None)
        self.assertEqual(runtime_updates[0]["stock_profile"], {"ticks": 1})

    def test_build_reuses_cached_bank_diag_until_refresh_interval(self):
        calls = []
        builder = DomDiagnosticsBuilder(
            to_screen_point=lambda x, y: (x, y),
            monotonic=lambda: 11.0,
            garden_get_diagnostics=lambda snapshot, to_screen: {},
            extract_lump_diag=lambda snapshot, to_screen: {},
            building_get_diagnostics=lambda snapshot, to_screen: {"cookies": 100.0, "reserve": 0.0},
            ascension_get_diagnostics=lambda snapshot: {},
            extract_upgrade_diag=lambda snapshot: {},
            extract_dragon_diag=lambda snapshot, to_screen: {},
            extract_golden_cookie_diag=lambda snapshot: {},
            spell_get_diagnostics=lambda snapshot, to_screen, building_diag=None: {},
            get_global_cookie_reserve=lambda snapshot, garden_diag, **kwargs: {
                "garden_reserve": 0.0,
                "lucky_reserve": 0.0,
                "hard_lucky_reserve": 0.0,
                "live_lucky_reserve": 0.0,
                "soft_lucky_delta": 0.0,
                "total_reserve": 0.0,
                "building_total_reserve": 0.0,
                "burst_window": 0.0,
            },
            get_next_purchase_goal=lambda snapshot, **kwargs: None,
            apply_building_burst_purchase_goal=lambda snapshot, building_diag, purchase_goal, burst_window: purchase_goal,
            get_stock_buy_controls=lambda building_diag, enabled, reserve: {
                "allow_buy_actions": True,
                "buy_reserve_cookies": 10.0,
            },
            stock_trade_management_active=lambda: True,
            stock_get_diagnostics=lambda snapshot, to_screen, **kwargs: calls.append("refresh") or {"reason": "buy_ready", "cookies": 20.0},
            extract_bank_diag_disabled=lambda snapshot: {"reason": "disabled"},
            wrinkler_get_diagnostics=lambda snapshot, to_screen, pop_goal=None: {},
            combo_get_diagnostics=lambda snapshot, to_screen: {},
            stock_get_runtime_stats=lambda: {},
            spell_get_runtime_stats=lambda: {},
            combo_get_runtime_stats=lambda: {},
            track_combo_run=lambda snapshot, buffs, spell_stats, combo_stats: None,
            get_non_click_pause_reasons=lambda buffs, **kwargs: (),
            should_pause_stock_trading=lambda buffs: False,
            should_allow_non_click_actions_during_pause=lambda snapshot, reasons: False,
            evaluate_upgrade_buff_window=lambda snapshot, buffs, upgrade_diag, reasons: {},
            should_defer_stock_actions_for_upgrade=lambda snapshot, upgrade_diag, **kwargs: False,
            set_runtime=lambda **kwargs: None,
        )
        prepared = PreparedSnapshot(
            snapshot={},
            shimmers=[],
            buffs=[],
            spell=None,
            big_cookie=None,
        )
        options = DomLoopBuildOptions(
            building_autobuy_enabled=False,
            lucky_reserve_enabled=False,
            stock_trading_enabled=True,
            upgrade_autobuy_enabled=False,
            ascension_prep_enabled=False,
            garden_automation_enabled=True,
            stock_diag_refresh_interval=3.0,
        )

        diagnostics, cache = builder.build(
            prepared,
            BankDiagCache(diag={"reason": "cached", "cookies": 55.0}, captured_at=10.0),
            options,
        )

        self.assertEqual(calls, [])
        self.assertEqual(cache.diag["reason"], "cached")
        self.assertEqual(diagnostics.bank_diag["buy_cookies_available"], 45.0)


class DomLoopCyclePreparerTests(unittest.TestCase):
    def test_prepare_cycle_builds_bundle_and_records_profiles(self):
        prepared = PreparedSnapshot(
            snapshot={"_age": 0.25},
            shimmers=[{"id": 1, "wrath": False}],
            buffs=[{"name": "Clot"}],
            spell={"ready": True, "on_minigame": False},
            big_cookie={"client_x": 1, "client_y": 2},
        )
        diagnostics = DomLoopDiagnostics(
            garden_diag={},
            lump_diag={},
            building_diag={},
            ascension_prep_diag={},
            upgrade_diag={},
            dragon_diag={},
            santa_diag={},
            golden_diag={},
            spell_diag={},
            reserve_budget={},
            purchase_goal=None,
            stock_buy_controls={},
            stock_management_active=False,
            bank_diag={},
            wrinkler_diag={},
            combo_diag={},
            trade_stats={},
            spell_stats={},
            combo_stats={},
            pause_reasons=(),
            pause_non_click_actions=False,
            pause_stock_trading=False,
            allow_non_click_actions_during_pause=False,
            defer_stock_for_upgrade=False,
        )
        perf_values = iter((10.0, 10.2, 11.0, 11.4))
        profile_calls = []
        publish_calls = []
        preparer = DomLoopCyclePreparer(
            snapshot_preparer=SimpleNamespace(
                prepare=lambda **kwargs: prepared,
            ),
            diagnostics_builder=SimpleNamespace(
                build=lambda prepared_value, cache, options: (diagnostics, BankDiagCache(diag={"reason": "cached"}, captured_at=4.0)),
                publish_runtime=lambda prepared_value, diagnostics_value, options: publish_calls.append((prepared_value, diagnostics_value, options)),
            ),
            should_pause_value_actions_during_clot=lambda buffs: True,
            perf_counter=lambda: next(perf_values),
            monotonic=lambda: 50.0,
            record_profile_ms=lambda prefix, elapsed_ms, spike_ms=None: profile_calls.append((prefix, round(elapsed_ms, 1), spike_ms)),
        )
        options = DomLoopBuildOptions(
            building_autobuy_enabled=True,
            lucky_reserve_enabled=False,
            stock_trading_enabled=False,
            upgrade_autobuy_enabled=True,
            ascension_prep_enabled=False,
            garden_automation_enabled=True,
            stock_diag_refresh_interval=3.0,
        )

        cycle = preparer.prepare_cycle(
            build_options=options,
            bank_diag_cache=BankDiagCache(),
        )

        self.assertIs(cycle.prepared, prepared)
        self.assertIs(cycle.diagnostics, diagnostics)
        self.assertEqual(cycle.bank_diag_cache.diag, {"reason": "cached"})
        self.assertEqual(cycle.now, 50.0)
        self.assertTrue(cycle.pause_value_actions_during_clot)
        self.assertEqual(profile_calls, [("dom_extract", 200.0, 20.0), ("dom_diag", 400.0, 25.0)])
        self.assertEqual(len(publish_calls), 1)


class DomLoopFeedLoggerTests(unittest.TestCase):
    def test_log_if_changed_logs_and_updates_signature_timestamp(self):
        log = _LogStub()
        logger = DomLoopFeedLogger(
            log=log,
            monotonic=lambda: 25.0,
            feed_debug_log_interval=2.0,
        )
        prepared = PreparedSnapshot(
            snapshot={"_age": 0.25},
            shimmers=[{"id": 1, "wrath": False}],
            buffs=[],
            spell={"ready": True, "on_minigame": False, "client_x": 10, "client_y": 20},
            big_cookie={"client_x": 1, "client_y": 2},
        )
        diagnostics = DomLoopDiagnostics(
            garden_diag={"reason": "garden_ready"},
            lump_diag={"reason": "lump_wait"},
            building_diag={"reason": "building_ready"},
            ascension_prep_diag={"reason": "ascension_idle"},
            upgrade_diag={"reason": "upgrade_ready"},
            dragon_diag={"reason": "dragon_ready"},
            santa_diag={},
            golden_diag={},
            spell_diag={"reason": "spell_idle"},
            reserve_budget={},
            purchase_goal=None,
            stock_buy_controls={},
            stock_management_active=False,
            bank_diag={"reason": "bank_idle"},
            wrinkler_diag={"reason": "wrinkler_idle"},
            combo_diag={"reason": "combo_idle"},
            trade_stats={},
            spell_stats={},
            combo_stats={},
            pause_reasons=(),
            pause_non_click_actions=False,
            pause_stock_trading=False,
            allow_non_click_actions_during_pause=False,
            defer_stock_for_upgrade=False,
        )

        signature, logged_at = logger.log_if_changed(
            prepared=prepared,
            diagnostics=diagnostics,
            last_feed_signature=None,
            last_feed_debug_at=0.0,
        )

        self.assertEqual(logged_at, 25.0)
        self.assertIsNotNone(signature)
        self.assertTrue(any(level == "debug" and "dom_feed:" in message for level, message in log.messages))

    def test_log_if_changed_skips_when_signature_unchanged(self):
        log = _LogStub()
        logger = DomLoopFeedLogger(
            log=log,
            monotonic=lambda: 25.0,
            feed_debug_log_interval=2.0,
        )
        prepared = PreparedSnapshot(snapshot={}, shimmers=[], buffs=[], spell=None, big_cookie=None)
        diagnostics = DomLoopDiagnostics(
            garden_diag={},
            lump_diag={},
            building_diag={},
            ascension_prep_diag={},
            upgrade_diag={},
            dragon_diag={},
            santa_diag={},
            golden_diag={},
            spell_diag={},
            reserve_budget={},
            purchase_goal=None,
            stock_buy_controls={},
            stock_management_active=False,
            bank_diag={},
            wrinkler_diag={},
            combo_diag={},
            trade_stats={},
            spell_stats={},
            combo_stats={},
            pause_reasons=(),
            pause_non_click_actions=False,
            pause_stock_trading=False,
            allow_non_click_actions_during_pause=False,
            defer_stock_for_upgrade=False,
        )
        initial_signature = DomDiagnosticsBuilder.build_feed_signature(prepared, diagnostics)

        signature, logged_at = logger.log_if_changed(
            prepared=prepared,
            diagnostics=diagnostics,
            last_feed_signature=initial_signature,
            last_feed_debug_at=24.5,
        )

        self.assertEqual(signature, initial_signature)
        self.assertEqual(logged_at, 24.5)
        self.assertEqual(log.messages, [])


class _NullLock:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False


class _Recorder:
    def __init__(self):
        self.actions = []

    def record_action(self, action):
        self.actions.append(action)


class _LogStub:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(("info", message))

    def debug(self, message):
        self.messages.append(("debug", message))

    def warning(self, message):
        self.messages.append(("warning", message))


class DomActionExecutorTests(unittest.TestCase):
    def _executor(self, *, can_interact=lambda now: True, ui_conflict=lambda owner, now: False, throttle=lambda kind, x, y, now: False):
        calls = {
            "clicks": [],
            "scrolls": [],
            "claims": [],
            "runtime": [],
            "events": [],
            "profiles": [],
            "sleep": [],
            "suppress": 0.0,
        }
        log = _LogStub()
        executor = DomActionExecutor(
            log=log,
            click_lock=_NullLock(),
            click=lambda x, y, **kwargs: calls["clicks"].append((x, y, kwargs)),
            scroll=lambda x, y, steps: calls["scrolls"].append((x, y, steps)),
            can_interact_with_game=can_interact,
            ui_owner_conflicts=ui_conflict,
            should_throttle_ui_action=throttle,
            claim_ui_owner=lambda owner, now: calls["claims"].append((owner, now)),
            move_mouse=lambda *args, **kwargs: calls.setdefault("moves", []).append((args, kwargs)),
            record_profile_ms=lambda prefix, elapsed_ms, spike_ms=None: calls["profiles"].append((prefix, spike_ms)),
            set_runtime=lambda **kwargs: calls["runtime"].append(kwargs),
            record_event=lambda message: calls["events"].append(message),
            time_monotonic=lambda: 123.0,
            perf_counter=lambda: 10.5,
            sleep=lambda seconds: calls["sleep"].append(seconds),
            building_click_hold=0.02,
            spell_click_hold=0.03,
            feed_poll_interval=0.08,
            main_click_suppress_seconds=0.30,
            suppress_main_click_until_getter=lambda: calls["suppress"],
            suppress_main_click_until_setter=lambda value: calls.__setitem__("suppress", value),
        )
        return executor, calls, log

    def test_execute_lump_action_clicks_and_records_runtime(self):
        executor, calls, _ = self._executor()

        action_at = executor.execute_lump_action(
            {"screen_x": 10, "screen_y": 20, "stage": "ripe", "current_type_name": "normal", "lumps": 3},
            now=5.0,
        )

        self.assertEqual(action_at, 123.0)
        self.assertEqual(calls["clicks"], [(10, 20, {"hold": 0.02})])
        self.assertEqual(calls["runtime"], [{"last_lump_action": "harvest normal (ripe)"}])
        self.assertEqual(calls["events"], ["Sugar lump harvest normal stage=ripe"])
        self.assertEqual(calls["sleep"], [0.08])
        self.assertEqual(calls["suppress"], 5.3)

    def test_execute_spell_action_respects_ui_gates(self):
        executor, calls, _ = self._executor(ui_conflict=lambda owner, now: True)

        action_at = executor.execute_spell_action(
            SimpleNamespace(kind="open_grimoire", screen_x=1, screen_y=2, magic=10.0, max_magic=20.0),
            now=5.0,
            action_started=10.0,
            spell_recorder=_Recorder(),
        )

        self.assertIsNone(action_at)
        self.assertEqual(calls["clicks"], [])
        self.assertEqual(calls["sleep"], [0.08])

    def test_execute_combo_action_scrolls_and_updates_runtime(self):
        executor, calls, _ = self._executor()
        recorder = _Recorder()

        action_at = executor.execute_combo_action(
            SimpleNamespace(
                kind="scroll_store",
                building_name="Cursor",
                quantity=100,
                detail="prep",
                screen_x=30,
                screen_y=40,
                scroll_steps=-2,
            ),
            now=6.0,
            action_started=10.0,
            combo_recorder=recorder,
        )

        self.assertEqual(action_at, 123.0)
        self.assertEqual(calls["scrolls"], [(30, 40, -2)])
        self.assertEqual(calls["runtime"], [{"last_combo_action": "prep Cursor"}])
        self.assertEqual(len(recorder.actions), 1)

    def test_execute_garden_action_clicks_and_claims_ui_owner(self):
        executor, calls, _ = self._executor()
        recorder = _Recorder()

        handled = executor.execute_garden_action(
            SimpleNamespace(kind="open_garden", detail="open", screen_x=11, screen_y=22),
            now=7.0,
            action_started=10.0,
            garden_recorder=recorder,
        )

        self.assertTrue(handled)
        self.assertEqual(calls["claims"], [("garden", 7.0)])
        self.assertEqual(calls["events"], ["Garden action open"])
        self.assertEqual(calls["clicks"], [(11, 22, {"hold": 0.02})])

    def test_execute_trade_action_clicks_and_updates_runtime(self):
        executor, calls, _ = self._executor()
        recorder = _Recorder()

        action_at = executor.execute_trade_action(
            SimpleNamespace(kind="buy", good_name="Sugar", good_id=7, price=12.5, screen_x=15, screen_y=16),
            now=8.0,
            action_started=10.0,
            stock_recorder=recorder,
            trade_click_hold=0.04,
        )

        self.assertEqual(action_at, 123.0)
        self.assertEqual(calls["claims"], [("bank", 8.0)])
        self.assertEqual(calls["clicks"], [(15, 16, {"hold": 0.04})])
        self.assertEqual(calls["runtime"], [{"last_trade_action": "buy Sugar"}])

    def test_execute_upgrade_action_updates_focus_state(self):
        executor, calls, _ = self._executor()
        result = executor.execute_upgrade_action(
            now=9.0,
            action_started=10.0,
            snapshot={"_age": 0.2, "store": {"buyMode": 1, "buyBulk": 1}},
            upgrade_diag={"candidate": "Kitten", "candidate_id": 3, "candidate_price": 250.0},
            upgrade_action=SimpleNamespace(kind="focus_store_section", screen_x=21, screen_y=22, planner_context=None),
            upgrade_store_action=None,
            upgrade_signature=("kitten",),
            last_upgrade_focus_signature=None,
            last_upgrade_focus_at=0.0,
            last_upgrade_focus_point=None,
            upgrade_attempt_tracker={"attempts": 0},
            upgrade_stuck_attempt_limit=4,
            upgrade_stuck_signature_suppress_seconds=60.0,
            post_upgrade_wrinkler_cooldown_seconds=3.0,
            extract_upgrade_target_debug=lambda snapshot, candidate_id: {},
            format_upgrade_planner_context=lambda context: "",
        )

        self.assertEqual(result["action_at"], 123.0)
        self.assertEqual(result["last_upgrade_focus_signature"], ("kitten",))
        self.assertEqual(result["last_upgrade_focus_point"], (21, 22))
        self.assertEqual(calls["moves"], [((21, 22), {})])
        self.assertEqual(calls["runtime"], [{"last_trade_action": "focus upgrades Kitten"}])

    def test_execute_building_action_updates_attempt_tracker(self):
        executor, calls, _ = self._executor()
        recorder = _Recorder()
        tracker = {"attempts": 0}

        action_at = executor.execute_building_action(
            building_action=SimpleNamespace(
                building_name="Cursor",
                building_id=1,
                price=15.0,
                quantity=1,
                delta_cps=0.5,
                payback_seconds=30.0,
            ),
            store_action=SimpleNamespace(
                kind="click_building",
                current_store_mode=1,
                store_mode=1,
                current_store_bulk=1,
                store_bulk=1,
                screen_x=31,
                screen_y=32,
                planner_context=None,
            ),
            snapshot={"_age": 0.3},
            now=10.0,
            action_started=10.0,
            building_signature=("cursor",),
            building_attempt_tracker=tracker,
            building_stuck_attempt_limit=4,
            building_stuck_signature_suppress_seconds=30.0,
            building_recorder=recorder,
            extract_building_target_debug=lambda snapshot, building_id: {},
            format_store_planner_context=lambda context: "",
            store_scroll_wheel_multiplier=12,
        )

        self.assertEqual(action_at, 123.0)
        self.assertEqual(tracker["candidate_id"], 1)
        self.assertEqual(tracker["candidate_signature"], ("cursor",))
        self.assertEqual(tracker["attempts"], 1)
        self.assertEqual(calls["claims"], [("building_store", 10.0)])
        self.assertEqual(calls["runtime"], [{"last_building_action": "Cursor"}])


class DomActionPlannerTests(unittest.TestCase):
    def _planner(self, **overrides):
        defaults = {
            "plan_reset_store_to_default": lambda snapshot, to_screen: SimpleNamespace(kind="set_store_mode"),
            "plan_upgrade_buy": lambda snapshot, to_screen, candidate_id: SimpleNamespace(kind="click_upgrade", candidate_id=candidate_id),
            "get_wrinkler_action": lambda snapshot, to_screen, **kwargs: SimpleNamespace(kind="pop", wrinkler_id=3),
            "get_desired_dragon_auras": lambda combo_diag, spell_diag=None: {"primary_id": 5, "secondary_id": 9},
            "plan_dragon_aura_action": lambda dragon_diag, combo_diag, spell_diag=None: None,
            "is_dragon_aura_unlocked": lambda level, aura_id: True,
            "get_ascension_action": lambda snapshot, now=None: None,
            "plan_building_buy": lambda snapshot, to_screen, building_id, quantity=1: SimpleNamespace(kind="click_building", building_id=building_id, quantity=quantity),
            "plan_building_sell": lambda snapshot, to_screen, building_id, quantity=1: SimpleNamespace(kind="click_building", building_id=building_id, quantity=quantity),
            "get_trade_action": lambda snapshot, to_screen, **kwargs: SimpleNamespace(kind="buy", good_id=7),
            "get_building_action": lambda snapshot, to_screen, now=None: None,
            "has_cookies_after_reserve": lambda snapshot, price, reserve: True,
            "plan_minigame_store_access": lambda snapshot, spell_diag, bank_diag, garden_diag: ("bank", SimpleNamespace(kind="open_bank")),
        }
        defaults.update(overrides)
        return DomActionPlanner(**defaults)

    def test_plan_upgrade_returns_store_reset_when_store_not_default(self):
        planner = self._planner()

        plan = planner.plan_upgrade(
            snapshot={"store": {"buyMode": 10, "buyBulk": 100}},
            to_screen_point=lambda x, y: (x, y),
            upgrade_diag={"candidate_can_buy": True, "candidate_id": 4, "candidate_price": 200.0},
            global_cookie_reserve=50.0,
        )

        self.assertIsNone(plan.upgrade_action)
        self.assertEqual(plan.upgrade_store_action.kind, "set_store_mode")

    def test_plan_dragon_keeps_non_aura_actions_when_aura_planning_disabled(self):
        planner = self._planner(
            plan_dragon_aura_action=lambda dragon_diag, combo_diag, spell_diag=None: {"kind": "set_aura"},
        )

        action = planner.plan_dragon(
            dragon_diag={
                "available": True,
                "open": False,
                "actionable": True,
                "open_target": {"screen_x": 10, "screen_y": 20},
            },
            combo_diag={},
            spell_diag={"reactive_combo_stack": False, "valuable_buffs": False},
            allow_aura_actions=False,
        )

        self.assertEqual(action["kind"], "open_dragon")

    def test_plan_building_returns_store_action_and_blocked_signature(self):
        action = SimpleNamespace(kind="buy_building", building_id=2, quantity=5)
        planner = self._planner(
            get_building_action=lambda snapshot, to_screen, now=None: action,
        )

        plan = planner.plan_building(
            snapshot={},
            to_screen_point=lambda x, y: (x, y),
            now=10.0,
            building_diag={"next_candidate_price": 123.0},
            building_cookie_reserve=40.0,
            build_signature=lambda value: ("sig", getattr(value, "building_id", None)),
            blocked_signature=("sig", 2),
            blocked_until=11.0,
        )

        self.assertEqual(plan.store_action.kind, "click_building")
        self.assertEqual(plan.signature, ("sig", 2))
        self.assertTrue(plan.signature_blocked)

    def test_plan_minigame_store_access_wraps_owner_and_action(self):
        planner = self._planner()

        plan = planner.plan_minigame_store_access(
            snapshot={},
            spell_diag={},
            bank_diag={},
            garden_diag={},
        )

        self.assertEqual(plan.owner, "bank")
        self.assertEqual(plan.store_action.kind, "open_bank")


class DomAttemptTrackerTests(unittest.TestCase):
    def test_sync_tracker_keeps_stuck_block_when_signature_matches(self):
        tracker = {
            "candidate_id": 11,
            "attempts": 4,
            "blocked_until": 10.0,
            "candidate_signature": ("sig", 11),
            "blocked_signature": ("sig", 11),
        }

        DomAttemptTracker.sync_tracker(
            tracker,
            candidate_id=11,
            candidate_signature=("sig", 11),
            now=20.0,
        )

        self.assertEqual(tracker["blocked_signature"], ("sig", 11))
        self.assertEqual(tracker["blocked_until"], 10.0)
        self.assertEqual(tracker["attempts"], 4)

    def test_sync_tracker_clears_stuck_block_when_signature_changes(self):
        tracker = {
            "candidate_id": 11,
            "attempts": 4,
            "blocked_until": 10.0,
            "candidate_signature": ("sig", 11),
            "blocked_signature": ("sig", 11),
        }

        DomAttemptTracker.sync_tracker(
            tracker,
            candidate_id=11,
            candidate_signature=("sig", 12),
            now=20.0,
        )

        self.assertIsNone(tracker["blocked_signature"])
        self.assertEqual(tracker["blocked_until"], 0.0)
        self.assertEqual(tracker["attempts"], 0)

    def test_is_signature_blocked_checks_active_backoff(self):
        tracker = {
            "candidate_id": 6,
            "attempts": 4,
            "blocked_until": 11.0,
            "candidate_signature": ("sig", 6),
            "blocked_signature": ("sig", 6),
        }

        self.assertTrue(
            DomAttemptTracker.is_signature_blocked(
                tracker,
                candidate_signature=("sig", 6),
                now=10.0,
            )
        )
        self.assertFalse(
            DomAttemptTracker.is_signature_blocked(
                tracker,
                candidate_signature=("sig", 6),
                now=12.0,
            )
        )

    def test_log_upgrade_blockers_deduplicates_repeated_signature(self):
        log = _LogStub()
        snapshot = {"cookies": 1000.0, "store": {"buyMode": 10, "buyBulk": 100}}
        upgrade_diag = {
            "candidate_id": 11,
            "candidate": "Fertilizer",
            "candidate_price": 55000.0,
        }
        blockers = ["cooldown_remaining=0.250s", "plan_buy_returned_none"]

        signature = DomAttemptTracker.log_upgrade_blockers(
            log=log,
            last_signature=None,
            snapshot=snapshot,
            upgrade_diag=upgrade_diag,
            blockers=blockers,
        )
        repeated = DomAttemptTracker.log_upgrade_blockers(
            log=log,
            last_signature=signature,
            snapshot=snapshot,
            upgrade_diag=upgrade_diag,
            blockers=blockers,
        )

        self.assertEqual(signature, repeated)
        self.assertEqual(len(log.messages), 1)
        self.assertIn("Upgrade candidate blocked", log.messages[0][1])


class DomStagePolicyTests(unittest.TestCase):
    def test_can_plan_upgrade_requires_open_gate_and_cooldown(self):
        allowed = DomStagePolicy.can_plan_upgrade(
            upgrade_autobuy_enabled=True,
            pause_non_click_actions=False,
            allow_upgrade_during_pause=False,
            combo_pending=False,
            shimmers_present=False,
            upgrade_signature_blocked=False,
            now=10.0,
            upgrade_blocked_until=5.0,
            last_upgrade_action=9.0,
            upgrade_action_cooldown=0.5,
            upgrade_diag={"candidate_can_buy": True, "candidate_id": 4},
        )
        blocked = DomStagePolicy.can_plan_upgrade(
            upgrade_autobuy_enabled=True,
            pause_non_click_actions=False,
            allow_upgrade_during_pause=False,
            combo_pending=False,
            shimmers_present=False,
            upgrade_signature_blocked=False,
            now=10.0,
            upgrade_blocked_until=5.0,
            last_upgrade_action=9.8,
            upgrade_action_cooldown=0.5,
            upgrade_diag={"candidate_can_buy": True, "candidate_id": 4},
        )

        self.assertTrue(allowed)
        self.assertFalse(blocked)

    def test_build_upgrade_blockers_collects_pause_reserve_and_cooldown_reasons(self):
        blockers = DomStagePolicy.build_upgrade_blockers(
            upgrade_autobuy_enabled=False,
            pause_non_click_actions=True,
            pause_reasons=("buff_pause",),
            allow_upgrade_during_pause=False,
            upgrade_diag={
                "buff_window_seconds": 12.0,
                "estimated_live_delta_cps": 1.5,
                "estimated_buff_window_gain": 18.0,
                "pause_window_reason": "buff_window",
            },
            combo_pending=True,
            combo_phase="sell",
            shimmers_present=True,
            shimmer_count=2,
            now=10.0,
            upgrade_blocked_until=12.0,
            upgrade_signature_blocked=False,
            cookies_after_reserve=False,
            global_cookie_reserve=60.0,
            garden_cookie_reserve=10.0,
            lucky_cookie_reserve=20.0,
            last_upgrade_action=9.8,
            upgrade_action_cooldown=0.5,
        )

        self.assertIn("upgrade_autobuy_disabled", blockers)
        self.assertTrue(any(item.startswith("pause_non_click_actions ") for item in blockers))
        self.assertIn("combo_pending phase=sell", blockers)
        self.assertIn("shimmers_present count=2", blockers)
        self.assertTrue(any(item.startswith("stuck_candidate_backoff_remaining=") for item in blockers))
        self.assertIn("global_reserve=60.0 (garden=10.0 lucky=20.0)", blockers)
        self.assertTrue(any(item.startswith("cooldown_remaining=") for item in blockers))

    def test_can_plan_wrinkler_respects_post_upgrade_cooldown(self):
        self.assertFalse(
            DomStagePolicy.can_plan_wrinkler(
                combo_pending=False,
                shimmers_present=False,
                now=10.0,
                last_wrinkler_action=9.0,
                wrinkler_action_cooldown=0.1,
                post_upgrade_wrinkler_cooldown_until=11.0,
                purchase_goal={"kind": "upgrade"},
            )
        )
        self.assertTrue(
            DomStagePolicy.can_plan_wrinkler(
                combo_pending=False,
                shimmers_present=False,
                now=10.0,
                last_wrinkler_action=9.0,
                wrinkler_action_cooldown=0.1,
                post_upgrade_wrinkler_cooldown_until=11.0,
                purchase_goal={"kind": "building"},
            )
        )

    def test_can_plan_trade_and_building_gate_on_pause_and_cooldown(self):
        self.assertTrue(
            DomStagePolicy.can_plan_trade(
                ascension_prep_enabled=False,
                stock_management_active=True,
                pause_non_click_actions=False,
                allow_non_click_actions_during_pause=False,
                pause_stock_trading=False,
                defer_stock_for_upgrade_live=False,
                shimmers_present=False,
                now=10.0,
                last_trade_action=9.0,
                trade_action_cooldown=0.5,
            )
        )
        self.assertFalse(
            DomStagePolicy.can_plan_building(
                ascension_prep_enabled=False,
                building_autobuy_enabled=True,
                pause_non_click_actions=True,
                allow_non_click_actions_during_pause=False,
                shimmers_present=False,
                now=10.0,
                last_building_action=9.0,
                building_action_cooldown=0.5,
            )
        )


class DomLoopLateStagePreparerTests(unittest.TestCase):
    def _preparer(self, **overrides):
        defaults = {
            "action_planner": SimpleNamespace(
                plan_upgrade=lambda **kwargs: UpgradeStagePlan(
                    upgrade_action=SimpleNamespace(kind="click_upgrade"),
                    upgrade_store_action=None,
                )
            ),
            "attempt_tracker": DomAttemptTracker(),
            "stage_policy": DomStagePolicy(),
            "update_upgrade_attempt_tracking": lambda snapshot, upgrade_diag, now: None,
            "build_upgrade_attempt_signature": lambda snapshot, upgrade_diag: ("sig", upgrade_diag.get("candidate_id")),
            "should_defer_stock_actions_for_upgrade": lambda snapshot, upgrade_diag, **kwargs: True,
            "has_cookies_after_reserve": lambda snapshot, price, reserve: True,
            "to_screen_point": lambda x, y: (x, y),
            "upgrade_action_cooldown": 0.35,
        }
        defaults.update(overrides)
        return DomLoopLateStagePreparer(**defaults)

    def test_prepare_computes_upgrade_block_state_and_upgrade_plan(self):
        tracker = {
            "blocked_until": 12.0,
            "blocked_signature": ("sig", 4),
        }
        updates = []
        preparer = self._preparer(
            update_upgrade_attempt_tracking=lambda snapshot, upgrade_diag, now: updates.append((upgrade_diag["candidate_id"], now)),
        )

        result = preparer.prepare(
            snapshot={},
            upgrade_diag={"candidate_can_buy": True, "candidate_id": 4, "candidate_price": 120.0},
            shimmers=[],
            now=10.0,
            upgrade_attempt_tracker=tracker,
            upgrade_autobuy_enabled=True,
            pause_non_click_actions=False,
            allow_non_click_actions_during_pause=False,
            global_cookie_reserve=20.0,
            last_upgrade_action=0.0,
            combo_pending=False,
        )

        self.assertEqual(updates, [(4, 10.0)])
        self.assertEqual(result.upgrade_signature, ("sig", 4))
        self.assertTrue(result.upgrade_signature_blocked)
        self.assertTrue(result.defer_stock_for_upgrade_live)
        self.assertTrue(result.cookies_after_upgrade_reserve)
        self.assertIsNone(result.upgrade_action)

    def test_prepare_allows_upgrade_plan_when_policy_gate_opens(self):
        preparer = self._preparer(
            should_defer_stock_actions_for_upgrade=lambda snapshot, upgrade_diag, **kwargs: False,
        )

        result = preparer.prepare(
            snapshot={},
            upgrade_diag={"candidate_can_buy": True, "candidate_id": 7, "candidate_price": 80.0},
            shimmers=[],
            now=10.0,
            upgrade_attempt_tracker={"blocked_until": 0.0, "blocked_signature": None},
            upgrade_autobuy_enabled=True,
            pause_non_click_actions=False,
            allow_non_click_actions_during_pause=False,
            global_cookie_reserve=10.0,
            last_upgrade_action=0.0,
            combo_pending=False,
        )

        self.assertEqual(result.upgrade_action.kind, "click_upgrade")
        self.assertIsNone(result.upgrade_store_action)
        self.assertFalse(result.upgrade_signature_blocked)
        self.assertFalse(result.defer_stock_for_upgrade_live)


class DomLoopOutcomeHandlerTests(unittest.TestCase):
    def _handler(self, **overrides):
        calls = {
            "profiles": [],
            "sleep": [],
        }
        defaults = {
            "perf_counter": lambda: 10.5,
            "record_profile_ms": lambda prefix, elapsed_ms, spike_ms=None: calls["profiles"].append(
                (prefix, round(elapsed_ms, 3), spike_ms)
            ),
            "sleep": lambda seconds: calls["sleep"].append(seconds),
            "feed_poll_interval": 0.08,
        }
        defaults.update(overrides)
        return DomLoopOutcomeHandler(**defaults), calls

    def test_apply_early_outcome_merges_known_fields(self):
        state = DomLoopEarlyStageState(
            last_lump_action=1.0,
            last_note_dismiss_action=2.0,
            last_combo_action_click=3.0,
            last_spell_click=4.0,
        )

        merged = DomLoopOutcomeHandler.apply_early_outcome(
            DomLoopActionOutcome(
                handled=True,
                updates={"last_note_dismiss_action": 9.0, "last_spell_click": 8.0},
            ),
            state,
        )

        self.assertEqual(merged.last_lump_action, 1.0)
        self.assertEqual(merged.last_note_dismiss_action, 9.0)
        self.assertEqual(merged.last_combo_action_click, 3.0)
        self.assertEqual(merged.last_spell_click, 8.0)

    def test_apply_late_outcome_preserves_wrinkler_cooldown_when_update_missing(self):
        state = DomLoopLateStageState(
            last_upgrade_action=1.0,
            last_upgrade_skip_signature=("old",),
            post_upgrade_wrinkler_cooldown_until=5.0,
            last_upgrade_focus_signature=("focus",),
            last_upgrade_focus_at=2.0,
            last_upgrade_focus_point=(10, 20),
            last_wrinkler_action=3.0,
            last_dragon_action=4.0,
            last_trade_action=5.0,
            last_building_action=6.0,
        )

        merged = DomLoopOutcomeHandler.apply_late_outcome(
            DomLoopActionOutcome(
                handled=False,
                updates={"last_upgrade_skip_signature": ("new",), "last_trade_action": 7.0},
            ),
            state,
        )

        self.assertEqual(merged.last_upgrade_skip_signature, ("new",))
        self.assertEqual(merged.last_trade_action, 7.0)
        self.assertEqual(merged.post_upgrade_wrinkler_cooldown_until, 5.0)
        self.assertEqual(merged.last_building_action, 6.0)

    def test_handle_idle_fallthrough_records_profile_and_sleeps(self):
        handler, calls = self._handler()

        handler.handle_idle_fallthrough(10.0)

        self.assertEqual(calls["profiles"], [("dom_action", 500.0, 25.0)])
        self.assertEqual(calls["sleep"], [0.08])


class DomLoopCoordinatorTests(unittest.TestCase):
    def _base_cycle_state(self):
        return DomLoopCycleState(
            build_options=DomLoopBuildOptions(
                building_autobuy_enabled=True,
                lucky_reserve_enabled=True,
                stock_trading_enabled=True,
                upgrade_autobuy_enabled=True,
                ascension_prep_enabled=False,
                garden_automation_enabled=True,
                stock_diag_refresh_interval=3.0,
            ),
            prepared=PreparedSnapshot(
                snapshot={"cookies": 1000.0},
                shimmers=[],
                buffs=[],
                spell={"ready": True, "on_minigame": False},
                big_cookie={"client_x": 10, "client_y": 20},
            ),
            diagnostics=DomLoopDiagnostics(
                garden_diag={},
                lump_diag={},
                building_diag={},
                ascension_prep_diag={},
                upgrade_diag={},
                dragon_diag={},
                santa_diag={},
                golden_diag={},
                spell_diag={},
                reserve_budget={
                    "garden_reserve": 1.0,
                    "lucky_reserve": 2.0,
                    "hard_lucky_reserve": 3.0,
                    "live_lucky_reserve": 4.0,
                    "soft_lucky_delta": 5.0,
                    "total_reserve": 6.0,
                    "building_total_reserve": 7.0,
                },
                purchase_goal=None,
                stock_buy_controls={"allow_buy_actions": True, "buy_reserve_cookies": 0.0},
                stock_management_active=False,
                bank_diag={},
                wrinkler_diag={},
                combo_diag={},
                trade_stats={},
                spell_stats={},
                combo_stats={"pending_phase": "idle"},
                pause_reasons=(),
                pause_non_click_actions=False,
                pause_stock_trading=False,
                allow_non_click_actions_during_pause=False,
                defer_stock_for_upgrade=False,
            ),
            bank_diag_cache=BankDiagCache(diag={"cached": True}, captured_at=8.0),
            now=12.0,
            pause_value_actions_during_clot=False,
        )

    def _base_state(self):
        return DomLoopState(
            suppress_main_click_until=0.5,
            last_spell_click=1.0,
            last_trade_action=2.0,
            last_building_action=3.0,
            last_upgrade_action=4.0,
            last_combo_action_click=5.0,
            last_wrinkler_action=6.0,
            last_dragon_action=7.0,
            last_note_dismiss_action=8.0,
            last_lump_action=9.0,
            last_upgrade_skip_signature=("old",),
            post_upgrade_wrinkler_cooldown_until=10.0,
            last_upgrade_focus_signature=("focus",),
            last_upgrade_focus_at=11.0,
            last_upgrade_focus_point=(1, 2),
            last_seen_golden_decision=("seen",),
            last_feed_signature=("feed",),
            last_feed_debug_at=13.0,
            bank_diag_cache=BankDiagCache(diag={"old": True}, captured_at=1.0),
        )

    def test_run_cycle_returns_after_shimmer_handle(self):
        cycle_state = self._base_cycle_state()
        state = self._base_state()
        stage_runner = SimpleNamespace(
            run_early=lambda context: self.fail("run_early should not be called"),
            run_late=lambda context: self.fail("run_late should not be called"),
        )
        coordinator = DomLoopCoordinator(
            cycle_preparer=SimpleNamespace(prepare_cycle=lambda **kwargs: cycle_state),
            feed_logger=SimpleNamespace(log_if_changed=lambda **kwargs: (("new-feed",), 14.0)),
            shimmer_handler=SimpleNamespace(
                process=lambda context: SimpleNamespace(
                    handled=True,
                    last_seen_golden_decision=("new-seen",),
                    suppress_main_click_until=2.5,
                )
            ),
            stage_runner=stage_runner,
            late_stage_preparer=SimpleNamespace(prepare=lambda **kwargs: None),
            outcome_handler=SimpleNamespace(
                apply_early_outcome=lambda outcome, state: state,
                apply_late_outcome=lambda outcome, state: state,
                handle_idle_fallthrough=lambda action_started: self.fail("idle should not run"),
            ),
            combo_pending_getter=lambda: False,
            perf_counter=lambda: 20.0,
        )

        updated = coordinator.run_cycle(
            state=state,
            build_options=cycle_state.build_options,
            upgrade_attempt_tracker={},
            building_attempt_tracker={},
            shimmer_autoclick_enabled=True,
            auto_cast_hand_of_fate=True,
        )

        self.assertEqual(updated.last_feed_signature, ("new-feed",))
        self.assertEqual(updated.last_feed_debug_at, 14.0)
        self.assertEqual(updated.last_seen_golden_decision, ("new-seen",))
        self.assertEqual(updated.suppress_main_click_until, 2.5)
        self.assertEqual(updated.bank_diag_cache, cycle_state.bank_diag_cache)

    def test_run_cycle_applies_early_and_late_stage_updates(self):
        cycle_state = self._base_cycle_state()
        state = self._base_state()
        early_outcome = DomLoopActionOutcome(handled=False, updates={"last_spell_click": 21.0})
        late_outcome = DomLoopActionOutcome(handled=True, updates={"last_upgrade_action": 33.0})
        prepared_late = SimpleNamespace(
            combo_pending=True,
            upgrade_action="buy",
            upgrade_store_action=None,
            upgrade_signature=("up", 1),
            upgrade_blocked_until=0.0,
            upgrade_signature_blocked=False,
            cookies_after_upgrade_reserve=True,
            defer_stock_for_upgrade_live=False,
        )
        late_contexts = []
        coordinator = DomLoopCoordinator(
            cycle_preparer=SimpleNamespace(prepare_cycle=lambda **kwargs: cycle_state),
            feed_logger=SimpleNamespace(log_if_changed=lambda **kwargs: (state.last_feed_signature, state.last_feed_debug_at)),
            shimmer_handler=SimpleNamespace(
                process=lambda context: SimpleNamespace(
                    handled=False,
                    last_seen_golden_decision=context.last_seen_golden_decision,
                    suppress_main_click_until=context.suppress_main_click_until,
                )
            ),
            stage_runner=SimpleNamespace(
                run_early=lambda context: early_outcome,
                run_late=lambda context: late_contexts.append(context) or late_outcome,
            ),
            late_stage_preparer=SimpleNamespace(prepare=lambda **kwargs: prepared_late),
            outcome_handler=SimpleNamespace(
                apply_early_outcome=lambda outcome, early_state: DomLoopEarlyStageState(
                    last_lump_action=early_state.last_lump_action,
                    last_note_dismiss_action=early_state.last_note_dismiss_action,
                    last_combo_action_click=early_state.last_combo_action_click,
                    last_spell_click=outcome.updates["last_spell_click"],
                ),
                apply_late_outcome=lambda outcome, late_state: DomLoopLateStageState(
                    last_upgrade_action=outcome.updates["last_upgrade_action"],
                    last_upgrade_skip_signature=("logged",),
                    post_upgrade_wrinkler_cooldown_until=41.0,
                    last_upgrade_focus_signature=("focus-2",),
                    last_upgrade_focus_at=42.0,
                    last_upgrade_focus_point=(3, 4),
                    last_wrinkler_action=43.0,
                    last_dragon_action=44.0,
                    last_trade_action=45.0,
                    last_building_action=46.0,
                ),
                handle_idle_fallthrough=lambda action_started: self.fail("idle should not run"),
            ),
            combo_pending_getter=lambda: True,
            perf_counter=lambda: 20.0,
        )

        updated = coordinator.run_cycle(
            state=state,
            build_options=cycle_state.build_options,
            upgrade_attempt_tracker={"attempts": 0},
            building_attempt_tracker={"attempts": 0},
            shimmer_autoclick_enabled=True,
            auto_cast_hand_of_fate=False,
        )

        self.assertEqual(updated.last_spell_click, 21.0)
        self.assertEqual(updated.last_upgrade_action, 33.0)
        self.assertEqual(updated.last_upgrade_skip_signature, ("logged",))
        self.assertEqual(updated.last_trade_action, 45.0)
        self.assertTrue(late_contexts[0].combo_pending)
        self.assertEqual(late_contexts[0].upgrade_signature, ("up", 1))


class DomLoopStateBridgeTests(unittest.TestCase):
    def test_create_state_initializes_loop_tracking_defaults(self):
        bridge = DomLoopStateBridge()

        state = bridge.create_state(
            suppress_main_click_until=1.0,
            last_spell_click=2.0,
            last_trade_action=3.0,
            last_building_action=4.0,
            last_upgrade_action=5.0,
            last_combo_action_click=6.0,
            last_wrinkler_action=7.0,
            last_dragon_action=8.0,
            last_note_dismiss_action=9.0,
            last_lump_action=10.0,
            last_upgrade_skip_signature=("skip",),
            post_upgrade_wrinkler_cooldown_until=11.0,
            last_upgrade_focus_signature=("focus",),
            last_upgrade_focus_at=12.0,
            last_upgrade_focus_point=(1, 2),
            last_seen_golden_decision=("seen",),
        )

        self.assertEqual(state.suppress_main_click_until, 1.0)
        self.assertEqual(state.last_upgrade_action, 5.0)
        self.assertEqual(state.last_feed_signature, None)
        self.assertEqual(state.last_feed_debug_at, 0.0)
        self.assertEqual(state.bank_diag_cache, BankDiagCache())

    def test_sync_before_cycle_preserves_higher_external_suppression(self):
        bridge = DomLoopStateBridge()
        state = DomLoopState(
            suppress_main_click_until=2.0,
            last_spell_click=0.0,
            last_trade_action=0.0,
            last_building_action=0.0,
            last_upgrade_action=0.0,
            last_combo_action_click=0.0,
            last_wrinkler_action=0.0,
            last_dragon_action=0.0,
            last_note_dismiss_action=0.0,
            last_lump_action=0.0,
            last_upgrade_skip_signature=None,
            post_upgrade_wrinkler_cooldown_until=0.0,
            last_upgrade_focus_signature=None,
            last_upgrade_focus_at=0.0,
            last_upgrade_focus_point=None,
            last_seen_golden_decision=None,
            last_feed_signature=("feed",),
            last_feed_debug_at=1.0,
            bank_diag_cache=BankDiagCache(),
        )

        updated = bridge.sync_before_cycle(state, suppress_main_click_until=4.5)

        self.assertEqual(updated.suppress_main_click_until, 4.5)
        self.assertEqual(updated.last_feed_signature, ("feed",))

    def test_export_state_returns_legacy_updates(self):
        bridge = DomLoopStateBridge()
        state = DomLoopState(
            suppress_main_click_until=2.0,
            last_spell_click=3.0,
            last_trade_action=4.0,
            last_building_action=5.0,
            last_upgrade_action=6.0,
            last_combo_action_click=7.0,
            last_wrinkler_action=8.0,
            last_dragon_action=9.0,
            last_note_dismiss_action=10.0,
            last_lump_action=11.0,
            last_upgrade_skip_signature=("skip",),
            post_upgrade_wrinkler_cooldown_until=12.0,
            last_upgrade_focus_signature=("focus",),
            last_upgrade_focus_at=13.0,
            last_upgrade_focus_point=(5, 6),
            last_seen_golden_decision=("seen",),
            last_feed_signature=None,
            last_feed_debug_at=0.0,
            bank_diag_cache=BankDiagCache(),
        )

        updates = bridge.export_state(state, suppress_main_click_until=4.0)

        self.assertEqual(updates["suppress_main_click_until"], 4.0)
        self.assertEqual(updates["last_upgrade_action"], 6.0)
        self.assertEqual(updates["last_upgrade_focus_point"], (5, 6))
        self.assertEqual(updates["last_seen_golden_decision"], ("seen",))


class DomShimmerHandlerTests(unittest.TestCase):
    def _handler(self, **overrides):
        calls = {
            "clicks": [],
            "sleep": [],
            "profiles": [],
            "reset": [],
            "outcomes": [],
            "events": [],
            "click_runtime": [],
            "collect_runtime": [],
            "cleared": [],
            "overlay": [],
        }
        defaults = {
            "log": _LogStub(),
            "click_lock": _NullLock(),
            "click_shimmer": lambda x, y, **kwargs: calls["clicks"].append((x, y, kwargs)),
            "can_interact_with_game": lambda now: True,
            "sleep": lambda seconds: calls["sleep"].append(seconds),
            "monotonic": lambda: 15.0,
            "perf_counter": lambda: 20.5,
            "record_profile_ms": lambda prefix, elapsed_ms, spike_ms=None: calls["profiles"].append(
                (prefix, round(elapsed_ms, 3), spike_ms)
            ),
            "should_skip_wrath_shimmer": lambda buffs, combo_diag=None: False,
            "format_shimmer_id_list": lambda ids, limit=8: ",".join(str(v) for v in ids) if ids else "-",
            "reset_shimmer_tracking": lambda reason, clear_click_state=False: calls["reset"].append((reason, clear_click_state)),
            "record_shimmer_outcome": lambda entry: calls["outcomes"].append(entry),
            "record_event": lambda message: calls["events"].append(message),
            "record_shimmer_click_runtime": lambda shimmer_id, mode: calls["click_runtime"].append((shimmer_id, mode)),
            "record_shimmer_collect_runtime": lambda kind, shimmer_id, outcome, blocked: calls["collect_runtime"].append((kind, shimmer_id, outcome, blocked)),
            "overlay_event_sender": lambda shimmer, **kwargs: calls["overlay"].append((shimmer, kwargs)),
            "get_pending_hand_shimmer": lambda shimmers, now=None: None,
            "clear_pending_hand_shimmer": lambda shimmer_id: calls["cleared"].append(shimmer_id),
            "recent_shimmer_clicks": {},
            "shimmer_first_seen": {},
            "shimmer_click_attempts": {},
            "pending_shimmer_results": {},
            "main_click_suppress_seconds": 0.30,
            "bonus_click_hold": 0.035,
            "feed_poll_interval": 0.08,
            "shimmer_click_delay_seconds": 1.2,
            "shimmer_click_cooldown": 0.12,
            "overlay_click_delay_seconds": 0.0,
        }
        defaults.update(overrides)
        return DomShimmerHandler(**defaults), calls

    def test_process_resolves_pending_shimmer_result(self):
        pending = {
            7: {
                "buffs": ("Frenzy",),
                "type": "golden",
                "wrath": False,
                "seed": 123,
                "selection_mode": "scan",
                "visible_count": 1,
                "visible_wrath_count": 0,
                "visible_ids": (7,),
                "visible_wrath_ids": (),
            }
        }
        handler, calls = self._handler(
            pending_shimmer_results=pending,
            shimmer_click_attempts={7: {"first_click": 10.0, "attempts": 1, "last_logged": 0.0}},
        )

        result = handler.process(
            DomShimmerContext(
                snapshot={},
                shimmers=[],
                buffs=[{"name": "Frenzy"}, {"name": "Click frenzy"}],
                now=12.0,
                pause_value_actions_during_clot=False,
                shimmer_autoclick_enabled=True,
                last_seen_golden_decision=None,
                suppress_main_click_until=0.0,
            )
        )

        self.assertFalse(result.handled)
        self.assertEqual(calls["cleared"], [7])
        self.assertEqual(calls["outcomes"][0]["outcome"], "Click frenzy")
        self.assertEqual(calls["collect_runtime"], [("golden", 7, "Click frenzy", False)])
        self.assertTrue(any("Shimmer collected id=7 outcome=Click frenzy" in msg for msg in calls["events"]))

    def test_process_clicks_priority_shimmer_and_tracks_attempt(self):
        priority = {
            "id": 11,
            "type": "golden",
            "wrath": False,
            "client_x": 10,
            "client_y": 20,
            "screen_x": 30,
            "screen_y": 40,
            "seed": 999,
        }
        recent = {}
        first_seen = {11: 9.7}
        attempts = {}
        pending = {}
        handler, calls = self._handler(
            get_pending_hand_shimmer=lambda shimmers, now=None: priority,
            recent_shimmer_clicks=recent,
            shimmer_first_seen=first_seen,
            shimmer_click_attempts=attempts,
            pending_shimmer_results=pending,
        )

        result = handler.process(
            DomShimmerContext(
                snapshot={},
                shimmers=[priority],
                buffs=[{"name": "Frenzy"}],
                now=10.0,
                pause_value_actions_during_clot=False,
                shimmer_autoclick_enabled=True,
                last_seen_golden_decision=None,
                suppress_main_click_until=1.0,
            )
        )

        self.assertTrue(result.handled)
        self.assertEqual(calls["clicks"], [(30, 40, {"hold": 0.035})])
        self.assertEqual(calls["click_runtime"], [(11, "planned")])
        self.assertEqual(calls["overlay"], [(priority, {"mode": "planned", "clicked_at": 15.0})])
        self.assertEqual(calls["sleep"], [0.08])
        self.assertEqual(recent[11], 15.0)
        self.assertEqual(attempts[11]["attempts"], 1)
        self.assertEqual(pending[11]["selection_mode"], "planned")
        self.assertAlmostEqual(result.suppress_main_click_until, 10.3)

    def test_process_profiles_scan_path_when_nothing_clicked(self):
        perf_values = iter((20.0, 20.5))
        handler, calls = self._handler(perf_counter=lambda: next(perf_values))

        result = handler.process(
            DomShimmerContext(
                snapshot={},
                shimmers=[],
                buffs=[],
                now=10.0,
                pause_value_actions_during_clot=False,
                shimmer_autoclick_enabled=True,
                last_seen_golden_decision=None,
                suppress_main_click_until=0.0,
            )
        )

        self.assertFalse(result.handled)
        self.assertEqual(calls["profiles"], [("dom_shimmer", 500.0, 20.0)])
        self.assertEqual(calls["sleep"], [])

    def test_process_clicks_scan_shimmer_and_emits_overlay_event(self):
        shimmer = {
            "id": 12,
            "type": "golden",
            "wrath": False,
            "client_x": 40,
            "client_y": 50,
            "screen_x": 140,
            "screen_y": 250,
            "life": 10,
            "dur": 20,
            "target_norm_x": 0.25,
            "target_norm_y": 0.50,
        }
        handler, calls = self._handler(shimmer_first_seen={12: 8.0})

        result = handler.process(
            DomShimmerContext(
                snapshot={},
                shimmers=[shimmer],
                buffs=[],
                now=10.0,
                pause_value_actions_during_clot=False,
                shimmer_autoclick_enabled=True,
                last_seen_golden_decision=None,
                suppress_main_click_until=0.0,
            )
        )

        self.assertTrue(result.handled)
        self.assertEqual(calls["clicks"], [(140, 250, {"hold": 0.035})])
        self.assertEqual(calls["overlay"], [(shimmer, {"mode": "clicked", "clicked_at": 15.0})])

    def test_process_delays_single_shimmer_click_after_overlay_preview(self):
        shimmer = {
            "id": 12,
            "type": "golden",
            "wrath": False,
            "client_x": 40,
            "client_y": 50,
            "screen_x": 140,
            "screen_y": 250,
            "life": 10,
            "dur": 20,
            "target_norm_x": 0.25,
            "target_norm_y": 0.50,
        }
        handler, calls = self._handler(
            shimmer_first_seen={12: 8.0},
            overlay_click_delay_seconds=1.0,
        )

        first = handler.process(
            DomShimmerContext(
                snapshot={},
                shimmers=[shimmer],
                buffs=[],
                now=10.0,
                pause_value_actions_during_clot=False,
                shimmer_autoclick_enabled=True,
                last_seen_golden_decision=None,
                suppress_main_click_until=0.0,
            )
        )
        second = handler.process(
            DomShimmerContext(
                snapshot={},
                shimmers=[shimmer],
                buffs=[],
                now=11.1,
                pause_value_actions_during_clot=False,
                shimmer_autoclick_enabled=True,
                last_seen_golden_decision=None,
                suppress_main_click_until=first.suppress_main_click_until,
            )
        )

        self.assertTrue(first.handled)
        self.assertTrue(second.handled)
        self.assertEqual(calls["overlay"], [
            (shimmer, {"mode": "clicked_preview", "clicked_at": 10.0}),
            (shimmer, {"mode": "clicked", "clicked_at": 15.0}),
        ])
        self.assertEqual(calls["clicks"], [(140, 250, {"hold": 0.035})])

    def test_process_clicks_multiple_shimmers_without_overlay_delay(self):
        first_shimmer = {
            "id": 12,
            "type": "golden",
            "wrath": False,
            "client_x": 40,
            "client_y": 50,
            "screen_x": 140,
            "screen_y": 250,
            "life": 10,
            "dur": 20,
            "target_norm_x": 0.25,
            "target_norm_y": 0.50,
        }
        second_shimmer = dict(first_shimmer, id=13, screen_x=160, screen_y=270, wrath=True)
        handler, calls = self._handler(
            shimmer_first_seen={12: 8.0, 13: 8.0},
            overlay_click_delay_seconds=1.0,
        )

        result = handler.process(
            DomShimmerContext(
                snapshot={},
                shimmers=[first_shimmer, second_shimmer],
                buffs=[],
                now=10.0,
                pause_value_actions_during_clot=False,
                shimmer_autoclick_enabled=True,
                last_seen_golden_decision=None,
                suppress_main_click_until=0.0,
            )
        )

        self.assertTrue(result.handled)
        self.assertEqual(calls["clicks"], [(140, 250, {"hold": 0.035})])
        self.assertEqual(calls["overlay"], [(first_shimmer, {"mode": "clicked", "clicked_at": 15.0})])

    def test_process_emits_overlay_for_skipped_wrath_cookie(self):
        shimmer = {
            "id": 12,
            "type": "golden",
            "wrath": True,
            "client_x": 40,
            "client_y": 50,
            "screen_x": 140,
            "screen_y": 250,
            "life": 10,
            "dur": 20,
            "target_norm_x": 0.25,
            "target_norm_y": 0.50,
        }
        handler, calls = self._handler(
            shimmer_first_seen={12: 8.0},
            should_skip_wrath_shimmer=lambda buffs, combo_diag=None: True,
        )

        result = handler.process(
            DomShimmerContext(
                snapshot={},
                shimmers=[shimmer],
                buffs=[],
                now=10.0,
                pause_value_actions_during_clot=False,
                shimmer_autoclick_enabled=True,
                last_seen_golden_decision=None,
                suppress_main_click_until=0.0,
            )
        )

        self.assertFalse(result.handled)
        self.assertEqual(calls["clicks"], [])
        self.assertEqual(calls["overlay"], [(shimmer, {"mode": "wrath_skipped_preview", "clicked_at": 10.0})])

    def test_process_clicks_fortune_without_full_shimmer_delay(self):
        fortune = {
            "id": -100042,
            "type": "fortune",
            "wrath": False,
            "client_x": 300,
            "client_y": 40,
            "screen_x": 400,
            "screen_y": 240,
            "life": 450,
            "dur": 500,
            "effect_kind": "upgrade",
            "effect_name": "Fortune #001",
            "text": "Fortune #001 : Remember to take breaks.",
        }
        pending = {}
        handler, calls = self._handler(
            shimmer_first_seen={-100042: 9.80},
            pending_shimmer_results=pending,
        )

        result = handler.process(
            DomShimmerContext(
                snapshot={},
                shimmers=[fortune],
                buffs=[],
                now=10.0,
                pause_value_actions_during_clot=False,
                shimmer_autoclick_enabled=True,
                last_seen_golden_decision=None,
                suppress_main_click_until=0.0,
            )
        )

        self.assertTrue(result.handled)
        self.assertEqual(calls["clicks"], [(400, 240, {"hold": 0.035})])
        self.assertEqual(calls["click_runtime"], [(-100042, "clicked")])
        self.assertEqual(pending[-100042]["type"], "fortune")
        self.assertEqual(pending[-100042]["effect_name"], "Fortune #001")


class DomActionCoordinatorTests(unittest.TestCase):
    def test_run_returns_first_handled_stage(self):
        calls = []
        coordinator = DomActionCoordinator()

        def first():
            calls.append("first")
            return DomLoopActionOutcome()

        def second():
            calls.append("second")
            return DomLoopActionOutcome(handled=True, updates={"stage": 2})

        def third():
            calls.append("third")
            return DomLoopActionOutcome(handled=True, updates={"stage": 3})

        outcome = coordinator.run((first, second, third))

        self.assertTrue(outcome.handled)
        self.assertEqual(outcome.updates, {"stage": 2})
        self.assertEqual(calls, ["first", "second"])

    def test_run_returns_empty_outcome_when_nothing_handles(self):
        coordinator = DomActionCoordinator()

        outcome = coordinator.run((lambda: DomLoopActionOutcome(),))

        self.assertFalse(outcome.handled)
        self.assertIsNone(outcome.updates)


class DomLoopStageRunnerTests(unittest.TestCase):
    def _runner(self, **overrides):
        action_executor = SimpleNamespace(
            execute_lump_action=lambda lump_diag, now: None,
            execute_note_action=lambda note_action, now: None,
            execute_combo_action=lambda combo_action, now, action_started, combo_recorder: None,
            execute_spell_action=lambda spell_action, now, action_started, spell_recorder: None,
            execute_garden_action=lambda garden_action, now, action_started, garden_recorder: False,
            execute_upgrade_action=lambda **kwargs: None,
            execute_wrinkler_action=lambda *args: None,
            execute_dragon_action=lambda *args: None,
            execute_santa_action=lambda *args: None,
            execute_ascension_prep_action=lambda *args: None,
            execute_trade_action=lambda *args: None,
            execute_building_action=lambda **kwargs: None,
            execute_minigame_store_action=lambda owner, store_action, now, action_started: False,
        )
        action_planner = SimpleNamespace(
            plan_wrinkler=lambda **kwargs: None,
            plan_dragon=lambda **kwargs: None,
            plan_ascension_prep=lambda **kwargs: AscensionStagePlan(),
            plan_trade=lambda **kwargs: None,
            plan_building=lambda **kwargs: BuildingStagePlan(),
            plan_minigame_store_access=lambda **kwargs: MinigameStorePlan(),
        )
        combo_controller = SimpleNamespace(
            has_pending=lambda: False,
            get_action=lambda snapshot, to_screen_point, now=None: None,
            owns_spellcasting=lambda snapshot, to_screen_point: False,
        )
        defaults = {
            "coordinator": DomActionCoordinator(),
            "action_executor": action_executor,
            "action_planner": action_planner,
            "attempt_tracker": SimpleNamespace(log_upgrade_blockers=lambda **kwargs: ("logged",)),
            "stage_policy": DomStagePolicy(),
            "note_target_getter": lambda snapshot, to_screen_point: None,
            "should_allow_garden_action": lambda snapshot, garden_diag: True,
            "update_building_attempt_tracking": lambda snapshot, building_action, now: None,
            "to_screen_point": lambda x, y: (x, y),
            "build_building_attempt_signature": lambda snapshot, action: ("sig", getattr(action, "building_id", None)),
            "extract_building_target_debug": lambda snapshot, building_id: {},
            "format_store_planner_context": lambda context: "",
            "extract_upgrade_target_debug": lambda snapshot, candidate_id: {},
            "format_upgrade_planner_context": lambda context: "",
            "combo_controller": combo_controller,
            "spell_controller": SimpleNamespace(get_action=lambda *args, **kwargs: None),
            "garden_controller": SimpleNamespace(get_action=lambda *args, **kwargs: None),
            "wrinkler_controller": _Recorder(),
            "ascension_controller": _Recorder(),
            "santa_controller": SimpleNamespace(get_action=lambda *args, **kwargs: None, record_action=lambda action: None),
            "stock_trader": _Recorder(),
            "building_autobuyer": _Recorder(),
            "log": _LogStub(),
            "sleep": lambda seconds: None,
            "lump_action_cooldown": 1.0,
            "note_dismiss_cooldown": 0.5,
            "combo_action_cooldown": 0.2,
            "spell_click_cooldown": 1.5,
            "wrinkler_action_cooldown": 0.12,
            "trade_action_cooldown": 0.35,
            "building_action_cooldown": 0.35,
            "upgrade_action_cooldown": 0.35,
            "dragon_action_cooldown": 0.5,
            "dragon_aura_action_cooldown": 15.0,
            "post_upgrade_wrinkler_cooldown_seconds": 3.0,
            "bonus_click_hold": 0.03,
            "trade_click_hold": 0.02,
            "building_stuck_attempt_limit": 4,
            "building_stuck_signature_suppress_seconds": 30.0,
            "upgrade_stuck_attempt_limit": 4,
            "upgrade_stuck_signature_suppress_seconds": 60.0,
            "store_scroll_wheel_multiplier": 12,
            "feed_poll_interval": 0.08,
        }
        defaults.update(overrides)
        return DomLoopStageRunner(**defaults)

    def test_run_early_executes_note_stage(self):
        runner = self._runner(
            note_target_getter=lambda snapshot, to_screen_point: {"kind": "close_note"},
            action_executor=SimpleNamespace(
                execute_lump_action=lambda lump_diag, now: None,
                execute_note_action=lambda note_action, now: 22.0,
                execute_combo_action=lambda combo_action, now, action_started, combo_recorder: None,
                execute_spell_action=lambda spell_action, now, action_started, spell_recorder: None,
                execute_garden_action=lambda garden_action, now, action_started, garden_recorder: False,
            ),
        )

        outcome = runner.run_early(
            DomLoopEarlyStageContext(
                snapshot={},
                shimmers=[],
                lump_diag={},
                garden_diag={},
                building_diag={},
                now=10.0,
                action_started=5.0,
                last_lump_action=9.5,
                last_note_dismiss_action=0.0,
                last_combo_action_click=9.9,
                last_spell_click=9.9,
                pause_non_click_actions=False,
                allow_non_click_actions_during_pause=False,
                pause_value_actions_during_clot=False,
                garden_automation_enabled=True,
                auto_cast_hand_of_fate=True,
            )
        )

        self.assertTrue(outcome.handled)
        self.assertEqual(outcome.updates, {"last_note_dismiss_action": 22.0})

    def test_run_late_preserves_logged_upgrade_skip_signature_without_handling(self):
        log = _LogStub()
        runner = self._runner(log=log)

        outcome = runner.run_late(
            DomLoopLateStageContext(
                snapshot={"store": {"buyMode": 1, "buyBulk": 1}},
                shimmers=[],
                upgrade_diag={"candidate_can_buy": True, "candidate_id": 3, "candidate": "Kitten", "candidate_price": 500.0},
                dragon_diag={},
                combo_diag={},
                spell_diag={},
                purchase_goal=None,
                stock_buy_controls={"allow_buy_actions": True, "buy_reserve_cookies": 0.0},
                stock_management_active=False,
                bank_diag={},
                garden_diag={},
                building_diag={},
                building_cookie_reserve=0.0,
                garden_cookie_reserve=0.0,
                lucky_cookie_reserve=0.0,
                global_cookie_reserve=0.0,
                pause_non_click_actions=False,
                allow_non_click_actions_during_pause=False,
                pause_stock_trading=False,
                pause_reasons=(),
                upgrade_autobuy_enabled=True,
                ascension_prep_enabled=False,
                stock_trading_enabled=False,
                building_autobuy_enabled=False,
                combo_pending=False,
                combo_phase="idle",
                now=10.0,
                action_started=5.0,
                upgrade_action=None,
                upgrade_store_action=None,
                upgrade_signature=("upgrade", 3),
                upgrade_blocked_until=0.0,
                upgrade_signature_blocked=False,
                cookies_after_upgrade_reserve=True,
                defer_stock_for_upgrade_live=False,
                last_upgrade_action=0.0,
                last_upgrade_skip_signature=None,
                last_upgrade_focus_signature=None,
                last_upgrade_focus_at=0.0,
                last_upgrade_focus_point=None,
                last_wrinkler_action=0.0,
                post_upgrade_wrinkler_cooldown_until=0.0,
                last_dragon_action=0.0,
                last_building_action=0.0,
                last_trade_action=0.0,
                upgrade_attempt_tracker={"attempts": 0},
                building_attempt_tracker={"attempts": 0},
            )
        )

        self.assertFalse(outcome.handled)
        self.assertEqual(outcome.updates["last_upgrade_skip_signature"], ("logged",))

    def test_run_late_executes_building_stage(self):
        update_calls = []
        runner = self._runner(
            update_building_attempt_tracking=lambda snapshot, building_action, now: update_calls.append((building_action, now)),
            action_planner=SimpleNamespace(
                plan_wrinkler=lambda **kwargs: None,
                plan_dragon=lambda **kwargs: None,
                plan_ascension_prep=lambda **kwargs: AscensionStagePlan(),
                plan_trade=lambda **kwargs: None,
                plan_building=lambda **kwargs: BuildingStagePlan(
                    building_action=SimpleNamespace(building_id=2, building_name="Grandma"),
                    store_action=SimpleNamespace(kind="click_building"),
                    signature=("sig", 2),
                    signature_blocked=False,
                ),
                plan_minigame_store_access=lambda **kwargs: MinigameStorePlan(),
            ),
            action_executor=SimpleNamespace(
                execute_upgrade_action=lambda **kwargs: None,
                execute_wrinkler_action=lambda *args: None,
                execute_dragon_action=lambda *args: None,
                execute_santa_action=lambda *args: None,
                execute_ascension_prep_action=lambda *args: None,
                execute_trade_action=lambda *args: None,
                execute_building_action=lambda **kwargs: 44.0,
                execute_minigame_store_action=lambda owner, store_action, now, action_started: False,
            ),
        )

        outcome = runner.run_late(
            DomLoopLateStageContext(
                snapshot={},
                shimmers=[],
                upgrade_diag={},
                dragon_diag={},
                combo_diag={},
                spell_diag={},
                purchase_goal=None,
                stock_buy_controls={"allow_buy_actions": True, "buy_reserve_cookies": 0.0},
                stock_management_active=False,
                bank_diag={},
                garden_diag={},
                building_diag={"next_candidate_price": 100.0},
                building_cookie_reserve=0.0,
                garden_cookie_reserve=0.0,
                lucky_cookie_reserve=0.0,
                global_cookie_reserve=0.0,
                pause_non_click_actions=False,
                allow_non_click_actions_during_pause=False,
                pause_stock_trading=False,
                pause_reasons=(),
                upgrade_autobuy_enabled=False,
                ascension_prep_enabled=False,
                stock_trading_enabled=False,
                building_autobuy_enabled=True,
                combo_pending=False,
                combo_phase="idle",
                now=10.0,
                action_started=5.0,
                upgrade_action=None,
                upgrade_store_action=None,
                upgrade_signature=None,
                upgrade_blocked_until=0.0,
                upgrade_signature_blocked=False,
                cookies_after_upgrade_reserve=False,
                defer_stock_for_upgrade_live=False,
                last_upgrade_action=10.0,
                last_upgrade_skip_signature=None,
                last_upgrade_focus_signature=None,
                last_upgrade_focus_at=0.0,
                last_upgrade_focus_point=None,
                last_wrinkler_action=10.0,
                post_upgrade_wrinkler_cooldown_until=0.0,
                last_dragon_action=10.0,
                last_building_action=0.0,
                last_trade_action=10.0,
                upgrade_attempt_tracker={"attempts": 0},
                building_attempt_tracker={"attempts": 0, "blocked_until": 0.0, "blocked_signature": None},
            )
        )

        self.assertTrue(outcome.handled)
        self.assertEqual(outcome.updates["last_building_action"], 44.0)
        self.assertEqual(update_calls[0][1], 10.0)

    def test_run_late_executes_santa_stage(self):
        santa_calls = []
        runner = self._runner(
            santa_controller=SimpleNamespace(
                get_action=lambda snapshot, to_screen_point, now=None: SimpleNamespace(
                    kind="click_santa",
                    screen_x=11,
                    screen_y=22,
                    level=0,
                    max_level=14,
                    target_level=14,
                    current_name="Festive test tube",
                    next_name="Festive ornament",
                    reason="level_santa",
                )
            ),
            action_executor=SimpleNamespace(
                execute_upgrade_action=lambda **kwargs: None,
                execute_wrinkler_action=lambda *args: None,
                execute_dragon_action=lambda *args: None,
                execute_santa_action=lambda santa_action, now, action_started, santa_recorder: santa_calls.append(
                    (santa_action.current_name, santa_action.next_name, now)
                ) or 55.0,
                execute_ascension_prep_action=lambda *args: None,
                execute_trade_action=lambda *args: None,
                execute_building_action=lambda **kwargs: None,
                execute_minigame_store_action=lambda owner, store_action, now, action_started: False,
            ),
        )

        outcome = runner.run_late(
            DomLoopLateStageContext(
                snapshot={"santa": {"level": 0, "maxLevel": 14, "unlocked": True}},
                shimmers=[],
                upgrade_diag={},
                dragon_diag={},
                combo_diag={},
                spell_diag={},
                purchase_goal=None,
                stock_buy_controls={"allow_buy_actions": True, "buy_reserve_cookies": 0.0},
                stock_management_active=False,
                bank_diag={},
                garden_diag={},
                building_diag={},
                building_cookie_reserve=0.0,
                garden_cookie_reserve=0.0,
                lucky_cookie_reserve=0.0,
                global_cookie_reserve=0.0,
                pause_non_click_actions=False,
                allow_non_click_actions_during_pause=False,
                pause_stock_trading=False,
                pause_reasons=(),
                upgrade_autobuy_enabled=False,
                ascension_prep_enabled=False,
                stock_trading_enabled=False,
                building_autobuy_enabled=False,
                combo_pending=False,
                combo_phase="idle",
                now=10.0,
                action_started=5.0,
                upgrade_action=None,
                upgrade_store_action=None,
                upgrade_signature=None,
                upgrade_blocked_until=0.0,
                upgrade_signature_blocked=False,
                cookies_after_upgrade_reserve=True,
                defer_stock_for_upgrade_live=False,
                last_upgrade_action=0.0,
                last_upgrade_skip_signature=None,
                last_upgrade_focus_signature=None,
                last_upgrade_focus_at=0.0,
                last_upgrade_focus_point=None,
                last_wrinkler_action=0.0,
                post_upgrade_wrinkler_cooldown_until=0.0,
                last_dragon_action=0.0,
                last_building_action=0.0,
                last_trade_action=0.0,
                upgrade_attempt_tracker={"attempts": 0},
                building_attempt_tracker={"attempts": 0},
            )
        )

        self.assertTrue(outcome.handled)
        self.assertEqual(santa_calls, [("Festive test tube", "Festive ornament", 10.0)])


if __name__ == "__main__":
    unittest.main()
