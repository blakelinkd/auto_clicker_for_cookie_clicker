import unittest

from clicker_bot.features.spell_autocaster import (
    CRAFTY_PIXIES_KEY,
    HAND_OF_FATE_KEY,
    RESURRECT_ABOMINATION_KEY,
    SpellAutocaster,
)


class _LogStub:
    def info(self, message):
        pass


def _identity_point(x, y):
    return x, y


class SpellAutocasterResurrectAbominationTests(unittest.TestCase):
    def setUp(self):
        self.autocaster = SpellAutocaster(_LogStub())

    def _resurrect_snapshot(self):
        return {
            "spellbook": {
                "onMinigame": True,
                "openControl": {"centerX": 5, "centerY": 5},
                "magic": 50.0,
                "maxMagic": 50.0,
                "spells": [
                    {
                        "id": 1,
                        "key": RESURRECT_ABOMINATION_KEY,
                        "name": "Resurrect Abomination",
                        "cost": 24.0,
                        "failChance": 0.15,
                        "ready": True,
                        "rect": {"centerX": 10, "centerY": 20},
                    },
                    {
                        "id": 2,
                        "key": HAND_OF_FATE_KEY,
                        "name": "Force the Hand of Fate",
                        "cost": 38.0,
                        "failChance": 0.15,
                        "ready": False,
                        "rect": {"centerX": 30, "centerY": 20},
                    },
                ],
                "activeBuffs": [],
                "handOfFateForecast": {
                    "outcome": "click frenzy",
                    "backfire": False,
                    "failChance": 0.15,
                    "castIndex": 100,
                },
            },
            "wrinklers": {
                "elderWrath": 1,
                "active": 0,
                "attached": 0,
                "max": 10,
                "openSlots": 10,
            },
        }

    def test_resurrect_abomination_is_disabled(self):
        action = self.autocaster.get_action(self._resurrect_snapshot(), _identity_point, now=10.0)
        diag = self.autocaster.get_diagnostics(self._resurrect_snapshot(), _identity_point)

        self.assertIsNone(action)
        self.assertEqual(diag["reason"], "resurrect_abomination_disabled")
        self.assertIsNone(diag["candidate"])

    def test_stretch_time_targets_cookie_storm(self):
        state = {
            "buffs": [{"name": "Cookie storm", "time": 2.0}],
        }

        target = self.autocaster._get_stretch_time_target(state)

        self.assertEqual(target, "Cookie storm")

    def test_stretch_time_targets_cursed_finger(self):
        state = {
            "buffs": [{"name": "Cursed finger", "time": 2.0}],
        }

        target = self.autocaster._get_stretch_time_target(state)

        self.assertEqual(target, "Cursed finger")

    def test_stretch_time_ignores_low_value_buff(self):
        state = {
            "buffs": [{"name": "Clot", "time": 2.0}],
        }

        target = self.autocaster._get_stretch_time_target(state)

        self.assertIsNone(target)

    def _pixies_snapshot(self, *, magic=40.0, fail_chance=0.0, buffs=()):
        return {
            "spellbook": {
                "onMinigame": True,
                "openControl": {"centerX": 5, "centerY": 5},
                "magic": magic,
                "maxMagic": 100.0,
                "spells": [
                    {
                        "id": 7,
                        "key": CRAFTY_PIXIES_KEY,
                        "name": "Summon Crafty Pixies",
                        "cost": 20.0,
                        "failChance": fail_chance,
                        "ready": True,
                        "rect": {"centerX": 10, "centerY": 20},
                    }
                ],
                "activeBuffs": [{"name": name} for name in buffs],
            },
            "wrinklers": {
                "elderWrath": 0,
                "openSlots": 10,
                "attached": 0,
                "max": 10,
            },
        }

    def test_opens_grimoire_when_hand_of_fate_is_ready_but_spellbook_is_closed(self):
        snapshot = {
            "spellbook": {
                "onMinigame": False,
                "openControl": {"centerX": 44, "centerY": 55},
                "magic": 100.0,
                "maxMagic": 100.0,
                "spells": [
                    {
                        "id": 2,
                        "key": HAND_OF_FATE_KEY,
                        "name": "Force the Hand of Fate",
                        "cost": 38.0,
                        "failChance": 0.15,
                        "ready": True,
                    },
                ],
                "activeBuffs": [],
                "handOfFateForecast": {
                    "outcome": "click frenzy",
                    "backfire": False,
                    "failChance": 0.15,
                    "castIndex": 100,
                },
            },
            "wrinklers": {
                "elderWrath": 0,
                "active": 0,
                "attached": 0,
                "max": 10,
                "openSlots": 10,
            },
        }

        action = self.autocaster.get_action(snapshot, _identity_point, now=10.0)
        diag = self.autocaster.get_diagnostics(snapshot, _identity_point)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "open_grimoire")
        self.assertEqual(action.reason, "open_grimoire")
        self.assertEqual(diag["reason"], "grimoire_closed")
        self.assertTrue(diag["has_open_target"])

    def test_opens_grimoire_when_closed_even_without_immediate_spell_signal(self):
        snapshot = {
            "spellbook": {
                "onMinigame": False,
                "openControl": {"centerX": 44, "centerY": 55},
                "magic": 10.0,
                "maxMagic": 100.0,
                "spells": [],
                "activeBuffs": [],
            },
            "wrinklers": {
                "elderWrath": 0,
                "active": 0,
                "attached": 0,
                "max": 10,
                "openSlots": 10,
            },
        }

        action = self.autocaster.get_action(snapshot, _identity_point, now=10.0)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "open_grimoire")

    def test_casts_crafty_pixies_for_large_dragon_floor_buy(self):
        building_diag = {
            "reason": "dragon_building_floor_ready",
            "candidate": "Bank",
            "candidate_price": 500_000_000_000.0,
            "cookies": 600_000_000_000.0,
            "cookies_ps": 1_000_000.0,
            "store_buy_mode": 1,
            "store_buy_bulk": 1,
            "dragon_target": {"building_name": "Bank"},
        }

        action = self.autocaster.get_action(
            self._pixies_snapshot(),
            _identity_point,
            now=10.0,
            building_diag=building_diag,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.key, CRAFTY_PIXIES_KEY)
        self.assertEqual(action.reason, "discount_Bank")

    def test_skips_crafty_pixies_for_large_regular_buy(self):
        building_diag = {
            "reason": "buy_ready",
            "candidate": "Alchemy lab",
            "candidate_price": 3_500_000_000_000_000.0,
            "cookies": 18_000_000_000_000_000.0,
            "cookies_ps": 140_000_000_000_000.0,
            "store_buy_mode": 1,
            "store_buy_bulk": 1,
        }

        action = self.autocaster.get_action(
            self._pixies_snapshot(),
            _identity_point,
            now=10.0,
            building_diag=building_diag,
        )

        self.assertIsNone(action)

    def test_skips_crafty_pixies_for_small_minigame_rebuy(self):
        building_diag = {
            "reason": "buy_ready",
            "candidate": "Farm",
            "candidate_price": 6_000.0,
            "cookies": 600_000_000_000.0,
            "cookies_ps": 1_000_000.0,
            "store_buy_mode": 1,
            "store_buy_bulk": 1,
        }

        action = self.autocaster.get_action(
            self._pixies_snapshot(),
            _identity_point,
            now=10.0,
            building_diag=building_diag,
        )

        self.assertIsNone(action)

    def test_casts_crafty_pixies_for_matching_active_building_buff(self):
        building_diag = {
            "reason": "buy_ready",
            "candidate": "Mine",
            "candidate_price": 5_000_000_000.0,
            "cookies": 4_000_000_000.0,
            "cookies_ps": 10_000_000.0,
            "store_buy_mode": 1,
            "store_buy_bulk": 1,
            "active_building_buffs": (
                {
                    "building_id": 3,
                    "building_name": "Mine",
                    "buff_name": "Ore vein",
                    "type": "building buff",
                    "multiplier": 10.0,
                },
            ),
        }

        action = self.autocaster.get_action(
            self._pixies_snapshot(buffs=("Frenzy", "Ore vein")),
            _identity_point,
            now=10.0,
            building_diag=building_diag,
        )
        diag = self.autocaster.get_diagnostics(
            self._pixies_snapshot(buffs=("Frenzy", "Ore vein")),
            _identity_point,
            building_diag=building_diag,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.key, CRAFTY_PIXIES_KEY)
        self.assertEqual(action.reason, "discount_Mine")
        self.assertEqual(diag["reason"], "crafty_pixies_ready")
        self.assertEqual(diag["crafty_pixies_target"], "Mine")

    def test_skips_crafty_pixies_during_reactive_combo_stack(self):
        building_diag = {
            "reason": "dragon_building_floor_ready",
            "candidate": "Bank",
            "candidate_price": 500_000_000_000.0,
            "cookies": 600_000_000_000.0,
            "cookies_ps": 1_000_000.0,
            "store_buy_mode": 1,
            "store_buy_bulk": 1,
            "dragon_target": {"building_name": "Bank"},
        }

        action = self.autocaster.get_action(
            self._pixies_snapshot(buffs=("Frenzy",)),
            _identity_point,
            now=10.0,
            building_diag=building_diag,
        )

        self.assertIsNone(action)

    def test_skips_crafty_pixies_when_store_is_not_actionable(self):
        building_diag = {
            "reason": "dragon_building_floor_ready",
            "candidate": "Bank",
            "candidate_price": 500_000_000_000.0,
            "cookies": 600_000_000_000.0,
            "cookies_ps": 1_000_000.0,
            "store_buy_mode": 1,
            "store_buy_bulk": 10,
            "dragon_target": {"building_name": "Bank"},
        }

        action = self.autocaster.get_action(
            self._pixies_snapshot(),
            _identity_point,
            now=10.0,
            building_diag=building_diag,
        )

        self.assertIsNone(action)

    def test_pending_hand_shimmer_ignores_non_golden_types(self):
        self.autocaster.pending_hand_cookie = {
            "cast_at": 10.0,
            "expected_outcome": "click frenzy",
            "target_shimmer_id": None,
        }

        target = self.autocaster.get_pending_hand_shimmer(
            [
                {"id": 11, "type": "reindeer"},
                {"id": 12, "type": "golden", "wrath": False},
            ],
            now=10.1,
        )

        self.assertIsNotNone(target)
        self.assertEqual(target["id"], 12)

    def test_casts_hand_of_fate_for_positive_economic_outcome(self):
        snapshot = {
            "spellbook": {
                "onMinigame": True,
                "magic": 40.0,
                "maxMagic": 100.0,
                "spells": [
                    {
                        "id": 1,
                        "key": HAND_OF_FATE_KEY,
                        "name": "Hand of Fate",
                        "cost": 10.0,
                        "failChance": 0.15,
                        "ready": True,
                        "rect": {"centerX": 10, "centerY": 20},
                    }
                ],
                "activeBuffs": [],
                "handOfFateForecast": {
                    "outcome": "building special",
                    "backfire": False,
                    "failChance": 0.15,
                    "castIndex": 10,
                },
            },
            "wrinklers": {
                "elderWrath": 0,
                "openSlots": 10,
                "attached": 0,
                "max": 10,
            },
        }

        action = self.autocaster.get_action(snapshot, _identity_point, now=10.0)
        diag = self.autocaster.get_diagnostics(snapshot, _identity_point)

        self.assertIsNotNone(action)
        self.assertEqual(action.key, HAND_OF_FATE_KEY)
        self.assertEqual(action.reason, "spawn_building_special")
        self.assertEqual(diag["reason"], "hand_of_fate_economic_ready")

    def test_casts_hand_of_fate_to_stack_building_special_on_frenzy(self):
        snapshot = {
            "spellbook": {
                "onMinigame": True,
                "magic": 40.0,
                "maxMagic": 100.0,
                "spells": [
                    {
                        "id": 1,
                        "key": HAND_OF_FATE_KEY,
                        "name": "Hand of Fate",
                        "cost": 10.0,
                        "failChance": 0.15,
                        "ready": True,
                        "rect": {"centerX": 10, "centerY": 20},
                    }
                ],
                "activeBuffs": [{"name": "Frenzy", "time": 50.0}],
                "handOfFateForecast": {
                    "outcome": "building special",
                    "backfire": False,
                    "failChance": 0.15,
                    "castIndex": 10,
                },
            },
            "wrinklers": {
                "elderWrath": 0,
                "openSlots": 10,
                "attached": 0,
                "max": 10,
            },
        }

        action = self.autocaster.get_action(snapshot, _identity_point, now=10.0)
        diag = self.autocaster.get_diagnostics(snapshot, _identity_point)

        self.assertIsNotNone(action)
        self.assertEqual(action.key, HAND_OF_FATE_KEY)
        self.assertEqual(action.reason, "spawn_building_special")
        self.assertEqual(diag["reason"], "hand_of_fate_combo_ready")

    def test_casts_hand_of_fate_to_stack_frenzy_on_building_special(self):
        snapshot = {
            "spellbook": {
                "onMinigame": True,
                "magic": 40.0,
                "maxMagic": 100.0,
                "spells": [
                    {
                        "id": 1,
                        "key": HAND_OF_FATE_KEY,
                        "name": "Hand of Fate",
                        "cost": 10.0,
                        "failChance": 0.15,
                        "ready": True,
                        "rect": {"centerX": 10, "centerY": 20},
                    }
                ],
                "activeBuffs": [{"name": "Building special", "time": 25.0}],
                "handOfFateForecast": {
                    "outcome": "frenzy",
                    "backfire": False,
                    "failChance": 0.15,
                    "castIndex": 10,
                },
            },
            "wrinklers": {
                "elderWrath": 0,
                "openSlots": 10,
                "attached": 0,
                "max": 10,
            },
        }

        action = self.autocaster.get_action(snapshot, _identity_point, now=10.0)

        self.assertIsNotNone(action)
        self.assertEqual(action.key, HAND_OF_FATE_KEY)
        self.assertEqual(action.reason, "spawn_frenzy")

    def test_does_not_cast_duplicate_frenzy_into_existing_frenzy(self):
        snapshot = {
            "spellbook": {
                "onMinigame": True,
                "magic": 40.0,
                "maxMagic": 100.0,
                "spells": [
                    {
                        "id": 1,
                        "key": HAND_OF_FATE_KEY,
                        "name": "Hand of Fate",
                        "cost": 10.0,
                        "failChance": 0.15,
                        "ready": True,
                        "rect": {"centerX": 10, "centerY": 20},
                    }
                ],
                "activeBuffs": [{"name": "Frenzy", "time": 50.0}],
                "handOfFateForecast": {
                    "outcome": "frenzy",
                    "backfire": False,
                    "failChance": 0.15,
                    "castIndex": 10,
                },
            },
            "wrinklers": {
                "elderWrath": 0,
                "openSlots": 10,
                "attached": 0,
                "max": 10,
            },
        }

        action = self.autocaster.get_action(snapshot, _identity_point, now=10.0)
        diag = self.autocaster.get_diagnostics(snapshot, _identity_point)

        self.assertIsNone(action)
        self.assertEqual(diag["reason"], "hand_of_fate_waiting_for_stack_roll")

    def test_stretch_time_does_not_preempt_ready_hand_combo(self):
        snapshot = {
            "spellbook": {
                "onMinigame": True,
                "magic": 40.0,
                "maxMagic": 100.0,
                "spells": [
                    {
                        "id": 1,
                        "key": HAND_OF_FATE_KEY,
                        "name": "Hand of Fate",
                        "cost": 10.0,
                        "failChance": 0.15,
                        "ready": True,
                        "rect": {"centerX": 10, "centerY": 20},
                    },
                    {
                        "id": 2,
                        "key": "stretch time",
                        "name": "Stretch Time",
                        "cost": 4.0,
                        "failChance": 0.0,
                        "ready": True,
                        "rect": {"centerX": 30, "centerY": 40},
                    },
                ],
                "activeBuffs": [
                    {"name": "Frenzy", "time": 2.5},
                    {"name": "Building special", "time": 18.0},
                ],
                "handOfFateForecast": {
                    "outcome": "click frenzy",
                    "backfire": False,
                    "failChance": 0.15,
                    "castIndex": 10,
                },
            },
            "wrinklers": {
                "elderWrath": 0,
                "openSlots": 10,
                "attached": 0,
                "max": 10,
            },
        }

        action = self.autocaster.get_action(snapshot, _identity_point, now=10.0)

        self.assertIsNotNone(action)
        self.assertEqual(action.key, HAND_OF_FATE_KEY)
        self.assertEqual(action.reason, "spawn_click_frenzy")

    def test_stretch_time_targets_stacked_frenzy_before_last_three_seconds(self):
        state = {
            "buffs": [
                {"name": "Frenzy", "time": 8.0},
                {"name": "Building special", "time": 14.0},
            ],
        }

        target = self.autocaster._get_stretch_time_target(state)

        self.assertEqual(target, "Frenzy")

    def test_step_spell_candidates_exclude_spontaneous_edifice(self):
        state = {
            "spells_by_key": {
                "spontaneous edifice": {
                    "key": "spontaneous edifice",
                    "name": "Spontaneous Edifice",
                    "cost": 50.0,
                    "ready": True,
                },
                "haggler's charm": {
                    "key": "haggler's charm",
                    "name": "Haggler's Charm",
                    "cost": 10.0,
                    "ready": True,
                },
            }
        }

        candidates = self.autocaster._get_step_spell_candidates(state)
        keys = {candidate["key"] for candidate in candidates}

        self.assertIn("haggler's charm", keys)
        self.assertNotIn("spontaneous edifice", keys)


if __name__ == "__main__":
    unittest.main()
