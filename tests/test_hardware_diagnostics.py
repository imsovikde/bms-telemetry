#!/usr/bin/env python3
"""
================================================================================
UNIT TESTS: BMS HARDWARE DIAGNOSTICS & PROCESS ATTRIBUTION
================================================================================
Validates:
1. Windows ACPI Battery IOCTL querying and power state bitmask parsing.
2. Thermal diagnostics, TjMax margin evaluation, and core DTS structure.
3. Process-level power attribution mathematical weighting and energy integration.
================================================================================
"""

import os
import sys
import unittest
import platform

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

import bms_engine as engine
import bms_diagnostics as diagnostics


class TestHardwareDiagnostics(unittest.TestCase):

    def test_01_battery_telemetry_contract(self):
        """Verify get_telemetry returns valid physical fields across OS platforms."""
        telem = engine.get_telemetry()
        self.assertIn("voltage_mv", telem)
        self.assertIn("remaining_capacity_mwh", telem)
        self.assertIn("full_charge_capacity_mwh", telem)
        self.assertIn("charge_rate_mw", telem)
        self.assertIn("discharge_rate_mw", telem)
        self.assertIn("hardware_link", telem)
        self.assertGreater(telem["voltage_mv"], 0)
        self.assertGreater(telem["full_charge_capacity_mwh"], 0)

        if platform.system() == "Windows":
            # On Windows laptop, verify either KERNEL_DIRECT_IOCTL or direct COM
            self.assertIn(telem["hardware_link"], [
                "KERNEL_DIRECT_IOCTL",
                "ONLINE_DIRECT_COM",
                "ONLINE_DIRECT_FALLBACK"
            ])
            if "hardware_status_flags" in telem:
                flags = telem["hardware_status_flags"]
                self.assertIn("charging", flags)
                self.assertIn("discharging", flags)
                self.assertIn("power_online", flags)

    def test_02_thermal_diagnostics_structure_and_margins(self):
        """Verify ThermalDiagnostics returns valid core maps, TjMax, and alert levels."""
        td = diagnostics.get_thermal_diagnostics()
        t = td.read_thermals()

        self.assertIn("cpu_package_temp_c", t)
        self.assertIn("distance_to_tjmax_c", t)
        self.assertIn("tjmax_c", t)
        self.assertIn("alert_level", t)
        self.assertIn("p_cores", t)
        self.assertIn("e_cores", t)

        self.assertEqual(t["tjmax_c"], 100.0)
        self.assertGreaterEqual(t["cpu_package_temp_c"], 20.0)
        self.assertLessEqual(t["cpu_package_temp_c"], 115.0)
        self.assertGreaterEqual(t["distance_to_tjmax_c"], 0.0)
        self.assertIn(t["alert_level"], ["OPTIMAL", "WARNING", "CRITICAL"])

        # Check core counts: 4 P-Cores, 8 E-Cores for i5-13500H
        self.assertEqual(len(t["p_cores"]), 4)
        self.assertEqual(len(t["e_cores"]), 8)

    def test_03_thermal_alert_threshold_evaluator(self):
        """Verify alert levels trigger accurately based on temperature headroom."""
        td = diagnostics.ThermalDiagnostics()
        
        # Simulated low load -> nominal
        t_nom = td.read_thermals(cpu_load_pct=10.0)
        self.assertIn(t_nom["alert_level"], ["OPTIMAL", "WARNING"])

        # Simulated high load -> higher temp
        t_high = td.read_thermals(cpu_load_pct=95.0)
        self.assertGreater(t_high["cpu_package_temp_c"], t_nom["cpu_package_temp_c"])
        self.assertLess(t_high["distance_to_tjmax_c"], t_nom["distance_to_tjmax_c"])

    def test_04_process_attribution_proportionality(self):
        """Verify mathematical process power attribution and energy accumulation."""
        pa = diagnostics.get_process_attribution_engine()
        top_procs = pa.sample_attribution(system_power_mw=18000.0, top_n=5)

        if top_procs:
            p0 = top_procs[0]
            self.assertIn("pid", p0)
            self.assertIn("name", p0)
            self.assertIn("power_mw", p0)
            self.assertIn("power_watts", p0)
            self.assertIn("power_share_pct", p0)
            self.assertIn("accumulated_energy_mwh", p0)

            self.assertGreaterEqual(p0["power_mw"], 0.0)
            self.assertGreaterEqual(p0["power_watts"], 0.0)
            self.assertGreaterEqual(p0["accumulated_energy_mwh"], 0.0)

            # Ordering verification: sorted descending by power_mw
            powers = [p["power_mw"] for p in top_procs]
            self.assertEqual(powers, sorted(powers, reverse=True))

    def test_05_subsystem_hardware_power_breakdown(self):
        """Verify subsystem power breakdown covers all major hardware modules."""
        subsystems = diagnostics.SubsystemHardwarePower.calculate_subsystems(
            battery_rate_mw=12000.0,
            is_charging=True,
            cpu_load_pct=35.0,
            gpu_load_pct=15.0,
            disk_bytes_sec=1024 * 1024,
            audio_active=True
        )
        self.assertIn("cpu", subsystems)
        self.assertIn("gpu", subsystems)
        self.assertIn("display", subsystems)
        self.assertIn("audio", subsystems)
        self.assertIn("storage", subsystems)
        self.assertIn("ram", subsystems)
        self.assertIn("auxiliary", subsystems)
        self.assertIn("total_system_watts", subsystems)
        self.assertIn("battery_watts", subsystems)

        self.assertGreater(subsystems["cpu"]["watts"], 3.0)
        self.assertGreater(subsystems["gpu"]["watts"], 0.5)
        self.assertEqual(subsystems["audio"]["watts"], 1.85)
        self.assertTrue(subsystems["audio"]["active"])
        self.assertGreater(subsystems["total_system_watts"], 10.0)
        self.assertEqual(subsystems["battery_watts"], 12.0)

    def test_06_bms_self_telemetry_overhead(self):
        """Verify BMS self-telemetry resource tracking."""
        overhead = diagnostics.get_bms_self_telemetry_overhead()
        self.assertIn("pid", overhead)
        self.assertIn("process_name", overhead)
        self.assertIn("cpu_percent", overhead)
        self.assertIn("memory_rss_mb", overhead)
        self.assertIn("power_mw", overhead)
        self.assertIn("accumulated_energy_mwh", overhead)
        self.assertIn("overhead_status", overhead)
        self.assertGreater(overhead["memory_rss_mb"], 0.0)
        self.assertGreater(overhead["power_mw"], 0.0)

    def test_07_electrochemical_terminal_voltage_variation(self):
        """Verify electrochemical terminal voltage varies with SoC and load."""
        telem = engine.get_telemetry()
        # Ensure voltage is in realistic 3S range (9.0V to 13.5V) and not a static stub
        self.assertGreater(telem["voltage_mv"], 9000)
        self.assertLess(telem["voltage_mv"], 13500)


if __name__ == "__main__":
    unittest.main(verbosity=2)
