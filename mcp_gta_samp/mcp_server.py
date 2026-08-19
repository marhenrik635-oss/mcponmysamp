from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .command_discovery import discover_commands
from .headless import HeadlessClient
from .openmp import OpenMpServer


def create_mcp_server(
    server: OpenMpServer,
    client: HeadlessClient | None = None,
    gamemode_source: Path | str | None = None,
) -> FastMCP:
    app = FastMCP("mcp-gta-samp", instructions="Control only a local or owned open.mp test server.")
    commands = discover_commands(gamemode_source) if gamemode_source else []

    @app.tool(description="Start the configured local open.mp test server and wait for readiness.")
    def server_start() -> dict[str, bool]:
        return server.start()

    @app.tool(description="Stop the configured local open.mp test server.")
    def server_stop() -> dict[str, bool]:
        return server.stop()

    @app.tool(description="Return local open.mp test server process status.")
    def server_status() -> dict[str, int | bool | None]:
        return server.status()

    if gamemode_source:
        @app.tool(description="List slash commands discovered in the configured Pawn gamemode.")
        def server_list_commands() -> dict[str, list[str]]:
            return {"commands": commands}

        @app.tool(description="Check whether a slash command is discovered and allowlisted.")
        def server_assert_command(command: str) -> dict[str, bool | str]:
            command = command.strip()
            if command not in commands:
                raise ValueError(f"command not discovered: {command}")
            return {"command": command, "allowed": True}

    if client is not None:
        @app.tool(description="Start the configured headless game client.")
        def client_start() -> dict[str, bool]:
            client.start()
            return {"running": client.running}

        @app.tool(description="Stop the configured headless game client.")
        def client_stop() -> dict[str, bool]:
            client.stop()
            return {"running": client.running}

        @app.tool(description="Return headless game client status.")
        def client_status() -> dict[str, bool]:
            return {"running": client.running}

        @app.tool(description="Send an allowlisted slash command to the headless game client.")
        def client_send_chat(command: str) -> dict[str, str]:
            command = command.strip()
            if commands and command not in commands:
                raise ValueError(f"command not discovered: {command}")
            return {"command": command, "output": client.send_chat_after_spawn(command)}

        @app.tool(description="Return buffered headless client output lines.")
        def client_get_history() -> dict[str, list[str]]:
            return {"lines": client.history()}

        @app.tool(description="Assert buffered headless output contains text.")
        def client_assert_output(text: str) -> dict[str, bool | str]:
            if not client.history_contains(text):
                raise AssertionError(f"Missing text: {text}")
            return {"found": True, "text": text}

    return app


# ponytail: source-derived allowlist; runtime command metadata comes later.