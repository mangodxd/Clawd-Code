"""Tests for doctor module."""

import unittest
from pathlib import Path

from src.doctor import Doctor, DiagCheck, DiagReport, run_doctor


class TestDoctor(unittest.TestCase):
    """Test cases for diagnostic system."""

    def test_create_diag_check(self):
        """Test creating a diagnostic check."""
        check = DiagCheck(
            category="Test",
            name="Test Check",
            status="ok",
            message="Test message",
        )

        self.assertEqual(check.category, "Test")
        self.assertEqual(check.name, "Test Check")
        self.assertEqual(check.status, "ok")

    def test_create_diag_report(self):
        """Test creating a diagnostic report."""
        checks = [
            DiagCheck("Env", "Check 1", "ok", "OK"),
            DiagCheck("Env", "Check 2", "warning", "Warning"),
        ]

        report = DiagReport(checks=checks)

        self.assertEqual(len(report.checks), 2)
        self.assertEqual(report.summary(), {"ok": 1, "warning": 1, "error": 0})

    def test_diag_report_has_errors(self):
        """Test error detection."""
        report_ok = DiagReport(checks=[DiagCheck("Test", "Check", "ok", "OK")])
        report_error = DiagReport(
            checks=[DiagCheck("Test", "Check", "error", "Error")]
        )

        self.assertFalse(report_ok.has_errors())
        self.assertTrue(report_error.has_errors())

    def test_diag_report_has_warnings(self):
        """Test warning detection."""
        report_ok = DiagReport(checks=[DiagCheck("Test", "Check", "ok", "OK")])
        report_warning = DiagReport(
            checks=[DiagCheck("Test", "Check", "warning", "Warning")]
        )

        self.assertFalse(report_ok.has_warnings())
        self.assertTrue(report_warning.has_warnings())

    def test_diag_report_markdown(self):
        """Test markdown rendering."""
        report = DiagReport(
            checks=[
                DiagCheck("Environment", "Python", "ok", "Python 3.11"),
                DiagCheck("Permissions", "API Key", "warning", "Not set"),
            ]
        )

        md = report.as_markdown()

        self.assertIn("# Diagnostic Report", md)
        self.assertIn("## Summary", md)
        self.assertIn("Python 3.11", md)
        self.assertIn("Not set", md)

    def test_run_doctor(self):
        """Test running diagnostics."""
        report = run_doctor()

        self.assertIsInstance(report, DiagReport)
        self.assertGreater(len(report.checks), 0)

        # Should have environment checks
        env_checks = [c for c in report.checks if c.category == "Environment"]
        self.assertGreater(len(env_checks), 0)

    def test_doctor_python_version_check(self):
        """Test Python version check."""
        doctor = Doctor()
        doctor._Check_python_version()

        self.assertEqual(len(doctor.checks), 1)
        check = doctor.checks[0]
        self.assertEqual(check.category, "Environment")
        self.assertEqual(check.name, "Python Version")

    def test_doctor_platform_check(self):
        """Test platform check."""
        doctor = Doctor()
        doctor._check_platform()

        self.assertEqual(len(doctor.checks), 1)
        check = doctor.checks[0]
        self.assertEqual(check.category, "Environment")
        self.assertEqual(check.name, "Platform")

    def test_doctor_dependencies_check(self):
        """Test dependencies check."""
        doctor = Doctor()
        doctor._check_dependencies()

        self.assertEqual(len(doctor.checks), 1)
        check = doctor.checks[0]
        self.assertEqual(check.category, "Environment")
        self.assertEqual(check.name, "Dependencies")

    def test_doctor_api_keys_check(self):
        """Test API keys check."""
        doctor = Doctor()
        doctor._check_api_keys()

        self.assertEqual(len(doctor.checks), 1)
        check = doctor.checks[0]
        self.assertEqual(check.category, "Permissions")
        self.assertEqual(check.name, "API Keys")

    def test_doctor_file_access_check(self):
        """Test file access check."""
        doctor = Doctor()
        doctor._check_file_access()

        self.assertEqual(len(doctor.checks), 1)
        check = doctor.checks[0]
        self.assertEqual(check.category, "Permissions")
        self.assertEqual(check.name, "File Access")

    def test_doctor_configuration_check(self):
        """Test configuration check."""
        doctor = Doctor()
        doctor._check_configuration()

        self.assertEqual(len(doctor.checks), 1)
        check = doctor.checks[0]
        self.assertEqual(check.category, "Configuration")
        self.assertEqual(check.name, "Config Files")


if __name__ == "__main__":
    unittest.main()
