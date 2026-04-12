class DashboardStateBuilder:
    """Builds the structured dashboard payload from runtime and subsystem stats."""

    def __init__(
        self,
        *,
        runtime_store,
        hud_recent_events,
        get_trade_stats,
        get_building_stats,
        get_ascension_prep_stats,
        get_garden_stats,
        get_combo_stats,
        get_spell_stats,
        get_wrinkler_stats,
        shimmer_seed_history,
        get_shimmer_reset_reason,
    ):
        self.runtime_store = runtime_store
        self.hud_recent_events = int(hud_recent_events)
        self.get_trade_stats = get_trade_stats
        self.get_building_stats = get_building_stats
        self.get_ascension_prep_stats = get_ascension_prep_stats
        self.get_garden_stats = get_garden_stats
        self.get_combo_stats = get_combo_stats
        self.get_spell_stats = get_spell_stats
        self.get_wrinkler_stats = get_wrinkler_stats
        self.shimmer_seed_history = shimmer_seed_history
        self.get_shimmer_reset_reason = get_shimmer_reset_reason

    def build(self):
        state, events, feed = self.runtime_store.snapshot_state()
        shimmer_count = len(self.shimmer_seed_history)
        shimmer_positive = sum(
            1 for event in self.shimmer_seed_history if event.get("classification") == "positive"
        )
        shimmer_negative = sum(
            1 for event in self.shimmer_seed_history if event.get("classification") == "negative"
        )
        shimmer_neutral = sum(
            1 for event in self.shimmer_seed_history if event.get("classification") == "neutral"
        )
        seeds_captured = sum(1 for event in self.shimmer_seed_history if event.get("seed"))
        shimmer_telemetry = state.get("last_shimmer_telemetry") or {}
        return {
            "state": state,
            "events": events[-self.hud_recent_events :],
            "feed": feed,
            "trade_stats": self.get_trade_stats(),
            "building_stats": self.get_building_stats(),
            "ascension_prep_stats": self.get_ascension_prep_stats(),
            "garden_stats": self.get_garden_stats(),
            "combo_stats": self.get_combo_stats(),
            "spell_stats": self.get_spell_stats(),
            "wrinkler_stats": self.get_wrinkler_stats(),
            "shimmer_stats": {
                "total": shimmer_count,
                "positive": shimmer_positive,
                "negative": shimmer_negative,
                "neutral": shimmer_neutral,
                "seeds_captured": seeds_captured,
                "tracking_active": bool(state.get("active")),
                "reset_reason": self.get_shimmer_reset_reason(),
                "valid": bool(state.get("active")),
                "predictor_mode": shimmer_telemetry.get("predictorMode"),
                "blocked_total": int(shimmer_telemetry.get("blockedCount") or 0),
                "last_choice": shimmer_telemetry.get("lastChoice"),
                "last_applied_choice": shimmer_telemetry.get("lastAppliedChoice"),
                "last_gate_classification": shimmer_telemetry.get("lastGateClassification"),
                "last_allowed": shimmer_telemetry.get("lastAllowed"),
            },
        }
