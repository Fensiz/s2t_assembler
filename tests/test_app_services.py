from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from s2t_tool.app.lifecycle import UpdateCheckResult
from s2t_tool.app.operations import AppOperationsService
from s2t_tool.app.recent import RecentItemsService
from s2t_tool.app.update_flow import AppUpdateFlowService
from s2t_tool.use_cases.results import GetResult, PutResult, RecentItem


class AppOperationsServiceTests(unittest.TestCase):
    def test_run_get_builds_get_command_and_returns_result(self) -> None:
        expected = GetResult(
            product_name="demo",
            output_excel=Path("/tmp/demo.xlsx"),
            diff_mode=True,
        )
        service = Mock()
        service.handle_get.return_value = expected

        result = AppOperationsService(service).run_get(
            product_name="demo",
            branch="s2t/master",
            version="2.0",
            diff_commit="abc1234",
            logger="logger",
        )

        self.assertEqual(result, expected)
        command = service.handle_get.call_args.args[0]
        self.assertEqual(command.product_name, "demo")
        self.assertEqual(command.branch_arg, "s2t/master")
        self.assertEqual(command.version_arg, "2.0")
        self.assertEqual(command.diff_commit_arg, "abc1234")
        self.assertEqual(command.logger, "logger")

    def test_run_put_builds_put_command_and_returns_result(self) -> None:
        expected = PutResult(
            product_name="demo",
            repo_dir=Path("/tmp/repo"),
            version="2.0",
            changed=True,
        )
        service = Mock()
        service.handle_put.return_value = expected

        result = AppOperationsService(service).run_put(
            product_name="demo",
            branch="s2t/master",
            version="2.0",
            keep_version=True,
            format_sql=True,
            excel_path="/tmp/demo.xlsx",
            commit_message="message",
            logger="logger",
        )

        self.assertEqual(result, expected)
        command = service.handle_put.call_args.args[0]
        self.assertEqual(command.product_name, "demo")
        self.assertEqual(command.branch_arg, "s2t/master")
        self.assertEqual(command.version_arg, "2.0")
        self.assertTrue(command.keep_version)
        self.assertTrue(command.format_sql)
        self.assertEqual(command.excel_arg, "/tmp/demo.xlsx")
        self.assertEqual(command.commit_message_arg, "message")
        self.assertEqual(command.logger, "logger")


class RecentItemsServiceTests(unittest.TestCase):
    def test_build_view_data_returns_items_and_labels(self) -> None:
        gateway = Mock()
        gateway.load.return_value = [
            RecentItem(product_name="a", branch="main"),
            RecentItem(product_name="b", branch=""),
        ]
        gateway.label.side_effect = lambda item: f"{item.product_name}:{item.branch}"

        result = RecentItemsService(gateway).build_view_data()

        self.assertEqual(
            result.items,
            [RecentItem(product_name="a", branch="main"), RecentItem(product_name="b", branch="")],
        )
        self.assertEqual(result.labels, ["a:main", "b:"])

    def test_add_recent_deduplicates_and_persists(self) -> None:
        gateway = Mock()
        gateway.load.return_value = [
            RecentItem(product_name="a", branch="main"),
            RecentItem(product_name="b", branch="dev"),
            RecentItem(product_name="a", branch="main"),
        ]
        gateway.label.side_effect = lambda item: f"{item.product_name}:{item.branch}"

        result = RecentItemsService(gateway).add_recent("a", "main")

        self.assertEqual(
            result.items,
            [
                RecentItem(product_name="a", branch="main"),
                RecentItem(product_name="b", branch="dev"),
            ],
        )
        gateway.save.assert_called_once_with(result.items)
        self.assertEqual(result.labels, ["a:main", "b:dev"])

    def test_get_by_index_returns_none_for_invalid_index(self) -> None:
        gateway = Mock()
        gateway.load.return_value = [RecentItem(product_name="a", branch="main")]
        service = RecentItemsService(gateway)

        self.assertIsNone(service.get_by_index(-1))
        self.assertIsNone(service.get_by_index(1))
        self.assertEqual(service.get_by_index(0), RecentItem(product_name="a", branch="main"))


class AppUpdateFlowServiceTests(unittest.TestCase):
    def test_check_updates_delegates_and_sets_logger(self) -> None:
        lifecycle = Mock()
        lifecycle.check_updates.return_value = UpdateCheckResult(True, "1.2.3")

        result = AppUpdateFlowService(lifecycle).check_updates(logger="logger")

        self.assertEqual(result, UpdateCheckResult(True, "1.2.3"))
        self.assertEqual(lifecycle.update_service.logger, "logger")
        lifecycle.check_updates.assert_called_once_with()

    def test_install_update_delegates_and_sets_logger(self) -> None:
        lifecycle = Mock()
        lifecycle.install_update.return_value = Path("/tmp/current.pyz")

        result = AppUpdateFlowService(lifecycle).install_update(logger="logger")

        self.assertEqual(result, Path("/tmp/current.pyz"))
        self.assertEqual(lifecycle.update_service.logger, "logger")
        lifecycle.install_update.assert_called_once_with()

    def test_restart_updated_app_uses_detached_launcher(self) -> None:
        lifecycle = Mock()
        service = AppUpdateFlowService(lifecycle)

        with patch("s2t_tool.app.update_flow.launch_app_detached", return_value=["python3", "/tmp/app.pyz"]) as launcher:
            result = service.restart_updated_app(Path("/tmp/app.pyz"), logger="logger")

        self.assertEqual(result, ["python3", "/tmp/app.pyz"])
        launcher.assert_called_once_with(Path("/tmp/app.pyz"), logger="logger")

    def test_detect_running_app_delegates_to_runtime_helper(self) -> None:
        lifecycle = Mock()
        service = AppUpdateFlowService(lifecycle)

        with patch("s2t_tool.app.update_flow.detect_running_app_path", return_value=Path("/tmp/app.pyz")) as detector:
            result = service.detect_running_app()

        self.assertEqual(result, Path("/tmp/app.pyz"))
        detector.assert_called_once_with()

    def test_adopt_external_app_delegates_and_sets_logger(self) -> None:
        lifecycle = Mock()
        lifecycle.update_service.adopt_external_app.return_value = Path("/tmp/current.pyz")

        result = AppUpdateFlowService(lifecycle).adopt_external_app(Path("/tmp/app.pyz"), logger="logger")

        self.assertEqual(result, Path("/tmp/current.pyz"))
        self.assertEqual(lifecycle.update_service.logger, "logger")
        lifecycle.update_service.adopt_external_app.assert_called_once_with(Path("/tmp/app.pyz"))


if __name__ == "__main__":
    unittest.main()
