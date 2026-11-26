import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from dg.alfred_items import emit, hint_row, row

PORT = 9201
SERVER_URL = "http://localhost:" + str(PORT) + "/mcp"
PROJECT_FILE = Path.home() / "dev" / "Dg.McpServer" / "Dg.McpServer" / "Dg.McpServer.csproj"
LOG_FILE = Path.home() / "Library" / "Logs" / "dg-mcp-server.log"
PROCESS_MARKER = "Dg.McpServer"
DOTNET_FALLBACK = "/usr/local/share/dotnet/dotnet"
# The same name is listed in ~/.claude/hooks/disable_work_mcps_in_private_repos.py, so private repos keep it off.
CLAUDE_SERVER_NAME = "dg-pilot"
CLAUDE_SETTINGS = Path.home() / ".claude.json"
CLAUDE_FALLBACK = "/opt/homebrew/bin/claude"
STARTUP_TIMEOUT_SECONDS = 120
SHUTDOWN_TIMEOUT_SECONDS = 15


def is_listening():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(("127.0.0.1", PORT)) == 0


def listening_pids():
    result = subprocess.run(
        ["lsof", "-nP", "-iTCP:" + str(PORT), "-sTCP:LISTEN", "-t"], capture_output=True, text=True, check=False
    )
    return [int(line) for line in result.stdout.split()]


def command_of(pid):
    result = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True, check=False)
    return result.stdout.strip()


def wait_until(condition, timeout_seconds):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.5)
    return condition()


def is_registered():
    try:
        settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return CLAUDE_SERVER_NAME in settings.get("mcpServers", {})


def claude(*arguments):
    binary = shutil.which("claude") or CLAUDE_FALLBACK
    try:
        result = subprocess.run([binary, "mcp", *arguments], capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return str(error)
    return "" if result.returncode == 0 else (result.stderr.strip() or result.stdout.strip()).splitlines()[0]


def register():
    if is_registered():
        return "in Claude Code registriert"
    failure = claude("add", "--transport", "http", "--scope", "user", CLAUDE_SERVER_NAME, SERVER_URL)
    return "Registrierung in Claude Code fehlgeschlagen: " + failure if failure else "in Claude Code registriert (ab der nächsten Session)"


def unregister():
    if not is_registered():
        return "nicht in Claude Code registriert"
    failure = claude("remove", "--scope", "user", CLAUDE_SERVER_NAME)
    return "Registrierung nicht entfernt: " + failure if failure else "aus Claude Code entfernt"


def start():
    # Registered only while running, so no session ever starts against a dead server.
    if is_listening():
        return "Dg MCP läuft schon auf Port " + str(PORT) + ", " + register()
    if not PROJECT_FILE.exists():
        return "Dg MCP: Projekt fehlt (" + str(PROJECT_FILE) + ")"
    dotnet = shutil.which("dotnet") or DOTNET_FALLBACK
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("ab") as log:
        server = subprocess.Popen(
            [dotnet, "run", "--project", str(PROJECT_FILE)],
            cwd=str(PROJECT_FILE.parent),
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    wait_until(lambda: is_listening() or server.poll() is not None, STARTUP_TIMEOUT_SECONDS)
    if is_listening():
        return "Dg MCP gestartet (" + SERVER_URL + "), " + register()
    if server.poll() is not None:
        return "Dg MCP ist beim Start ausgestiegen, Log: " + str(LOG_FILE)
    return "Dg MCP startet noch (Build?), Log: " + str(LOG_FILE)


def foreign_commands(pids):
    commands = [command_of(pid) for pid in pids]
    return [command for command in commands if PROCESS_MARKER not in command]


def stop():
    pids = listening_pids()
    if not pids:
        return "Dg MCP läuft nicht, " + unregister()
    foreign = foreign_commands(pids)
    if foreign:
        # Port 9201 answering does not prove it is our server, so a foreign process is never killed.
        return "Port " + str(PORT) + " gehört einem anderen Prozess, nicht gestoppt: " + foreign[0]
    for pid in pids:
        os.kill(pid, signal.SIGTERM)
    if wait_until(lambda: not is_listening(), SHUTDOWN_TIMEOUT_SECONDS):
        return "Dg MCP gestoppt, " + unregister()
    return "Dg MCP reagiert nicht auf SIGTERM (PID " + ", ".join(str(pid) for pid in pids) + ")"


def status():
    pids = listening_pids()
    registration = "in Claude Code registriert" if is_registered() else "nicht in Claude Code registriert"
    if not pids:
        return "Dg MCP läuft nicht, " + registration
    return "Dg MCP läuft auf Port " + str(PORT) + " (PID " + ", ".join(str(pid) for pid in pids) + "), " + registration


def action_rows(running):
    start_row = row("Start Dg MCP", "dotnet run auf " + SERVER_URL + ", registriert ihn in Claude Code", "start")
    stop_row = row("Stop Dg MCP", "Beendet den Server und entfernt ihn aus Claude Code", "stop")
    state = hint_row("Dg MCP läuft" if running else "Dg MCP läuft nicht", "Port " + str(PORT))
    return [state, stop_row, start_row] if running else [state, start_row, stop_row]


ACTIONS = {"start": start, "stop": stop, "status": status}


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "filter":
        emit(action_rows(is_listening()))
    elif action in ACTIONS:
        print(ACTIONS[action]())
    else:
        sys.exit("mcp_server: unbekannte Aktion " + action)


if __name__ == "__main__":
    main()
