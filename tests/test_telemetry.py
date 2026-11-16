"""Unit tests for COLAB-HUD telemetry and CLI."""

from __future__ import annotations

import builtins
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from desktop import cli, telemetry


class TestColabHudTelemetry(unittest.TestCase):
    def test_unauthenticated_never_prompts_stdin(self) -> None:
        telemetry.bootstrap_colab_cli()
        with (
            patch("colab_cli.auth._get_token_from_keyring", return_value=None),
            patch("colab_cli.auth.LEGACY_TOKEN_PATH", "__nonexistent_colab_token__.json"),
            patch.object(builtins, "input", side_effect=AssertionError("input() called during polling")),
        ):
            creds, auth_state, err_msg, fp = telemetry.load_cached_credentials()
            self.assertIsNone(creds)
            self.assertEqual(auth_state, "unauthenticated")
            self.assertIsNotNone(err_msg)
            self.assertIsNone(fp)

            snap = telemetry.fetch_snapshot()
            self.assertFalse(snap["authenticated"])
            self.assertEqual(snap["auth_state"], "unauthenticated")
            self.assertEqual(snap["runtimes"], [])

    def test_format_runtime_summary_variants(self) -> None:
        self.assertEqual(telemetry.format_runtime_summary("NONE", "DEFAULT", "Standard"), "CPU")
        self.assertEqual(telemetry.format_runtime_summary("T4", "GPU", "Standard"), "T4 GPU")
        self.assertEqual(telemetry.format_runtime_summary("A100", "GPU", "High-RAM"), "A100 GPU · High-RAM")
        self.assertEqual(telemetry.format_runtime_summary("V5E1", "TPU", "Standard"), "TPU v5e-1")

    def test_extract_probe_json(self) -> None:
        outputs = [
            {"output_type": "stream", "text": 'hello\n__COLAB_HUD_PROBE__{"gpu_name": "NVIDIA L4", "gpu_count": 1}\n'},
        ]
        parsed = telemetry._extract_probe_json(outputs)
        self.assertEqual(parsed, {"gpu_name": "NVIDIA L4", "gpu_count": 1})

    def test_fetch_snapshot_with_active_gpu_and_probe(self) -> None:
        telemetry.bootstrap_colab_cli()
        from colab_cli.client import Accelerator, AssignmentVariant, Shape
        from colab_cli.consumption import ConsumptionUserInfo

        fake_usage = ConsumptionUserInfo(
            paidComputeUnitsBalance=198.5,
            consumptionRateHourly=13.08,
            assignmentsCount=1,
        )
        fake_assignment = SimpleNamespace(
            accelerator=Accelerator.A100,
            variant=AssignmentVariant.GPU,
            machine_shape=Shape.HIGH_RAM,
            endpoint="ep-a100-01",
            runtime_proxy_info=SimpleNamespace(
                url="https://proxy.example.invalid",
                token="tok-123",
                token_expires_in_seconds=3600,
            ),
        )
        cached_probe = {
            "ep-a100-01": {
                "gpu_name": "NVIDIA A100-SXM4-40GB",
                "gpu_count": 1,
                "vram_used_mb": 1024.0,
                "vram_total_mb": 40960.0,
                "gpu_util_pct": 12.0,
                "ram_used_gb": 4.2,
                "ram_total_gb": 83.48,
                "cpu_count": 12,
                "disk_used_gb": 38.0,
                "disk_total_gb": 235.0,
            }
        }

        mock_client = MagicMock()
        mock_client.get_consumption_user_info.return_value = fake_usage
        mock_client.list_assignments.return_value = [fake_assignment]

        with (
            patch("desktop.telemetry.load_cached_credentials", return_value=(MagicMock(), "ok", None, "fp123")),
            patch("google.auth.transport.requests.AuthorizedSession", return_value=MagicMock()),
            patch("colab_cli.client.Client", return_value=mock_client),
            patch("desktop.telemetry._resolve_account_email", return_value="naino@example.com"),
            patch("desktop.telemetry._inspect_proxy_kernels", return_value=(1, "idle", "kid-1")),
            patch("desktop.telemetry._load_probe_cache", return_value=cached_probe),
        ):
            snap = telemetry.fetch_snapshot()

        self.assertTrue(snap["authenticated"])
        self.assertEqual(snap["account_email"], "naino@example.com")
        self.assertEqual(snap["balance_cu"], 198.5)
        self.assertEqual(snap["rate_cu_hr"], 13.08)
        self.assertEqual(snap["est_hours_left"], round(198.5 / 13.08, 2))
        self.assertEqual(len(snap["runtimes"]), 1)
        rt = snap["runtimes"][0]
        self.assertEqual(rt["summary_label"], "A100 GPU · High-RAM")
        self.assertEqual(rt["kernel_state"], "idle")
        self.assertEqual(rt["probe"]["gpu_name"], "NVIDIA A100-SXM4-40GB")

        summary = cli.format_cli_table(snap)
        self.assertIn("198.5 CU", summary)
        self.assertIn("A100 GPU · High-RAM", summary)
        self.assertIn("NVIDIA A100-SXM4-40GB", summary)

    def test_probe_busy_kernel_skips_when_not_forced(self) -> None:
        telemetry.bootstrap_colab_cli()
        from colab_cli.client import Accelerator, AssignmentVariant, Shape

        fake_assignment = SimpleNamespace(
            accelerator=Accelerator.T4,
            variant=AssignmentVariant.GPU,
            machine_shape=Shape.STANDARD,
            endpoint="ep-t4-busy",
            runtime_proxy_info=SimpleNamespace(url="https://proxy.example.invalid", token="tok"),
        )
        mock_client = MagicMock()
        mock_client.list_assignments.return_value = [fake_assignment]

        with (
            patch("desktop.telemetry.load_cached_credentials", return_value=(MagicMock(), "ok", None, "fp")),
            patch("google.auth.transport.requests.AuthorizedSession", return_value=MagicMock()),
            patch("colab_cli.client.Client", return_value=mock_client),
            patch("desktop.telemetry._inspect_proxy_kernels", return_value=(1, "busy", None)),
        ):
            res = telemetry.probe_runtime_hardware(force=False)

        self.assertFalse(res["ok"])
        self.assertTrue(res.get("busy"))

    def test_cli_json_outputs_valid_json(self) -> None:
        buf = io.StringIO()
        sample_snap = {"authenticated": False, "auth_state": "unauthenticated", "runtimes": []}
        with patch("desktop.cli.fetch_snapshot", return_value=sample_snap), redirect_stdout(buf):
            rc = cli.main(["--json", "--no-kernel-check"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(buf.getvalue()), sample_snap)

    def test_oauth_begin_and_complete(self) -> None:
        telemetry.bootstrap_colab_cli()
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "ok"}'
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = ("https://accounts.google.com/o/oauth2/auth?x=1", "st")
        mock_flow.fetch_token.return_value = {"scope": ["openid"]}
        mock_flow.credentials = mock_creds
        mock_flow.oauth2session = MagicMock()

        with (
            patch("desktop.telemetry._load_oauth_client_config", return_value={"installed": {"client_id": "id"}}),
            patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_config", return_value=mock_flow),
            patch("colab_cli.auth._save_token_to_keyring") as save_mock,
            patch("colab_cli.auth._remove_legacy_token"),
        ):
            flow, auth_url = telemetry.begin_oauth_flow(switch_account=False)
            self.assertTrue(auth_url.startswith("https://accounts.google.com/"))
            res = telemetry.complete_oauth_flow(flow, "  4/0A-TEST-CODE  ")
            self.assertEqual(res, {"ok": True})
            mock_flow.fetch_token.assert_called_once_with(code="4/0A-TEST-CODE")
            save_mock.assert_called_once_with('{"token": "ok"}')

    def test_pill_skips_redundant_redraws(self) -> None:
        from desktop.hud_pill import ColabHudPill

        store = telemetry.ColabTelemetryStore(interval_sec=60)
        pill = ColabHudPill(store=store, lang="zh", alpha=0.94, refresh_ms=1000)
        try:
            snap1 = {
                "authenticated": False,
                "auth_state": "unauthenticated",
                "account_email": None,
                "timestamp_ms": 1000,
                "balance_cu": None,
                "rate_cu_hr": None,
                "assignments_count": 0,
                "est_hours_left": None,
                "runtimes": [],
                "error": "Not signed in",
            }
            pill._render_snapshot(snap1)
            children_first = list(pill.hw_body.winfo_children())

            # Newer poll with identical values should not destroy/recreate runtime widgets.
            snap2 = dict(snap1, timestamp_ms=11000)
            pill._render_snapshot(snap2)
            self.assertEqual(list(pill.hw_body.winfo_children()), children_first)

            # _poll_ui with unchanged snapshot timestamp should skip _render_snapshot completely.
            with (
                patch.object(store, "get_snapshot", return_value=snap2),
                patch.object(pill, "_render_snapshot") as render_mock,
            ):
                pill._poll_ui()
                render_mock.assert_not_called()
        finally:
            pill.close()


if __name__ == "__main__":
    unittest.main()
