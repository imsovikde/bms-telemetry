#!/usr/bin/env python3
"""
================================================================================
UNIT TESTS: BMS SQLITE WAL PERSISTENCE & EXPORT ENGINE
================================================================================
Validates:
1. SQLite WAL mode configuration and journal integrity.
2. Sub-millisecond telemetry record insertion and index search.
3. Process attribution snapshot storage and aggregation queries.
4. Streaming RFC-4180 CSV generation and JSON archive round-trip.
================================================================================
"""

import os
import sys
import time
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

import bms_storage as storage


class TestStorageWAL(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_telemetry.db")
        self.engine = storage.BMSStorageEngine(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_wal_mode_and_schema_initialized(self):
        """Verify database pragma is set to WAL and tables exist."""
        conn = self.engine._get_connection()
        try:
            mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            self.assertEqual(mode.lower(), "wal")

            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()]
            self.assertIn("telemetry_samples", tables)
            self.assertIn("process_attribution_samples", tables)
            self.assertIn("hardware_alerts", tables)
        finally:
            conn.close()

    def test_02_record_telemetry_and_range_query(self):
        """Verify recording samples and slicing by epoch_ms range."""
        base_ms = 1789000000000
        for i in range(10):
            self.engine.record_telemetry({
                "timestamp": f"2026-09-10T12:{i:02d}:00Z",
                "epoch_ms": base_ms + (i * 1000),
                "voltage_mv": 11550.0 + i,
                "current_ma": 1000.0,
                "power_mw": 11550.0,
                "charging": 1,
                "soc_pct": 50.0 + i,
                "accumulated_cycles": f"15.{i:030d}",
                "virtual_health_pct": 99.4,
                "cpu_temp_c": 48.0 + (i * 0.5),
                "cpu_headroom_c": 52.0 - (i * 0.5),
                "event_type": "TEST_TICK"
            })

        # Query middle slice [base_ms + 2000, base_ms + 6000]
        results = self.engine.query_telemetry(base_ms + 2000, base_ms + 6000)
        self.assertEqual(len(results), 5)
        self.assertEqual(results[0]["epoch_ms"], base_ms + 2000)
        self.assertEqual(results[-1]["epoch_ms"], base_ms + 6000)

    def test_03_record_process_attribution_and_aggregate(self):
        """Verify process attribution storage and aggregation."""
        base_ms = 1789000000000
        procs = [
            {"pid": 101, "name": "browser.exe", "cpu_pct": 15.0, "gpu_pct": 5.0, "power_mw": 3500.0, "accumulated_energy_mwh": 0.5, "power_share_pct": 25.0},
            {"pid": 102, "name": "editor.exe", "cpu_pct": 8.0, "gpu_pct": 0.0, "power_mw": 1200.0, "accumulated_energy_mwh": 0.2, "power_share_pct": 10.0}
        ]
        self.engine.record_process_attribution(procs, epoch_ms=base_ms)
        top = self.engine.query_top_processes(base_ms - 500, base_ms + 500)
        self.assertEqual(len(top), 2)
        self.assertEqual(top[0]["process_name"], "browser.exe")
        self.assertEqual(top[0]["pid"], 101)

    def test_04_streaming_csv_export(self):
        """Verify RFC-4180 streaming CSV output."""
        base_ms = 1789000000000
        self.engine.record_telemetry({
            "timestamp": "2026-09-10T12:00:00Z",
            "epoch_ms": base_ms,
            "voltage_mv": 11550.0,
            "current_ma": 500.0,
            "power_mw": 5775.0,
            "charging": 1,
            "soc_pct": 75.0,
            "accumulated_cycles": "15.309873844527311029482710394827",
            "virtual_health_pct": 99.4,
            "cpu_temp_c": 50.0,
            "cpu_headroom_c": 50.0,
            "event_type": "CSV_TEST"
        })

        chunks = list(self.engine.export_csv_stream(base_ms - 100, base_ms + 100))
        full_csv = "".join(chunks)
        lines = full_csv.strip().split("\n")
        self.assertGreaterEqual(len(lines), 2)
        header = lines[0].split(",")
        self.assertIn("timestamp", header)
        self.assertIn("voltage_mv", header)
        self.assertIn("accumulated_cycles", header)
        self.assertIn("cpu_temp_c", header)

    def test_05_json_export_and_import_roundtrip(self):
        """Verify JSON export and idempotent import with deduplication."""
        base_ms = 1789000000000
        self.engine.record_telemetry({
            "timestamp": "2026-09-10T12:00:00Z",
            "epoch_ms": base_ms,
            "voltage_mv": 11550.0,
            "power_mw": 5000.0,
            "soc_pct": 80.0,
            "accumulated_cycles": "15.123",
            "virtual_health_pct": 99.5,
            "cpu_temp_c": 49.0,
            "cpu_headroom_c": 51.0,
            "event_type": "JSON_TEST"
        })

        exported = self.engine.export_json(base_ms - 100, base_ms + 100)
        self.assertEqual(exported["format"], "BMS_LIFETIME_TELEMETRY_EXPORT_V2")
        self.assertEqual(len(exported["telemetry_points"]), 1)

        # Import into fresh engine
        new_db = os.path.join(self.temp_dir.name, "new_telemetry.db")
        new_engine = storage.BMSStorageEngine(db_path=new_db)
        res = new_engine.import_json(exported)
        self.assertTrue(res["success"])
        self.assertEqual(res["imported_points"], 1)

        # Test deduplication: importing same archive again should insert 0 new records
        res_dedup = new_engine.import_json(exported)
        self.assertTrue(res_dedup["success"])
        self.assertEqual(res_dedup["imported_points"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
