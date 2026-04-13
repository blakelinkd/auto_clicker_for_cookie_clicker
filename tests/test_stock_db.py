import tempfile
import unittest
from pathlib import Path

from clicker_bot.features.stock_db import StockDatabase


class _LogStub:
    def debug(self, message):
        pass

    def info(self, message):
        pass

    def warning(self, message):
        pass


class StockDatabaseSeriesTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.db_path = Path(handle.name)
        handle.close()
        self.db_path.unlink(missing_ok=True)
        db_path = self.db_path
        self.db = StockDatabase(db_path, _LogStub())
        self.db.HISTORY_COMMIT_ROW_THRESHOLD = 1
        self.db.THRESHOLD_RAW_FALLBACK_MIN_LIMIT = 1
        self.db.THRESHOLD_RAW_FALLBACK_MAX_LIMIT = 1000
        self.db.THRESHOLD_RAW_FALLBACK_MULTIPLIER = 10

    def tearDown(self):
        self.db.conn.close()
        self.db.read_conn.close()
        self.db_path.unlink(missing_ok=True)

    def _record_values(self, values, *, good_id=0):
        for idx, value in enumerate(values, start=1):
            self.db.record_prices(
                idx,
                [
                    {
                        "id": good_id,
                        "symbol": "TST",
                        "name": "Test Good",
                        "value": float(value),
                        "stock": 0,
                        "stock_max": 100,
                    }
                ],
            )
        with self.db.lock:
            self.db._commit_all_locked()

    def test_get_price_series_uses_change_points_from_raw_history(self):
        self._record_values([10, 10, 10, 12, 12, 9, 9, 15])

        with self.db.lock:
            self.db.conn.execute("DELETE FROM stock_price_change_history")
            self.db._commit_all_locked()

        series = self.db.get_price_series([0], per_good_limit=10)

        self.assertEqual(series[0], [10.0, 12.0, 9.0, 15.0])

    def test_record_prices_populates_change_history_without_duplicates(self):
        self._record_values([10, 10, 12, 12, 12, 11])

        series = self.db.get_price_series([0], per_good_limit=10)

        self.assertEqual(series[0], [10.0, 12.0, 11.0])


if __name__ == "__main__":
    unittest.main()
