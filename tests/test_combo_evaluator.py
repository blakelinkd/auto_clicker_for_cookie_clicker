import unittest

from clicker_bot.features.combo_evaluator import evaluate_combo_buffs


class ComboEvaluatorTests(unittest.TestCase):
    def test_reports_idle_when_no_combo_buffs_are_active(self):
        combo = evaluate_combo_buffs(set())

        self.assertEqual(combo["stage"], "idle")
        self.assertEqual(combo["phase"], "idle")

    def test_reports_setup_when_a_production_buff_is_active_without_a_ready_spell(self):
        combo = evaluate_combo_buffs({"Frenzy"}, spell_ready=False)

        self.assertEqual(combo["stage"], "build_combo")
        self.assertEqual(combo["phase"], "setup")

    def test_reports_fish_when_a_production_buff_is_active_and_the_spell_is_ready(self):
        combo = evaluate_combo_buffs({"Frenzy"}, spell_ready=True)

        self.assertEqual(combo["stage"], "build_combo")
        self.assertEqual(combo["phase"], "fish")

    def test_reports_execute_when_click_and_production_buffs_overlap(self):
        combo = evaluate_combo_buffs({"Frenzy", "Click frenzy"}, spell_ready=True)

        self.assertEqual(combo["stage"], "execute_click_combo")
        self.assertEqual(combo["phase"], "execute")


if __name__ == "__main__":
    unittest.main()
