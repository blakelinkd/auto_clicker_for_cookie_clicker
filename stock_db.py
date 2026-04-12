import json
import sqlite3
import threading
import time
from pathlib import Path


class StockDatabase:
    HISTORY_COMMIT_INTERVAL_SECONDS = 1.0
    HISTORY_COMMIT_ROW_THRESHOLD = 180
    THRESHOLD_SERIES_LIMIT_PER_GOOD = 2000
    THRESHOLD_RAW_FALLBACK_MULTIPLIER = 90
    THRESHOLD_RAW_FALLBACK_MIN_LIMIT = 50000
    THRESHOLD_RAW_FALLBACK_MAX_LIMIT = 250000

    def __init__(self, db_path, log):
        self.log = log
        self.db_path = Path(db_path)
        self.lock = threading.Lock()
        self.read_lock = threading.Lock()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.read_conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.pending_history_rows = 0
        self.last_history_commit_at = time.monotonic()
        self.profile = {}
        self.profile_last_log_at = {}
        self.last_change_value_by_good = {}
        with self.lock:
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
        with self.read_lock:
            self.read_conn.execute("PRAGMA journal_mode=WAL")
            self.read_conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()
        self._prime_last_change_values()

    def _init_schema(self):
        started = time.perf_counter()
        with self.lock:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS stock_price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observed_at_ms INTEGER NOT NULL,
                    good_id INTEGER NOT NULL,
                    symbol TEXT,
                    name TEXT,
                    value REAL NOT NULL,
                    stock INTEGER NOT NULL,
                    stock_max INTEGER,
                    UNIQUE(observed_at_ms, good_id) ON CONFLICT IGNORE
                );

                CREATE INDEX IF NOT EXISTS idx_stock_price_history_good_time
                ON stock_price_history(good_id, observed_at_ms);

                CREATE TABLE IF NOT EXISTS stock_price_change_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observed_at_ms INTEGER NOT NULL,
                    good_id INTEGER NOT NULL,
                    symbol TEXT,
                    name TEXT,
                    value REAL NOT NULL,
                    UNIQUE(observed_at_ms, good_id) ON CONFLICT IGNORE
                );

                CREATE INDEX IF NOT EXISTS idx_stock_price_change_history_good_time
                ON stock_price_change_history(good_id, observed_at_ms);

                CREATE TABLE IF NOT EXISTS stock_positions (
                    good_id INTEGER PRIMARY KEY,
                    symbol TEXT,
                    name TEXT,
                    shares INTEGER NOT NULL,
                    avg_entry REAL NOT NULL,
                    avg_entry_cookies REAL NOT NULL,
                    updated_at_ms INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS stock_trade_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_at_ms INTEGER NOT NULL,
                    phase TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    good_id INTEGER,
                    symbol TEXT,
                    name TEXT,
                    shares INTEGER,
                    price REAL,
                    cookies REAL,
                    unit_cost_cookies REAL,
                    unit_sale_cookies REAL,
                    previous_shares INTEGER,
                    observed_shares INTEGER,
                    avg_entry_before REAL,
                    avg_entry_after REAL,
                    avg_entry_cookies_before REAL,
                    avg_entry_cookies_after REAL,
                    realized_pnl_cookies REAL,
                    reason TEXT,
                    mode_name TEXT,
                    resting_value REAL,
                    range_min REAL,
                    range_max REAL,
                    range_avg REAL,
                    range_position REAL,
                    buy_threshold REAL,
                    sell_threshold REAL,
                    delta REAL,
                    history_json TEXT,
                    extra_json TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_stock_trade_history_time
                ON stock_trade_history(event_at_ms);

                CREATE INDEX IF NOT EXISTS idx_stock_trade_history_good_time
                ON stock_trade_history(good_id, event_at_ms);

                CREATE TABLE IF NOT EXISTS stock_trade_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observed_at_ms INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    action_kind TEXT,
                    buy_candidate_id INTEGER,
                    buy_candidate_name TEXT,
                    sell_candidate_id INTEGER,
                    sell_candidate_name TEXT,
                    sell_reason TEXT,
                    cookies REAL,
                    portfolio_exposure REAL,
                    portfolio_cap REAL,
                    portfolio_remaining REAL,
                    buy_reserve_cookies REAL,
                    buy_actions_enabled INTEGER NOT NULL,
                    sell_actions_enabled INTEGER NOT NULL,
                    buy_good_json TEXT,
                    sell_good_json TEXT,
                    extra_json TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_stock_trade_decisions_time
                ON stock_trade_decisions(observed_at_ms);
                """
            )
            self.conn.commit()
        self._record_profile("init_schema", time.perf_counter() - started, spike_ms=50.0)

    def record_prices(self, observed_at_ms, goods):
        started = time.perf_counter()
        rows = []
        change_rows = []
        timestamp = int(observed_at_ms)
        for good in goods:
            good_id = int(good["id"])
            value = float(good["value"])
            rows.append(
                (
                    timestamp,
                    good_id,
                    good.get("symbol"),
                    good.get("name"),
                    value,
                    int(good["stock"]),
                    None if good.get("stock_max") is None else int(good["stock_max"]),
                )
            )
            previous_value = self.last_change_value_by_good.get(good_id)
            if previous_value is None or float(previous_value) != value:
                change_rows.append(
                    (
                        timestamp,
                        good_id,
                        good.get("symbol"),
                        good.get("name"),
                        value,
                    )
                )
                self.last_change_value_by_good[good_id] = value
        if not rows:
            return
        with self.lock:
            self.conn.executemany(
                """
                INSERT OR IGNORE INTO stock_price_history (
                    observed_at_ms, good_id, symbol, name, value, stock, stock_max
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            if change_rows:
                self.conn.executemany(
                    """
                    INSERT OR IGNORE INTO stock_price_change_history (
                        observed_at_ms, good_id, symbol, name, value
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    change_rows,
                )
            self.pending_history_rows += len(rows)
            self._commit_history_if_due()
        self._record_profile("record_prices", time.perf_counter() - started, spike_ms=15.0)

    def get_prior_high(self, good_id, observed_at_ms):
        started = time.perf_counter()
        with self.read_lock:
            row = self.read_conn.execute(
                """
                SELECT MAX(value)
                FROM stock_price_history
                WHERE good_id = ? AND observed_at_ms < ?
                """,
                (int(good_id), int(observed_at_ms)),
            ).fetchone()
        self._record_profile("get_prior_high", time.perf_counter() - started, spike_ms=10.0)
        if not row or row[0] is None:
            return None
        return float(row[0])

    def get_recent_range_stats(self, good_ids, observed_at_ms, window_ms):
        started = time.perf_counter()
        ids = [int(good_id) for good_id in good_ids]
        if not ids:
            return {}

        start_ms = int(observed_at_ms) - int(window_ms)
        placeholders = ",".join("?" for _ in ids)
        query = f"""
            SELECT
                good_id,
                MIN(value) AS min_value,
                MAX(value) AS max_value,
                AVG(value) AS avg_value,
                COUNT(*) AS sample_count
            FROM stock_price_history
            WHERE observed_at_ms >= ?
              AND observed_at_ms < ?
              AND good_id IN ({placeholders})
            GROUP BY good_id
        """
        params = [start_ms, int(observed_at_ms), *ids]
        with self.read_lock:
            rows = self.read_conn.execute(query, params).fetchall()
        self._record_profile("get_recent_range_stats", time.perf_counter() - started, spike_ms=15.0)

        stats = {}
        for row in rows:
            stats[int(row[0])] = {
                "min": None if row[1] is None else float(row[1]),
                "max": None if row[2] is None else float(row[2]),
                "avg": None if row[3] is None else float(row[3]),
                "samples": int(row[4] or 0),
            }
        return stats

    def get_price_series(self, good_ids, per_good_limit=None):
        started = time.perf_counter()
        ids = [int(good_id) for good_id in good_ids]
        if not ids:
            return {}

        limit = int(per_good_limit or self.THRESHOLD_SERIES_LIMIT_PER_GOOD)
        series = {}
        with self.read_lock:
            for good_id in ids:
                rows = self.read_conn.execute(
                    """
                    SELECT value
                    FROM stock_price_change_history
                    WHERE good_id = ?
                    ORDER BY observed_at_ms DESC
                    LIMIT ?
                    """,
                    (int(good_id), limit),
                ).fetchall()
                if rows and len(rows) >= limit:
                    values = [float(row[0]) for row in reversed(rows) if row and row[0] is not None]
                else:
                    values = self._get_price_series_from_raw_history_locked(int(good_id), limit)
                series[int(good_id)] = values
        self._record_profile("get_price_series", time.perf_counter() - started, spike_ms=25.0)
        return series

    def _prime_last_change_values(self):
        started = time.perf_counter()
        query = """
            SELECT good_id, value
            FROM (
                SELECT good_id, value,
                       ROW_NUMBER() OVER (PARTITION BY good_id ORDER BY observed_at_ms DESC) AS rn
                FROM stock_price_change_history
            )
            WHERE rn = 1
        """
        fallback_query = """
            SELECT good_id, value
            FROM (
                SELECT good_id, value,
                       ROW_NUMBER() OVER (PARTITION BY good_id ORDER BY observed_at_ms DESC) AS rn
                FROM stock_price_history
            )
            WHERE rn = 1
        """
        with self.read_lock:
            rows = self.read_conn.execute(query).fetchall()
            if not rows:
                rows = self.read_conn.execute(fallback_query).fetchall()
        self.last_change_value_by_good = {
            int(row[0]): float(row[1])
            for row in rows
            if row and row[0] is not None and row[1] is not None
        }
        self._record_profile("prime_last_change_values", time.perf_counter() - started, spike_ms=50.0)

    def _get_price_series_from_raw_history_locked(self, good_id, limit):
        raw_limit = max(
            self.THRESHOLD_RAW_FALLBACK_MIN_LIMIT,
            min(
                self.THRESHOLD_RAW_FALLBACK_MAX_LIMIT,
                int(limit) * self.THRESHOLD_RAW_FALLBACK_MULTIPLIER,
            ),
        )
        rows = self.read_conn.execute(
            """
            SELECT value
            FROM stock_price_history
            WHERE good_id = ?
            ORDER BY observed_at_ms DESC
            LIMIT ?
            """,
            (int(good_id), int(raw_limit)),
        ).fetchall()
        deduped_desc = []
        last_value = object()
        for row in rows:
            if not row or row[0] is None:
                continue
            value = float(row[0])
            if deduped_desc and value == last_value:
                continue
            deduped_desc.append(value)
            last_value = value
            if len(deduped_desc) >= int(limit):
                break
        deduped_desc.reverse()
        return deduped_desc

    def load_positions(self):
        started = time.perf_counter()
        with self.read_lock:
            rows = self.read_conn.execute(
                """
                SELECT good_id, symbol, name, shares, avg_entry, avg_entry_cookies
                FROM stock_positions
                """
            ).fetchall()
        self._record_profile("load_positions", time.perf_counter() - started, spike_ms=10.0)
        positions = {}
        for row in rows:
            positions[int(row[0])] = {
                "symbol": row[1],
                "name": row[2],
                "shares": int(row[3]),
                "avg_entry": float(row[4]),
                "avg_entry_cookies": float(row[5]),
            }
        return positions

    def upsert_position(self, good_id, symbol, name, shares, avg_entry, avg_entry_cookies, updated_at_ms):
        started = time.perf_counter()
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO stock_positions (
                    good_id, symbol, name, shares, avg_entry, avg_entry_cookies, updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(good_id) DO UPDATE SET
                    symbol = excluded.symbol,
                    name = excluded.name,
                    shares = excluded.shares,
                    avg_entry = excluded.avg_entry,
                    avg_entry_cookies = excluded.avg_entry_cookies,
                    updated_at_ms = excluded.updated_at_ms
                """,
                (
                    int(good_id),
                    symbol,
                    name,
                    int(shares),
                    float(avg_entry),
                    float(avg_entry_cookies),
                    int(updated_at_ms),
                ),
            )
            self._commit_all_locked()
        self._record_profile("upsert_position", time.perf_counter() - started, spike_ms=20.0)

    def delete_position(self, good_id):
        started = time.perf_counter()
        with self.lock:
            self.conn.execute("DELETE FROM stock_positions WHERE good_id = ?", (int(good_id),))
            self._commit_all_locked()
        self._record_profile("delete_position", time.perf_counter() - started, spike_ms=20.0)

    def record_trade_event(self, **fields):
        started = time.perf_counter()
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO stock_trade_history (
                    event_at_ms, phase, kind, good_id, symbol, name, shares, price, cookies,
                    unit_cost_cookies, unit_sale_cookies, previous_shares, observed_shares,
                    avg_entry_before, avg_entry_after, avg_entry_cookies_before, avg_entry_cookies_after,
                    realized_pnl_cookies, reason, mode_name, resting_value, range_min, range_max,
                    range_avg, range_position, buy_threshold, sell_threshold, delta, history_json, extra_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(fields.get("event_at_ms") or int(time.time() * 1000)),
                    str(fields.get("phase") or ""),
                    str(fields.get("kind") or ""),
                    None if fields.get("good_id") is None else int(fields.get("good_id")),
                    fields.get("symbol"),
                    fields.get("name"),
                    None if fields.get("shares") is None else int(fields.get("shares")),
                    None if fields.get("price") is None else float(fields.get("price")),
                    None if fields.get("cookies") is None else float(fields.get("cookies")),
                    None if fields.get("unit_cost_cookies") is None else float(fields.get("unit_cost_cookies")),
                    None if fields.get("unit_sale_cookies") is None else float(fields.get("unit_sale_cookies")),
                    None if fields.get("previous_shares") is None else int(fields.get("previous_shares")),
                    None if fields.get("observed_shares") is None else int(fields.get("observed_shares")),
                    None if fields.get("avg_entry_before") is None else float(fields.get("avg_entry_before")),
                    None if fields.get("avg_entry_after") is None else float(fields.get("avg_entry_after")),
                    None if fields.get("avg_entry_cookies_before") is None else float(fields.get("avg_entry_cookies_before")),
                    None if fields.get("avg_entry_cookies_after") is None else float(fields.get("avg_entry_cookies_after")),
                    None if fields.get("realized_pnl_cookies") is None else float(fields.get("realized_pnl_cookies")),
                    fields.get("reason"),
                    fields.get("mode_name"),
                    None if fields.get("resting_value") is None else float(fields.get("resting_value")),
                    None if fields.get("range_min") is None else float(fields.get("range_min")),
                    None if fields.get("range_max") is None else float(fields.get("range_max")),
                    None if fields.get("range_avg") is None else float(fields.get("range_avg")),
                    None if fields.get("range_position") is None else float(fields.get("range_position")),
                    None if fields.get("buy_threshold") is None else float(fields.get("buy_threshold")),
                    None if fields.get("sell_threshold") is None else float(fields.get("sell_threshold")),
                    None if fields.get("delta") is None else float(fields.get("delta")),
                    json.dumps(fields.get("history")) if fields.get("history") is not None else None,
                    json.dumps(fields.get("extra")) if fields.get("extra") is not None else None,
                ),
            )
            self._commit_all_locked()
        self._record_profile("record_trade_event", time.perf_counter() - started, spike_ms=20.0)

    def record_trade_decision(self, **fields):
        started = time.perf_counter()
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO stock_trade_decisions (
                    observed_at_ms, reason, action_kind, buy_candidate_id, buy_candidate_name,
                    sell_candidate_id, sell_candidate_name, sell_reason, cookies, portfolio_exposure,
                    portfolio_cap, portfolio_remaining, buy_reserve_cookies, buy_actions_enabled,
                    sell_actions_enabled, buy_good_json, sell_good_json, extra_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(fields.get("observed_at_ms") or int(time.time() * 1000)),
                    str(fields.get("reason") or ""),
                    fields.get("action_kind"),
                    None if fields.get("buy_candidate_id") is None else int(fields.get("buy_candidate_id")),
                    fields.get("buy_candidate_name"),
                    None if fields.get("sell_candidate_id") is None else int(fields.get("sell_candidate_id")),
                    fields.get("sell_candidate_name"),
                    fields.get("sell_reason"),
                    None if fields.get("cookies") is None else float(fields.get("cookies")),
                    None if fields.get("portfolio_exposure") is None else float(fields.get("portfolio_exposure")),
                    None if fields.get("portfolio_cap") is None else float(fields.get("portfolio_cap")),
                    None if fields.get("portfolio_remaining") is None else float(fields.get("portfolio_remaining")),
                    None if fields.get("buy_reserve_cookies") is None else float(fields.get("buy_reserve_cookies")),
                    1 if fields.get("buy_actions_enabled") else 0,
                    1 if fields.get("sell_actions_enabled") else 0,
                    json.dumps(fields.get("buy_good")) if fields.get("buy_good") is not None else None,
                    json.dumps(fields.get("sell_good")) if fields.get("sell_good") is not None else None,
                    json.dumps(fields.get("extra")) if fields.get("extra") is not None else None,
                ),
            )
            self._commit_all_locked()
        self._record_profile("record_trade_decision", time.perf_counter() - started, spike_ms=20.0)

    def _commit_history_if_due(self):
        now = time.monotonic()
        if (
            self.pending_history_rows >= self.HISTORY_COMMIT_ROW_THRESHOLD
            or (now - self.last_history_commit_at) >= self.HISTORY_COMMIT_INTERVAL_SECONDS
        ):
            self._commit_all_locked()

    def _commit_all_locked(self):
        started = time.perf_counter()
        self.conn.commit()
        self.pending_history_rows = 0
        self.last_history_commit_at = time.monotonic()
        self._record_profile("commit", time.perf_counter() - started, spike_ms=20.0)

    def _record_profile(self, key, elapsed_seconds, spike_ms):
        elapsed_ms = float(elapsed_seconds) * 1000.0
        stat = self.profile.get(key)
        if stat is None:
            stat = {"avg_ms": elapsed_ms, "max_ms": elapsed_ms, "count": 1}
        else:
            count = int(stat["count"]) + 1
            stat["avg_ms"] = ((stat["avg_ms"] * stat["count"]) + elapsed_ms) / count
            stat["max_ms"] = max(float(stat["max_ms"]), elapsed_ms)
            stat["count"] = count
        self.profile[key] = stat
        last_logged = float(self.profile_last_log_at.get(key, 0.0))
        now = time.monotonic()
        if elapsed_ms >= float(spike_ms) and (now - last_logged) >= 5.0:
            self.profile_last_log_at[key] = now
            self.log.warning(f"DB spike op={key} elapsed_ms={elapsed_ms:.1f}")

    def get_runtime_stats(self):
        return {
            key: {
                "avg_ms": round(float(value["avg_ms"]), 3),
                "max_ms": round(float(value["max_ms"]), 3),
                "count": int(value["count"]),
            }
            for key, value in self.profile.items()
        }
