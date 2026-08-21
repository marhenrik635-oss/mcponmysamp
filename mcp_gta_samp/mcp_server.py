from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .command_discovery import discover_commands
from .headless import HeadlessClient
from .openmp import OpenMpServer
from .remote import RemoteControl, RemoteControlError

# ponytail: hints declared literally (not via a helper) so static AST scanners
# (M8ven/Glama) can see every tool's annotations without executing the code.


def create_mcp_server(
    server: OpenMpServer,
    client: HeadlessClient | None = None,
    gamemode_source: Path | str | None = None,
    remote: RemoteControl | None = None,
) -> FastMCP:
    app = FastMCP("mcp-gta-samp", instructions="Control only a local or owned open.mp test server.")
    commands = discover_commands(gamemode_source) if gamemode_source else []

    @app.tool(
        description="Start the configured local open.mp test server and wait for readiness.",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    )
    def server_start() -> dict[str, bool]:
        return server.start()

    @app.tool(
        description="Stop the configured local open.mp test server.",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False),
    )
    def server_stop() -> dict[str, bool]:
        return server.stop()

    @app.tool(
        description="Return local open.mp test server process status.",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
    )
    def server_status() -> dict[str, int | bool | None]:
        return server.status()

    if gamemode_source:
        @app.tool(
            description="List slash commands discovered in the configured Pawn gamemode.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def server_list_commands() -> dict[str, list[str]]:
            return {"commands": commands}

        @app.tool(
            description="Check whether a slash command is discovered and allowlisted.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def server_assert_command(command: str) -> dict[str, bool | str]:
            command = command.strip()
            if command not in commands:
                raise ValueError(f"command not discovered: {command}")
            return {"command": command, "allowed": True}

    if client is not None:
        @app.tool(
            description="Start the configured headless game client.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
        )
        def client_start() -> dict[str, bool]:
            client.start()
            return {"running": client.running}

        @app.tool(
            description="Stop the configured headless game client.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False),
        )
        def client_stop() -> dict[str, bool]:
            client.stop()
            return {"running": client.running}

        @app.tool(
            description="Return headless game client status.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def client_status() -> dict[str, bool]:
            return {"running": client.running}

        @app.tool(
            description="Send an allowlisted slash command to the headless game client.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def client_send_chat(command: str) -> dict[str, str]:
            command = command.strip()
            if commands and command not in commands:
                raise ValueError(f"command not discovered: {command}")
            return {"command": command, "output": client.send_chat_after_spawn(command)}

        @app.tool(
            description="Return buffered headless client output lines.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def client_get_history() -> dict[str, list[str]]:
            return {"lines": client.history()}

        @app.tool(
            description="Assert buffered headless output contains text.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def client_assert_output(text: str) -> dict[str, bool | str]:
            if not client.history_contains(text):
                raise AssertionError(f"Missing text: {text}")
            return {"found": True, "text": text}

    if remote is not None:
        @app.tool(
            description="Walk to a world position over the navmesh (walk/jog/sprint/direct).",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_walk_to(x: float, y: float, z: float, mode: str = "jog") -> dict[str, bool]:
            remote.walk_to(x, y, z, mode)
            return {"ok": True}

        @app.tool(
            description="Stop the current navmesh walk.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
        )
        def bot_stop() -> dict[str, bool]:
            remote.walk_stop()
            return {"ok": True}

        @app.tool(
            description="Teleport to a world position (client-side, no anti-cheat bypass).",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_teleport(x: float, y: float, z: float) -> dict[str, bool]:
            remote.teleport(x, y, z)
            return {"ok": True}

        @app.tool(
            description="Face a heading in degrees (0 = north/+Y, 90 = east/+X, clockwise).",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
        )
        def bot_face_heading(heading: float) -> dict[str, bool]:
            remote.face_heading(heading)
            return {"ok": True}

        @app.tool(
            description="Face a world point.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
        )
        def bot_face_point(x: float, y: float) -> dict[str, bool]:
            remote.face_point(x, y)
            return {"ok": True}

        @app.tool(
            description="Pulse a jump key (hold->sync->release->sync).",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_jump() -> dict[str, bool]:
            remote.jump()
            return {"ok": True}

        @app.tool(
            description="Get current bot world position.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_get_position() -> dict[str, float]:
            x, y, z = remote.position()
            return {"x": x, "y": y, "z": z}

        @app.tool(
            description="Get current bot heading in degrees.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_get_rotation() -> dict[str, float]:
            return {"heading": remote.rotation()}

        @app.tool(
            description="Check whether the bot is currently walking.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_is_walking() -> dict[str, bool]:
            return {"walking": remote.is_walking()}

        @app.tool(
            description="Liveness probe for the remote control script bridge.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_ping() -> dict[str, str]:
            if remote.ping():
                return {"status": "alive"}
            raise RemoteControlError("remote control bridge is not responding")

        @app.tool(
            description="List streamed-in players around the bot (id, x, y, z).",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_scan_players() -> dict[str, list[dict[str, float]]]:
            return {"players": remote.scan_players()}

        @app.tool(
            description="List streamed-in vehicles around the bot (id, x, y, z).",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_scan_vehicles() -> dict[str, list[dict[str, float]]]:
            return {"vehicles": remote.scan_vehicles()}

        @app.tool(
            description="Get bot health and armour via server round-trip.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_get_health() -> dict[str, float]:
            hp, armor = remote.health(client)
            return {"health": hp, "armour": armor}

        @app.tool(
            description="Hold a movement/action key (8=sprint, 4=fire, 128=crouch, 32=jump) until bot_key_release.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_key_hold(mask: int) -> dict[str, bool]:
            remote.key_hold(mask)
            return {"ok": True}

        @app.tool(
            description="Release all held keys.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
        )
        def bot_key_release() -> dict[str, bool]:
            remote.key_release()
            return {"ok": True}

        @app.tool(
            description="Enter a vehicle by id (seat 0=driver, 1=passenger). Sends EnterVehicle RPC.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_enter_vehicle(vehicle_id: int, seat: int = 0) -> dict[str, bool]:
            remote.enter_vehicle(vehicle_id, seat)
            return {"ok": True}

        @app.tool(
            description="Exit the current vehicle. Sends ExitVehicle RPC.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_exit_vehicle() -> dict[str, bool]:
            remote.exit_vehicle()
            return {"ok": True}

        @app.tool(
            description="Get current vehicle id (0 = on foot).",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_get_vehicle() -> dict[str, int]:
            return {"vehicle": remote.vehicle_id()}

        @app.tool(
            description="Send a plain chat line (no slash needed).",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_send_chat(text: str) -> dict[str, str]:
            return {"sent": text, "echo": remote.send_chat(client, text)}

        @app.tool(
            description="Force an on-foot animation (id, flags).",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_animation(anim_id: int, flags: int = 0) -> dict[str, bool]:
            remote.animation(anim_id, flags)
            return {"ok": True}

        @app.tool(
            description="Set bot velocity vector (x, y, z).",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_set_velocity(x: float, y: float, z: float) -> dict[str, bool]:
            remote.set_velocity(x, y, z)
            return {"ok": True}

        @app.tool(
            description="Get bot money.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_get_money() -> dict[str, int]:
            return {"money": remote.money()}

        @app.tool(
            description="Get bot nick.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_get_nick() -> dict[str, str]:
            return {"nick": remote.nick()}

        @app.tool(
            description="Get bot interior id.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_get_interior() -> dict[str, int]:
            return {"interior": remote.interior()}

        @app.tool(
            description="Get server address the bot is connected to.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_get_server() -> dict[str, str]:
            return {"address": remote.server_addr()}

        @app.tool(
            description="Block until a chat line containing marker appears (max timeout s).",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_wait_for_chat(marker: str, timeout: float = 15.0) -> dict[str, list[str]]:
            return {"lines": remote.wait_for_chat(client, marker, timeout)}

        @app.tool(
            description="Force respawn of the bot (sampSpawnPlayer).",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
        )
        def bot_respawn() -> dict[str, bool]:
            remote.respawn()
            return {"ok": True}

        @app.tool(
            description="Disconnect and reconnect to the server after delay_ms (default 500).",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False),
        )
        def bot_reconnect(delay_ms: int = 500) -> dict[str, bool]:
            remote.reconnect(delay_ms)
            return {"ok": True}

        @app.tool(
            description="Get current weapon id (0 = fists).",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_get_weapon() -> dict[str, int]:
            return {"weapon": remote.weapon()}

        @app.tool(
            description="Get camera world position (differs from body in freecam).",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_get_camera() -> dict[str, float]:
            x, y, z = remote.camera_pos()
            return {"x": x, "y": y, "z": z}

        @app.tool(
            description="Get currently held key mask (8=sprint, 4=fire, 32=jump, 128=crouch).",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_get_keys() -> dict[str, int]:
            return {"keys": remote.keys()}

        @app.tool(
            description="Respond to a server dialog (button 1=left, 0=right; listItem for list dialogs; input_text for input dialogs).",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
        )
        def bot_dialog(dialog_id: int, button: int, list_item: int = 0, input_text: str = "") -> dict[str, bool]:
            remote.dialog(dialog_id, button, list_item, input_text)
            return {"ok": True}

        @app.tool(
            description="Hold vehicle keys: accel (bool), brake (bool), steer (-1=left, 0=straight, 1=right). Release with bot_key_release.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_vehicle_drive(accel: bool, brake: bool = False, steer: int = 0) -> dict[str, bool]:
            remote.vehicle_drive(accel, brake, steer)
            return {"ok": True}

        @app.tool(
            description="Pulse the vehicle horn.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
        )
        def bot_vehicle_horn() -> dict[str, bool]:
            remote.vehicle_horn()
            return {"ok": True}

        @app.tool(
            description="Get current vehicle health (1000 = perfect, 0 = destroyed).",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_vehicle_health() -> dict[str, float]:
            return {"health": remote.vehicle_health()}

        @app.tool(
            description="Get current vehicle world position.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_vehicle_position() -> dict[str, float]:
            x, y, z = remote.vehicle_position()
            return {"x": x, "y": y, "z": z}

        @app.tool(
            description="Set vehicle velocity vector (x, y, z).",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_vehicle_velocity(x: float, y: float, z: float) -> dict[str, bool]:
            remote.vehicle_velocity(x, y, z)
            return {"ok": True}

        @app.tool(
            description="Get current vehicle speed (units/s, magnitude of move speed).",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_vehicle_speed() -> dict[str, float]:
            return {"speed": remote.vehicle_speed()}

        @app.tool(
            description="Read the currently active server dialog (id, style, title, buttons, text), or none.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_get_dialog() -> dict[str, object]:
            dlg = remote.get_dialog()
            return {"dialog": dlg}

        @app.tool(
            description="Block until a server dialog appears; return its content. Raises on timeout.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_wait_for_dialog(timeout: float = 5.0) -> dict[str, object]:
            return {"dialog": remote.wait_dialog(timeout)}

        @app.tool(
            description="Block until a server message arrives (optionally containing marker). Returns the message.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_wait_for_message(marker: str = "", timeout: float = 5.0) -> dict[str, str]:
            return {"message": remote.wait_message(marker, timeout)}

        @app.tool(
            description="Click a textdraw by id (RPC 83).",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_click_textdraw(textdraw_id: int) -> dict[str, bool]:
            remote.click_textdraw(textdraw_id)
            return {"ok": True}

        @app.tool(
            description="Pick up a pickup by id (RPC 131).",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_pickup_pickup(pickup_id: int) -> dict[str, bool]:
            remote.pickup_pickup(pickup_id)
            return {"ok": True}

        @app.tool(
            description="Set aim target entity ids: object, vehicle, player, actor (RPC 168). Zero = none.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
        )
        def bot_target_entity(object_id: int = 0, vehicle_id: int = 0, player_id: int = 0, actor_id: int = 0) -> dict[str, bool]:
            remote.target_entity(object_id, vehicle_id, player_id, actor_id)
            return {"ok": True}

        @app.tool(
            description="List 3D text labels streamed around the bot (id, color, position, text).",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_scan_textlabels() -> dict[str, list[dict]]:
            return {"labels": remote.scan_textlabels()}

        @app.tool(
            description="List pickups streamed around the bot (id, model, type, position).",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_scan_pickups() -> dict[str, list[dict]]:
            return {"pickups": remote.scan_pickups()}

        @app.tool(
            description="List objects streamed around the bot (id, model, position).",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        def bot_scan_objects() -> dict[str, list[dict]]:
            return {"objects": remote.scan_objects()}

    return app


# ponytail: source-derived allowlist; runtime command metadata comes later.
