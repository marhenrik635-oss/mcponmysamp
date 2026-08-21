from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .command_discovery import discover_commands
from .headless import HeadlessClient
from .openmp import OpenMpServer
from .remote import RemoteControl, RemoteControlError


def create_mcp_server(
    server: OpenMpServer,
    client: HeadlessClient | None = None,
    gamemode_source: Path | str | None = None,
    remote: RemoteControl | None = None,
) -> FastMCP:
    app = FastMCP("mcp-gta-samp", instructions="Control only a local or owned open.mp test server.")
    commands = discover_commands(gamemode_source) if gamemode_source else []

    def annotate(*, read_only: bool, destructive: bool = False, idempotent: bool = False, open_world: bool = False):
        return ToolAnnotations(
            readOnlyHint=read_only,
            destructiveHint=destructive,
            idempotentHint=idempotent,
            openWorldHint=open_world,
        )

    @app.tool(description="Start the configured local open.mp test server and wait for readiness.", annotations=annotate(read_only=False, idempotent=True))
    def server_start() -> dict[str, bool]:
        return server.start()

    @app.tool(description="Stop the configured local open.mp test server.", annotations=annotate(read_only=False, destructive=True))
    def server_stop() -> dict[str, bool]:
        return server.stop()

    @app.tool(description="Return local open.mp test server process status.", annotations=annotate(read_only=True))
    def server_status() -> dict[str, int | bool | None]:
        return server.status()

    if gamemode_source:
        @app.tool(description="List slash commands discovered in the configured Pawn gamemode.", annotations=annotate(read_only=True))
        def server_list_commands() -> dict[str, list[str]]:
            return {"commands": commands}

        @app.tool(description="Check whether a slash command is discovered and allowlisted.", annotations=annotate(read_only=True))
        def server_assert_command(command: str) -> dict[str, bool | str]:
            command = command.strip()
            if command not in commands:
                raise ValueError(f"command not discovered: {command}")
            return {"command": command, "allowed": True}

    if client is not None:
        @app.tool(description="Start the configured headless game client.", annotations=annotate(read_only=False, idempotent=True))
        def client_start() -> dict[str, bool]:
            client.start()
            return {"running": client.running}

        @app.tool(description="Stop the configured headless game client.", annotations=annotate(read_only=False, destructive=True))
        def client_stop() -> dict[str, bool]:
            client.stop()
            return {"running": client.running}

        @app.tool(description="Return headless game client status.", annotations=annotate(read_only=True))
        def client_status() -> dict[str, bool]:
            return {"running": client.running}

        @app.tool(description="Send an allowlisted slash command to the headless game client.", annotations=annotate(read_only=False))
        def client_send_chat(command: str) -> dict[str, str]:
            command = command.strip()
            if commands and command not in commands:
                raise ValueError(f"command not discovered: {command}")
            return {"command": command, "output": client.send_chat_after_spawn(command)}

        @app.tool(description="Return buffered headless client output lines.", annotations=annotate(read_only=True))
        def client_get_history() -> dict[str, list[str]]:
            return {"lines": client.history()}

        @app.tool(description="Assert buffered headless output contains text.", annotations=annotate(read_only=True))
        def client_assert_output(text: str) -> dict[str, bool | str]:
            if not client.history_contains(text):
                raise AssertionError(f"Missing text: {text}")
            return {"found": True, "text": text}

    if remote is not None:
        @app.tool(description="Walk to a world position over the navmesh (walk/jog/sprint/direct).", annotations=annotate(read_only=False))
        def bot_walk_to(x: float, y: float, z: float, mode: str = "jog") -> dict[str, bool]:
            remote.walk_to(x, y, z, mode)
            return {"ok": True}

        @app.tool(description="Stop the current navmesh walk.", annotations=annotate(read_only=False, idempotent=True))
        def bot_stop() -> dict[str, bool]:
            remote.walk_stop()
            return {"ok": True}

        @app.tool(description="Teleport to a world position (client-side, no anti-cheat bypass).", annotations=annotate(read_only=False))
        def bot_teleport(x: float, y: float, z: float) -> dict[str, bool]:
            remote.teleport(x, y, z)
            return {"ok": True}

        @app.tool(description="Face a heading in degrees (0 = north/+Y, 90 = east/+X, clockwise).", annotations=annotate(read_only=False, idempotent=True))
        def bot_face_heading(heading: float) -> dict[str, bool]:
            remote.face_heading(heading)
            return {"ok": True}

        @app.tool(description="Face a world point.", annotations=annotate(read_only=False, idempotent=True))
        def bot_face_point(x: float, y: float) -> dict[str, bool]:
            remote.face_point(x, y)
            return {"ok": True}

        @app.tool(description="Pulse a jump key (hold->sync->release->sync).", annotations=annotate(read_only=False))
        def bot_jump() -> dict[str, bool]:
            remote.jump()
            return {"ok": True}

        @app.tool(description="Get current bot world position.", annotations=annotate(read_only=True))
        def bot_get_position() -> dict[str, float]:
            x, y, z = remote.position()
            return {"x": x, "y": y, "z": z}

        @app.tool(description="Get current bot heading in degrees.", annotations=annotate(read_only=True))
        def bot_get_rotation() -> dict[str, float]:
            return {"heading": remote.rotation()}

        @app.tool(description="Check whether the bot is currently walking.", annotations=annotate(read_only=True))
        def bot_is_walking() -> dict[str, bool]:
            return {"walking": remote.is_walking()}

        @app.tool(description="Liveness probe for the remote control script bridge.", annotations=annotate(read_only=True))
        def bot_ping() -> dict[str, str]:
            if remote.ping():
                return {"status": "alive"}
            raise RemoteControlError("remote control bridge is not responding")

        @app.tool(description="List streamed-in players around the bot (id, x, y, z).", annotations=annotate(read_only=True))
        def bot_scan_players() -> dict[str, list[dict[str, float]]]:
            return {"players": remote.scan_players()}

        @app.tool(description="List streamed-in vehicles around the bot (id, x, y, z).", annotations=annotate(read_only=True))
        def bot_scan_vehicles() -> dict[str, list[dict[str, float]]]:
            return {"vehicles": remote.scan_vehicles()}

        @app.tool(description="Get bot health and armour via server round-trip.", annotations=annotate(read_only=True))
        def bot_get_health() -> dict[str, float]:
            hp, armor = remote.health(client)
            return {"health": hp, "armour": armor}

        @app.tool(description="Hold a movement/action key (8=sprint, 4=fire, 128=crouch, 32=jump) until bot_key_release.", annotations=annotate(read_only=False))
        def bot_key_hold(mask: int) -> dict[str, bool]:
            remote.key_hold(mask)
            return {"ok": True}

        @app.tool(description="Release all held keys.", annotations=annotate(read_only=False, idempotent=True))
        def bot_key_release() -> dict[str, bool]:
            remote.key_release()
            return {"ok": True}

        @app.tool(description="Enter a vehicle by id (seat 0=driver, 1=passenger). Sends EnterVehicle RPC.", annotations=annotate(read_only=False))
        def bot_enter_vehicle(vehicle_id: int, seat: int = 0) -> dict[str, bool]:
            remote.enter_vehicle(vehicle_id, seat)
            return {"ok": True}

        @app.tool(description="Exit the current vehicle. Sends ExitVehicle RPC.", annotations=annotate(read_only=False))
        def bot_exit_vehicle() -> dict[str, bool]:
            remote.exit_vehicle()
            return {"ok": True}

        @app.tool(description="Get current vehicle id (0 = on foot).", annotations=annotate(read_only=True))
        def bot_get_vehicle() -> dict[str, int]:
            return {"vehicle": remote.vehicle_id()}

        @app.tool(description="Send a plain chat line (no slash needed).", annotations=annotate(read_only=False))
        def bot_send_chat(text: str) -> dict[str, str]:
            return {"sent": text, "echo": remote.send_chat(client, text)}

        @app.tool(description="Force an on-foot animation (id, flags).", annotations=annotate(read_only=False))
        def bot_animation(anim_id: int, flags: int = 0) -> dict[str, bool]:
            remote.animation(anim_id, flags)
            return {"ok": True}

        @app.tool(description="Set bot velocity vector (x, y, z).", annotations=annotate(read_only=False))
        def bot_set_velocity(x: float, y: float, z: float) -> dict[str, bool]:
            remote.set_velocity(x, y, z)
            return {"ok": True}

        @app.tool(description="Get bot money.", annotations=annotate(read_only=True))
        def bot_get_money() -> dict[str, int]:
            return {"money": remote.money()}

        @app.tool(description="Get bot nick.", annotations=annotate(read_only=True))
        def bot_get_nick() -> dict[str, str]:
            return {"nick": remote.nick()}

        @app.tool(description="Get bot interior id.", annotations=annotate(read_only=True))
        def bot_get_interior() -> dict[str, int]:
            return {"interior": remote.interior()}

        @app.tool(description="Get server address the bot is connected to.", annotations=annotate(read_only=True))
        def bot_get_server() -> dict[str, str]:
            return {"address": remote.server_addr()}

        @app.tool(description="Block until a chat line containing marker appears (max timeout s).", annotations=annotate(read_only=True))
        def bot_wait_for_chat(marker: str, timeout: float = 15.0) -> dict[str, list[str]]:
            return {"lines": remote.wait_for_chat(client, marker, timeout)}

    return app


# ponytail: source-derived allowlist; runtime command metadata comes later.
