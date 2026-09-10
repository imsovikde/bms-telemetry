#!/usr/bin/env python3
"""
================================================================================
BMS UI CONTRACT & STATIC FRONTEND VERIFICATION SUITE
================================================================================
Systematically validates that:
1. Static web assets exist in web/ (HTML, CSS, JS) with zero em-dashes.
2. The HTTP server serves static assets with proper Content-Type headers.
3. The backend API contracts (/api/status, /api/history, /api/export) are preserved.
4. Client-side JavaScript algorithms (format30, LTTB downsampling, SVG path construction)
   operate deterministically with zero NaN coordinates via headless Node.js.
================================================================================
"""

import os
import sys
import json
import unittest
import threading
import subprocess
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from http.server import ThreadingHTTPServer

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

import bms_engine as engine
import bms_ui


class TestUIFrontendContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Spin up ephemeral in-process HTTP server on free port."""
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), bms_ui.BMSHandler)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        """Shut down ephemeral HTTP server."""
        try:
            cls.server.shutdown()
            cls.server.server_close()
        except Exception:
            pass

    def setUp(self):
        self.web_dir = os.path.join(_ROOT, "web")

    def test_01_static_directory_structure_exists(self):
        """Verify all required isolated frontend assets exist in web/."""
        required_files = [
            "index.html",
            "css/tokens.css",
            "css/layout.css",
            "css/components.css",
            "js/state.js",
            "js/chart.js",
            "js/combobox.js",
            "js/calendar.js",
            "js/app.js"
        ]
        for rel_path in required_files:
            full_path = os.path.join(self.web_dir, rel_path)
            self.assertTrue(os.path.isfile(full_path), f"Missing required frontend asset: {rel_path}")

    def test_02_anti_slop_no_em_dashes_in_web_assets(self):
        """Verify that zero em-dashes (\u2014) or en-dashes (\u2013) exist in web/ files."""
        for root, _, files in os.walk(self.web_dir):
            for fname in files:
                if fname.endswith((".html", ".css", ".js", ".ts", ".json")):
                    fpath = os.path.join(root, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.assertEqual(content.count("\u2014"), 0, f"Em-dash found in {fpath}")
                    self.assertEqual(content.count("\u2013"), 0, f"En-dash found in {fpath}")

    def test_03_tokens_css_contains_shadcn_variables(self):
        """Verify tokens.css defines the complete Shadcn dark token palette."""
        tokens_file = os.path.join(self.web_dir, "css", "tokens.css")
        with open(tokens_file, "r", encoding="utf-8") as f:
            css = f.read()
        for token in ["--background", "--foreground", "--card", "--border", "--primary", "--safe", "--warn", "--danger", "--radius"]:
            self.assertIn(token, css, f"tokens.css missing design token: {token}")

    def test_04_zero_native_controls_in_html(self):
        """Verify index.html contains zero <select>, native <input type='date'>, or native checkboxes."""
        html_file = os.path.join(self.web_dir, "index.html")
        with open(html_file, "r", encoding="utf-8") as f:
            html = f.read().lower()
        self.assertNotIn("<select", html, "HTML contains forbidden native <select>")
        self.assertNotIn('type="date"', html, "HTML contains forbidden native date picker")
        self.assertNotIn('type="checkbox"', html, "HTML contains forbidden native checkbox")

    def test_05_backend_api_contracts_deterministic(self):
        """Verify backend functions produce deterministic schema without regressions."""
        state = engine.load_state()
        self.assertIn("accumulated_cycles", state)
        self.assertIn("state_of_charge_percentage", state)
        self.assertIn("virtual_health_percentage", state)
        self.assertEqual(len(str(state["accumulated_cycles"]).split(".")[1]), 30)

        telem = engine.get_telemetry()
        self.assertIn("voltage_mv", telem)
        self.assertIn("power_online", telem)
        self.assertIn("remaining_capacity_mwh", telem)
        if engine.is_windows() and "tag" in telem:
            self.assertIsInstance(telem["tag"], int)

        export_data = engine.export_lifetime_data()
        self.assertEqual(export_data.get("format"), "BMS_LIFETIME_ARCHIVE")
        self.assertIn("complete_history_ledger", export_data)

    def test_06_http_server_serves_static_assets(self):
        """Verify the server serves all static files with strict Content-Type headers."""
        asset_tests = [
            ("", "text/html; charset=utf-8"),
            ("index.html", "text/html; charset=utf-8"),
            ("css/tokens.css", "text/css; charset=utf-8"),
            ("css/layout.css", "text/css; charset=utf-8"),
            ("css/components.css", "text/css; charset=utf-8"),
            ("js/state.js", "application/javascript; charset=utf-8"),
            ("js/chart.js", "application/javascript; charset=utf-8"),
            ("js/combobox.js", "application/javascript; charset=utf-8"),
            ("js/calendar.js", "application/javascript; charset=utf-8"),
            ("js/app.js", "application/javascript; charset=utf-8"),
        ]
        for rel_path, expected_mime in asset_tests:
            url = f"{self.base_url}/{rel_path}"
            req = Request(url)
            with urlopen(req, timeout=3.0) as resp:
                self.assertEqual(resp.status, 200, f"HTTP status not 200 for {url}")
                content_type = resp.headers.get("Content-Type", "")
                self.assertEqual(content_type, expected_mime, f"MIME type mismatch for {url}: got {content_type}")
                body = resp.read()
                self.assertGreater(len(body), 50, f"Body too small for {url}")

    def test_07_http_server_serves_api_endpoints(self):
        """Verify /api/status, /api/history, and /api/export HTTP responses."""
        # /api/status
        with urlopen(f"{self.base_url}/api/status", timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers.get("Content-Type"), "application/json")
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("telemetry", data)
            self.assertIn("state", data)
            self.assertIn("hardware_identity", data)

        # /api/history
        with urlopen(f"{self.base_url}/api/history?preset=24h", timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers.get("Content-Type"), "application/json")
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "success")
            self.assertIn("points", data)
            self.assertIn("time_range", data)

        # /api/export
        with urlopen(f"{self.base_url}/api/export", timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("format"), "BMS_LIFETIME_ARCHIVE")

    def test_08_path_traversal_protection(self):
        """Verify directory traversal is strictly blocked."""
        traversal_urls = [
            f"{self.base_url}/../bms_engine.py",
            f"{self.base_url}/../../bms_engine.py",
        ]
        for url in traversal_urls:
            try:
                with urlopen(url, timeout=2.0) as resp:
                    # If it succeeded, it should not return engine code
                    body = resp.read().decode("utf-8", errors="ignore")
                    self.assertNotIn("NOMINAL_VOLTAGE_MV", body, "Path traversal succeeded and leaked bms_engine.py!")
            except HTTPError as e:
                self.assertIn(e.code, (400, 403, 404))

    def test_09_js_headless_algorithms_execution(self):
        """Execute headless Node.js tests for format30, LTTB, and SVG path generation."""
        import shutil
        if not shutil.which("node"):
            self.skipTest("Node.js not installed in current environment; skipping headless JS verification")
        test_script = os.path.join(_ROOT, "tests", "test_js_algorithms.mjs")
        proc = subprocess.run(
            ["node", test_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        self.assertEqual(proc.returncode, 0, f"Node.js tests failed: {proc.stderr}\n{proc.stdout}")
        self.assertIn("format30 verified", proc.stdout)
        self.assertIn("LTTB downsampling verified", proc.stdout)
        self.assertIn("SVG vector path builder verified", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
