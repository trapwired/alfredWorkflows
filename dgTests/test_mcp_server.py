import unittest
from unittest import mock

from dg import mcp_server

OWN_SERVER = "/Users/x/dev/Dg.McpServer/bin/Debug/net9.0/Dg.McpServer"


def patched(**replacements):
    return mock.patch.multiple(mcp_server, **replacements)


class Stop(unittest.TestCase):
    def test_not_running_kills_nothing_but_clears_a_stale_registration(self):
        unregister = mock.Mock(return_value="aus Claude Code entfernt")
        with patched(listening_pids=lambda: [], unregister=unregister), mock.patch.object(mcp_server.os, "kill") as kill:
            message = mcp_server.stop()

        self.assertEqual(message, "Dg MCP läuft nicht, aus Claude Code entfernt")
        kill.assert_not_called()

    def test_foreign_process_on_the_port_is_never_killed_and_stays_registered(self):
        unregister = mock.Mock()
        with patched(
            listening_pids=lambda: [4711],
            command_of=lambda pid: "/usr/bin/python3 -m http.server 9201",
            unregister=unregister,
        ), mock.patch.object(mcp_server.os, "kill") as kill:
            message = mcp_server.stop()

        self.assertIn("anderen Prozess", message)
        self.assertIn("http.server", message)
        kill.assert_not_called()
        unregister.assert_not_called()

    def test_own_server_gets_sigterm_and_is_unregistered(self):
        with patched(
            listening_pids=lambda: [4711],
            command_of=lambda pid: OWN_SERVER,
            is_listening=lambda: False,
            unregister=lambda: "aus Claude Code entfernt",
        ), mock.patch.object(mcp_server.os, "kill") as kill:
            message = mcp_server.stop()

        self.assertEqual(message, "Dg MCP gestoppt, aus Claude Code entfernt")
        kill.assert_called_once_with(4711, mcp_server.signal.SIGTERM)

    def test_server_that_ignores_sigterm_stays_registered(self):
        unregister = mock.Mock()
        with patched(
            listening_pids=lambda: [4711],
            command_of=lambda pid: OWN_SERVER,
            is_listening=lambda: True,
            unregister=unregister,
            SHUTDOWN_TIMEOUT_SECONDS=0,
        ), mock.patch.object(mcp_server.os, "kill"):
            message = mcp_server.stop()

        self.assertIn("reagiert nicht", message)
        unregister.assert_not_called()


class Start(unittest.TestCase):
    def test_already_running_starts_no_second_server_but_ensures_registration(self):
        with patched(is_listening=lambda: True, register=lambda: "in Claude Code registriert"), mock.patch.object(
            mcp_server.subprocess, "Popen"
        ) as popen:
            message = mcp_server.start()

        self.assertEqual(message, "Dg MCP läuft schon auf Port 9201, in Claude Code registriert")
        popen.assert_not_called()

    def test_server_that_exits_during_start_is_not_registered(self):
        exited = mock.Mock()
        exited.poll.return_value = 1
        register = mock.Mock()
        with patched(is_listening=lambda: False, register=register), mock.patch.object(
            mcp_server.subprocess, "Popen", return_value=exited
        ), mock.patch.object(mcp_server.Path, "open", mock.mock_open()), mock.patch.object(mcp_server.Path, "mkdir"):
            message = mcp_server.start()

        self.assertIn("beim Start ausgestiegen", message)
        register.assert_not_called()


class Registration(unittest.TestCase):
    def test_register_adds_the_server_user_wide_under_the_name_the_hook_knows(self):
        claude = mock.Mock(return_value="")
        with patched(is_registered=lambda: False, claude=claude):
            message = mcp_server.register()

        claude.assert_called_once_with(
            "add", "--transport", "http", "--scope", "user", "dg-pilot", "http://localhost:9201/mcp"
        )
        self.assertIn("registriert", message)

    def test_register_is_a_no_op_when_already_registered(self):
        claude = mock.Mock()
        with patched(is_registered=lambda: True, claude=claude):
            mcp_server.register()

        claude.assert_not_called()

    def test_failed_registration_is_reported(self):
        with patched(is_registered=lambda: False, claude=lambda *arguments: "boom"):
            message = mcp_server.register()

        self.assertEqual(message, "Registrierung in Claude Code fehlgeschlagen: boom")

    def test_unregister_removes_only_an_existing_registration(self):
        claude = mock.Mock(return_value="")
        with patched(is_registered=lambda: True, claude=claude):
            self.assertEqual(mcp_server.unregister(), "aus Claude Code entfernt")
        claude.assert_called_once_with("remove", "--scope", "user", "dg-pilot")

        claude.reset_mock()
        with patched(is_registered=lambda: False, claude=claude):
            mcp_server.unregister()
        claude.assert_not_called()


class ActionRows(unittest.TestCase):
    def test_applicable_action_comes_first(self):
        self.assertEqual([item.get("arg") for item in mcp_server.action_rows(running=False)], [None, "start", "stop"])
        self.assertEqual([item.get("arg") for item in mcp_server.action_rows(running=True)], [None, "stop", "start"])


if __name__ == "__main__":
    unittest.main()
