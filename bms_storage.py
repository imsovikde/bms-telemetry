#!/usr/bin/env python3
"""
================================================================================
BMS SQLITE WAL HIGH-FREQUENCY TIME-SERIES STORAGE ENGINE
================================================================================
ACID-resilient, sub-millisecond append-only storage with Write-Ahead Logging (WAL).
Maintains 100% historical telemetry, hardware thermal states, and process power
attributions across reboots. Provides streaming RFC-4180 CSV export and JSON
archive import/playback with automated schema indexing.
================================================================================
"""

import os
import sys
import time
import sqlite3
import threading
import csv
import gzip
import io
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Generator

_HERE = os.path.dirname(os.path.abspath(__file__))
_PRIMARY_DB_DIR = r"C:\ProgramData\BMS"
if os.path.exists(_PRIMARY_DB_DIR):
    DB_PATH = os.path.join(_PRIMARY_DB_DIR, "bms_telemetry.db")
else:
    DB_PATH = os.path.join(_HERE, "bms_telemetry.db")


class BMSStorageEngine:
    """High-throughput SQLite WAL storage engine for BMS telemetry."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA cache_size = -8000;")
        return conn

    def _init_db(self):
        """Initializes tables and high-speed B-Tree indexes."""
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS telemetry_samples (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT NOT NULL,
                            epoch_ms INTEGER NOT NULL,
                            voltage_mv REAL,
                            current_ma REAL,
                            power_mw REAL,
                            charging INTEGER,
                            discharging INTEGER,
                            power_online INTEGER,
                            remaining_capacity_mwh REAL,
                            full_charge_capacity_mwh REAL,
                            design_capacity_mwh REAL,
                            soc_pct REAL,
                            accumulated_cycles TEXT,
                            virtual_health_pct REAL,
                            cpu_temp_c REAL,
                            cpu_headroom_c REAL,
                            event_type TEXT
                        );
                    """)
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_telem_epoch 
                        ON telemetry_samples(epoch_ms);
                    """)

                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS process_attribution_samples (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT NOT NULL,
                            epoch_ms INTEGER NOT NULL,
                            pid INTEGER,
                            process_name TEXT,
                            cpu_pct REAL,
                            gpu_pct REAL,
                            power_mw REAL,
                            energy_mwh REAL,
                            share_pct REAL
                        );
                    """)
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_proc_epoch 
                        ON process_attribution_samples(epoch_ms);
                    """)

                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS hardware_alerts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT NOT NULL,
                            epoch_ms INTEGER NOT NULL,
                            alert_type TEXT,
                            level TEXT,
                            message TEXT
                        );
                    """)
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_alert_epoch 
                        ON hardware_alerts(epoch_ms);
                    """)
            finally:
                conn.close()

    def record_telemetry(self, p: Dict[str, Any]):
        """Records a single telemetry snapshot point."""
        now_epoch_ms = p.get("epoch_ms") or int(time.time() * 1000)
        ts = p.get("timestamp") or datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        INSERT INTO telemetry_samples (
                            timestamp, epoch_ms, voltage_mv, current_ma, power_mw,
                            charging, discharging, power_online,
                            remaining_capacity_mwh, full_charge_capacity_mwh, design_capacity_mwh,
                            soc_pct, accumulated_cycles, virtual_health_pct,
                            cpu_temp_c, cpu_headroom_c, event_type
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, (
                        ts,
                        now_epoch_ms,
                        float(p.get("voltage_mv") or 0.0),
                        float(p.get("current_ma") or 0.0),
                        float(p.get("power_mw") or 0.0),
                        1 if p.get("charging") else 0,
                        1 if p.get("discharging") else 0,
                        1 if p.get("power_online") else 0,
                        float(p.get("remaining_capacity_mwh") or 0.0),
                        float(p.get("full_charge_capacity_mwh") or 0.0),
                        float(p.get("design_capacity_mwh") or 0.0),
                        float(p.get("soc_pct") or 100.0),
                        str(p.get("accumulated_cycles") or "0.0"),
                        float(p.get("virtual_health_pct") or 100.0),
                        float(p.get("cpu_temp_c") or 45.0),
                        float(p.get("cpu_headroom_c") or 55.0),
                        str(p.get("event_type") or "TELEMETRY_SAMPLE")
                    ))
            finally:
                conn.close()

    def record_process_attribution(self, procs: List[Dict[str, Any]], epoch_ms: Optional[int] = None):
        """Records a batch of top process power attributions."""
        if not procs:
            return
        now_ms = epoch_ms or int(time.time() * 1000)
        ts = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.executemany("""
                        INSERT INTO process_attribution_samples (
                            timestamp, epoch_ms, pid, process_name,
                            cpu_pct, gpu_pct, power_mw, energy_mwh, share_pct
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, [
                        (
                            ts,
                            now_ms,
                            int(p.get("pid", 0)),
                            str(p.get("name", "unknown")),
                            float(p.get("cpu_pct", 0.0)),
                            float(p.get("gpu_pct", 0.0)),
                            float(p.get("power_mw", 0.0)),
                            float(p.get("accumulated_energy_mwh", 0.0)),
                            float(p.get("power_share_pct", 0.0))
                        )
                        for p in procs
                    ])
            finally:
                conn.close()

    def record_alert(self, alert_type: str, level: str, message: str):
        """Logs a hardware alert threshold event."""
        now_ms = int(time.time() * 1000)
        ts = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        INSERT INTO hardware_alerts (timestamp, epoch_ms, alert_type, level, message)
                        VALUES (?, ?, ?, ?, ?);
                    """, (ts, now_ms, alert_type, level, message))
            finally:
                conn.close()

    def query_telemetry(
        self,
        start_epoch_ms: int,
        end_epoch_ms: int,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Queries historical telemetry samples within time window. If limit is None or 0, returns all samples."""
        with self._lock:
            conn = self._get_connection()
            try:
                if limit and limit > 0:
                    cur = conn.execute("""
                        SELECT * FROM telemetry_samples
                        WHERE epoch_ms >= ? AND epoch_ms <= ?
                        ORDER BY epoch_ms ASC
                        LIMIT ?;
                    """, (start_epoch_ms, end_epoch_ms, limit))
                else:
                    cur = conn.execute("""
                        SELECT * FROM telemetry_samples
                        WHERE epoch_ms >= ? AND epoch_ms <= ?
                        ORDER BY epoch_ms ASC;
                    """, (start_epoch_ms, end_epoch_ms))
                rows = cur.fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()

    def query_top_processes(
        self,
        start_epoch_ms: int,
        end_epoch_ms: int,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Returns aggregated energy-consuming processes in the given window. If limit is None or 0, returns all."""
        with self._lock:
            conn = self._get_connection()
            try:
                if limit and limit > 0:
                    cur = conn.execute("""
                        SELECT process_name, pid,
                               AVG(cpu_pct) as avg_cpu,
                               AVG(gpu_pct) as avg_gpu,
                               AVG(power_mw) as avg_power_mw,
                               MAX(energy_mwh) as total_energy_mwh,
                               AVG(share_pct) as avg_share
                        FROM process_attribution_samples
                        WHERE epoch_ms >= ? AND epoch_ms <= ?
                        GROUP BY process_name, pid
                        ORDER BY avg_power_mw DESC
                        LIMIT ?;
                    """, (start_epoch_ms, end_epoch_ms, limit))
                else:
                    cur = conn.execute("""
                        SELECT process_name, pid,
                               AVG(cpu_pct) as avg_cpu,
                               AVG(gpu_pct) as avg_gpu,
                               AVG(power_mw) as avg_power_mw,
                               MAX(energy_mwh) as total_energy_mwh,
                               AVG(share_pct) as avg_share
                        FROM process_attribution_samples
                        WHERE epoch_ms >= ? AND epoch_ms <= ?
                        GROUP BY process_name, pid
                        ORDER BY avg_power_mw DESC;
                    """, (start_epoch_ms, end_epoch_ms))
                return [dict(r) for r in cur.fetchall()]
            finally:
                conn.close()

    def record_s5_offline_event(
        self,
        event_type: str,
        delta_mwh: float,
        delta_cycles: str,
        capacity_before: float,
        capacity_after: float,
        timestamp: Optional[str] = None
    ):
        """Records an immutable S5 offline charging or drain event directly into SQLite WAL."""
        now_ms = int(time.time() * 1000)
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        INSERT INTO telemetry_samples (
                            timestamp, epoch_ms, voltage_mv, current_ma, power_mw,
                            charging, discharging, power_online,
                            remaining_capacity_mwh, full_charge_capacity_mwh, design_capacity_mwh,
                            soc_pct, accumulated_cycles, virtual_health_pct,
                            cpu_temp_c, cpu_headroom_c, event_type
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, (
                        ts,
                        now_ms,
                        12500.0,
                        0.0,
                        delta_mwh,
                        1 if "CHARGE" in event_type else 0,
                        1 if "DRAIN" in event_type else 0,
                        1 if "CHARGE" in event_type else 0,
                        capacity_after,
                        69993.0,
                        69993.0,
                        round((capacity_after / 69993.0) * 100.0, 2),
                        str(delta_cycles),
                        100.0,
                        38.0,
                        62.0,
                        event_type
                    ))
                    conn.execute("""
                        INSERT INTO hardware_alerts (timestamp, epoch_ms, alert_type, level, message)
                        VALUES (?, ?, ?, ?, ?);
                    """, (
                        ts,
                        now_ms,
                        event_type,
                        "INFO",
                        f"S5 Offline Delta: {delta_mwh:+.1f} mWh ({delta_cycles} cycles). Before: {capacity_before:.1f} mWh, After: {capacity_after:.1f} mWh"
                    ))
            finally:
                conn.close()

    def export_csv_stream(
        self,
        start_epoch_ms: int = 0,
        end_epoch_ms: Optional[int] = None
    ) -> Generator[str, None, None]:
        """Streaming RFC-4180 CSV generator for high-speed downloads of complete lifetime telemetry."""
        if end_epoch_ms is None:
            end_epoch_ms = int(time.time() * 1000)

        columns = [
            "timestamp", "epoch_ms", "voltage_mv", "current_ma", "power_mw",
            "charging", "discharging", "power_online", "remaining_capacity_mwh",
            "full_charge_capacity_mwh", "design_capacity_mwh", "soc_pct",
            "accumulated_cycles", "virtual_health_pct", "cpu_temp_c", "cpu_headroom_c",
            "event_type"
        ]

        # Write header
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(columns)
        yield buf.getvalue()

        conn = self._get_connection()
        try:
            cur = conn.execute("""
                SELECT timestamp, epoch_ms, voltage_mv, current_ma, power_mw,
                       charging, discharging, power_online, remaining_capacity_mwh,
                       full_charge_capacity_mwh, design_capacity_mwh, soc_pct,
                       accumulated_cycles, virtual_health_pct, cpu_temp_c, cpu_headroom_c,
                       event_type
                FROM telemetry_samples
                WHERE epoch_ms >= ? AND epoch_ms <= ?
                ORDER BY epoch_ms ASC;
            """, (start_epoch_ms, end_epoch_ms))

            batch_size = 500
            while True:
                rows = cur.fetchmany(batch_size)
                if not rows:
                    break
                buf = io.StringIO()
                writer = csv.writer(buf)
                for r in rows:
                    writer.writerow([r[c] for c in columns])
                yield buf.getvalue()
        finally:
            conn.close()

    def export_csv_gz_stream(
        self,
        start_epoch_ms: int = 0,
        end_epoch_ms: Optional[int] = None
    ) -> Generator[bytes, None, None]:
        """Streaming gzip-compressed RFC-4180 CSV generator for high-speed, compact downloads."""
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            for chunk in self.export_csv_stream(start_epoch_ms, end_epoch_ms):
                gz.write(chunk.encode("utf-8"))
                val = buf.getvalue()
                if val:
                    yield val
                    buf.seek(0)
                    buf.truncate(0)
        rem = buf.getvalue()
        if rem:
            yield rem

    def export_json(
        self,
        start_epoch_ms: int = 0,
        end_epoch_ms: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Comprehensive JSON export of all lifetime telemetry and process profiles without truncation."""
        if end_epoch_ms is None:
            end_epoch_ms = int(time.time() * 1000)

        points = self.query_telemetry(start_epoch_ms, end_epoch_ms, limit=limit)
        procs = self.query_top_processes(start_epoch_ms, end_epoch_ms, limit=limit)
        return {
            "format": "BMS_LIFETIME_TELEMETRY_EXPORT_V2",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "time_window": {
                "start_epoch_ms": start_epoch_ms,
                "end_epoch_ms": end_epoch_ms,
                "total_points": len(points),
                "total_processes": len(procs)
            },
            "telemetry_points": points,
            "top_processes": procs
        }

    def export_json_gz_stream(
        self,
        start_epoch_ms: int = 0,
        end_epoch_ms: Optional[int] = None
    ) -> Generator[bytes, None, None]:
        """Streaming gzip-compressed JSON generator covering all lifetime telemetry with zero memory bloat."""
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            header = f'{{"format":"BMS_LIFETIME_TELEMETRY_EXPORT_V2","exported_at":"{datetime.now(timezone.utc).isoformat()}","telemetry_points":['
            gz.write(header.encode("utf-8"))
            val = buf.getvalue()
            if val:
                yield val
                buf.seek(0)
                buf.truncate(0)

            conn = self._get_connection()
            first = True
            try:
                cur = conn.execute("""
                    SELECT * FROM telemetry_samples
                    WHERE epoch_ms >= ? AND epoch_ms <= ?
                    ORDER BY epoch_ms ASC;
                """, (start_epoch_ms, end_epoch_ms or int(time.time() * 1000)))

                while True:
                    rows = cur.fetchmany(500)
                    if not rows:
                        break
                    chunk_str = ""
                    for r in rows:
                        prefix = "" if first else ","
                        first = False
                        chunk_str += prefix + json.dumps(dict(r))
                    gz.write(chunk_str.encode("utf-8"))
                    val = buf.getvalue()
                    if val:
                        yield val
                        buf.seek(0)
                        buf.truncate(0)
            finally:
                conn.close()

            # Append top processes aggregation
            procs = self.query_top_processes(start_epoch_ms, end_epoch_ms or int(time.time() * 1000))
            procs_json = json.dumps(procs)
            footer = f'],"top_processes":{procs_json}}}'
            gz.write(footer.encode("utf-8"))
            val = buf.getvalue()
            if val:
                yield val
                buf.seek(0)
                buf.truncate(0)

        rem = buf.getvalue()
        if rem:
            yield rem

    def import_json(self, archive: Dict[str, Any]) -> Dict[str, Any]:
        """Imports retrospective JSON archive into SQLite WAL with deduplication."""
        points = archive.get("telemetry_points", [])
        if not points:
            return {"success": False, "imported": 0, "error": "No telemetry_points in archive"}

        count = 0
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    for p in points:
                        ep = p.get("epoch_ms")
                        if not ep:
                            continue
                        exists = conn.execute(
                            "SELECT 1 FROM telemetry_samples WHERE epoch_ms = ? LIMIT 1;",
                            (ep,)
                        ).fetchone()
                        if not exists:
                            conn.execute("""
                                INSERT INTO telemetry_samples (
                                    timestamp, epoch_ms, voltage_mv, current_ma, power_mw,
                                    charging, discharging, power_online,
                                    remaining_capacity_mwh, full_charge_capacity_mwh, design_capacity_mwh,
                                    soc_pct, accumulated_cycles, virtual_health_pct,
                                    cpu_temp_c, cpu_headroom_c, event_type
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                            """, (
                                p.get("timestamp", datetime.now(timezone.utc).isoformat()),
                                ep,
                                float(p.get("voltage_mv") or 0.0),
                                float(p.get("current_ma") or 0.0),
                                float(p.get("power_mw") or 0.0),
                                int(p.get("charging", 0)),
                                int(p.get("discharging", 0)),
                                int(p.get("power_online", 1)),
                                float(p.get("remaining_capacity_mwh") or 0.0),
                                float(p.get("full_charge_capacity_mwh") or 0.0),
                                float(p.get("design_capacity_mwh") or 0.0),
                                float(p.get("soc_pct") or 100.0),
                                str(p.get("accumulated_cycles") or "0.0"),
                                float(p.get("virtual_health_pct") or 100.0),
                                float(p.get("cpu_temp_c") or 45.0),
                                float(p.get("cpu_headroom_c") or 55.0),
                                str(p.get("event_type") or "IMPORTED_ARCHIVE")
                            ))
                            count += 1
            finally:
                conn.close()

        return {
            "success": True,
            "imported_points": count,
            "total_archive_points": len(points)
        }


# Singleton accessor
_STORAGE_ENGINE: Optional[BMSStorageEngine] = None
_STORAGE_LOCK = threading.Lock()


def get_storage_engine() -> BMSStorageEngine:
    """Returns singleton instance of BMSStorageEngine."""
    global _STORAGE_ENGINE
    with _STORAGE_LOCK:
        if _STORAGE_ENGINE is None:
            _STORAGE_ENGINE = BMSStorageEngine()
        return _STORAGE_ENGINE
