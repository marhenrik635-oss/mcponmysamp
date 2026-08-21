import sys
from pathlib import Path

import pytest

from mcp_gta_samp.headless import HeadlessClient
from mcp_gta_samp.mcp_server import create_mcp_server
from mcp_gta_samp.openmp import OpenMpConfig, OpenMpServer
from mcp_gta_samp.remote import RemoteControlError


class DummyRemote:
    """Stub for the RakClient Luau bridge; every method is a no-op/constant."""

    def __init__(self):
        self.position_ = (1.0, 2.0, 3.0)
        self.walk_calls = 0
        self.keys_held = 0

    def walk_to(self, x, y, z, mode="jog"):
        self.walk_calls += 1

    def walk_stop(self):
        self.walk_calls = 0

    def teleport(self, x, y, z):
        pass

    def face_heading(self, heading):
        pass

    def face_point(self, x, y):
        pass

    def jump(self):
        pass

    def position(self):
        return self.position_

    def rotation(self):
        return 90.0

    def is_walking(self):
        return self.walk_calls > 0

    def ping(self):
        return True

    def scan_players(self):
        return [{"id": 1, "x": 1.0, "y": 2.0, "z": 3.0}]

    def scan_vehicles(self):
        return [{"id": 1, "x": 1.0, "y": 2.0, "z": 3.0}]

    def health(self, client):
        return (75.0, 25.0)

    def key_hold(self, mask):
        self.keys_held = mask

    def key_release(self):
        self.keys_held = 0

    def enter_vehicle(self, vehicle_id, seat=0):
        pass

    def exit_vehicle(self):
        pass

    def vehicle_id(self):
        return 5

    def send_chat(self, client, text):
        return text

    def animation(self, anim_id, flags=0):
        pass

    def set_velocity(self, x, y, z):
        pass

    def money(self):
        return 5000

    def nick(self):
        return "MCPBot"

    def interior(self):
        return 0

    def server_addr(self):
        return "127.0.0.1:7777"

    def respawn(self):
        pass

    def reconnect(self, delay_ms=500):
        pass

    def weapon(self):
        return 24

    def camera_pos(self):
        return (100.0, 200.0, 300.0)

    def keys(self):
        return 8

    def dialog(self, dialog_id, button, list_item=0, input_text=""):
        pass

    def vehicle_drive(self, accel, brake=False, steer=0):
        pass

    def vehicle_horn(self):
        pass

    def vehicle_health(self):
        return 800.0

    def vehicle_position(self):
        return (1500.0, 2000.0, 25.0)

    def vehicle_velocity(self, x, y, z):
        pass

    def vehicle_speed(self):
        return 42.5

    def get_dialog(self):
        return {"id": 7, "style": 0, "title": "Selamat Datang", "button1": "OK", "button2": "", "text": "Halo"}

    def wait_dialog(self, timeout=5.0):
        return {"id": 7, "style": 0, "title": "Selamat Datang", "button1": "OK", "button2": "", "text": "Halo"}

    def wait_message(self, marker="", timeout=5.0):
        return "Selamat datang di server!"

    def click_textdraw(self, textdraw_id):
        pass

    def pickup_pickup(self, pickup_id):
        pass

    def target_entity(self, obj=0, veh=0, player=0, actor=0):
        pass

    def scan_textlabels(self):
        return [{"id": 1, "color": 0xFFFFFFFF, "x": 1.0, "y": 2.0, "z": 3.0, "text": "Info"}]

    def scan_pickups(self):
        return [{"id": 1, "model": 1240, "pickup_type": 2, "x": 1.0, "y": 2.0, "z": 3.0}]

    def scan_objects(self):
        return [{"id": 1, "model": 19341, "x": 1.0, "y": 2.0, "z": 3.0}]

    def set_nick(self, nick):
        pass

    def play_anim(self, name):
        pass

    def list_anims(self):
        return ["sit", "dance", "wave", "cheer", "clap", "cry", "laugh", "salute", "point", "fall", "dodge", "punch", "kick", "dead", "crouch"]

    def server_info(self):
        return {"worldtime": 12, "weather": 1, "gravity": 0.008}

    def state(self):
        return {"x": 1.0, "y": 2.0, "z": 3.0, "vehicle": 0, "worldtime": 12, "interior": 0}

    def scan_players_detail(self):
        return [{"id": 1, "x": 1.0, "y": 2.0, "z": 3.0, "health": 100.0, "armor": 0.0, "weapon": 0, "vehicle": 0, "in_vehicle": False}]

    def scan_vehicles_detail(self):
        return [{"id": 1, "health": 800.0, "speed": 20.0, "x": 1.0, "y": 2.0, "z": 3.0, "model": 411}]

    def fire(self):
        pass

    def send_command(self, cmd):
        pass

    def wait_for_chat(self, client, marker, timeout=15.0):
        return ["line1", "line2"]


class DeadRemote(DummyRemote):
    def ping(self):
        return False


@pytest.fixture
def app(tmp_path):
    server_exe = tmp_path / "server.exe"
    server_exe.write_text("placeholder", encoding="utf-8")
    client = HeadlessClient(sys.executable, ["-c", "import time; time.sleep(60)"])
    app = create_mcp_server(
        OpenMpServer(OpenMpConfig(executable=server_exe)),
        client=client,
        gamemode_source=Path(__file__).parent / ".." / "examples" / "mcp_test.pwn",
        remote=DummyRemote(),
    )
    yield app
    client.stop()


def _t(app, name):
    return app._tool_manager._tools[name].fn


def test_bot_movement_tools(app):
    assert _t(app, "bot_walk_to")(1.0, 2.0, 3.0, "sprint") == {"ok": True}
    assert _t(app, "bot_stop")() == {"ok": True}
    assert _t(app, "bot_teleport")(10.0, 20.0, 30.0) == {"ok": True}
    assert _t(app, "bot_face_heading")(180.0) == {"ok": True}
    assert _t(app, "bot_face_point")(0.0, 0.0) == {"ok": True}
    assert _t(app, "bot_jump")() == {"ok": True}


def test_bot_sensing_tools(app):
    assert _t(app, "bot_get_position")() == {"x": 1.0, "y": 2.0, "z": 3.0}
    assert _t(app, "bot_get_rotation")() == {"heading": 90.0}
    assert _t(app, "bot_is_walking")() == {"walking": False}
    assert _t(app, "bot_ping")() == {"status": "alive"}
    assert _t(app, "bot_scan_players")() == {"players": [{"id": 1, "x": 1.0, "y": 2.0, "z": 3.0}]}
    assert _t(app, "bot_scan_vehicles")() == {"vehicles": [{"id": 1, "x": 1.0, "y": 2.0, "z": 3.0}]}
    assert _t(app, "bot_get_health")() == {"health": 75.0, "armour": 25.0}
    assert _t(app, "bot_get_vehicle")() == {"vehicle": 5}
    assert _t(app, "bot_get_money")() == {"money": 5000}
    assert _t(app, "bot_get_nick")() == {"nick": "MCPBot"}
    assert _t(app, "bot_get_interior")() == {"interior": 0}
    assert _t(app, "bot_get_server")() == {"address": "127.0.0.1:7777"}


def test_bot_action_tools(app):
    assert _t(app, "bot_key_hold")(8) == {"ok": True}
    assert _t(app, "bot_key_release")() == {"ok": True}
    assert _t(app, "bot_enter_vehicle")(3, 0) == {"ok": True}
    assert _t(app, "bot_exit_vehicle")() == {"ok": True}
    assert _t(app, "bot_send_chat")("halo") == {"sent": "halo", "echo": "halo"}
    assert _t(app, "bot_animation")(0, 0) == {"ok": True}
    assert _t(app, "bot_set_velocity")(0.0, 0.0, 10.0) == {"ok": True}


def test_bot_wait_for_chat(app):
    assert _t(app, "bot_wait_for_chat")("marker", 5.0) == {"lines": ["line1", "line2"]}


def test_bot_utility_tools(app):
    assert _t(app, "bot_respawn")() == {"ok": True}
    assert _t(app, "bot_reconnect")(1000) == {"ok": True}
    assert _t(app, "bot_get_weapon")() == {"weapon": 24}
    assert _t(app, "bot_get_camera")() == {"x": 100.0, "y": 200.0, "z": 300.0}
    assert _t(app, "bot_get_keys")() == {"keys": 8}
    assert _t(app, "bot_dialog")(1, 1, 0, "") == {"ok": True}


def test_bot_vehicle_tools(app):
    assert _t(app, "bot_vehicle_drive")(True, False, 1) == {"ok": True}
    assert _t(app, "bot_vehicle_horn")() == {"ok": True}
    assert _t(app, "bot_vehicle_health")() == {"health": 800.0}
    assert _t(app, "bot_vehicle_position")() == {"x": 1500.0, "y": 2000.0, "z": 25.0}
    assert _t(app, "bot_vehicle_velocity")(0.0, 0.0, 10.0) == {"ok": True}
    assert _t(app, "bot_vehicle_speed")() == {"speed": 42.5}


def test_bot_dialog_awareness_tools(app):
    dlg = {"id": 7, "style": 0, "title": "Selamat Datang", "button1": "OK", "button2": "", "text": "Halo"}
    assert _t(app, "bot_get_dialog")() == {"dialog": dlg}
    assert _t(app, "bot_wait_for_dialog")(3.0) == {"dialog": dlg}
    assert _t(app, "bot_wait_for_message")("Selamat", 3.0) == {"message": "Selamat datang di server!"}


def test_bot_world_interaction_tools(app):
    assert _t(app, "bot_click_textdraw")(1) == {"ok": True}
    assert _t(app, "bot_pickup_pickup")(1) == {"ok": True}
    assert _t(app, "bot_target_entity")(0, 2, 0, 0) == {"ok": True}


def test_bot_world_scan_tools(app):
    labels = [{"id": 1, "color": 0xFFFFFFFF, "x": 1.0, "y": 2.0, "z": 3.0, "text": "Info"}]
    pickups = [{"id": 1, "model": 1240, "pickup_type": 2, "x": 1.0, "y": 2.0, "z": 3.0}]
    objects = [{"id": 1, "model": 19341, "x": 1.0, "y": 2.0, "z": 3.0}]
    assert _t(app, "bot_scan_textlabels")() == {"labels": labels}
    assert _t(app, "bot_scan_pickups")() == {"pickups": pickups}
    assert _t(app, "bot_scan_objects")() == {"objects": objects}


def test_bot_social_tools(app):
    assert _t(app, "bot_set_nick")("NewName") == {"ok": True}
    assert _t(app, "bot_play_animation")("dance") == {"ok": True}
    assert _t(app, "bot_list_animations")()["anims"][0] == "sit"


def test_bot_server_info_tools(app):
    assert _t(app, "bot_get_server_info")() == {"worldtime": 12, "weather": 1, "gravity": 0.008}
    assert _t(app, "bot_get_state")() == {"x": 1.0, "y": 2.0, "z": 3.0, "vehicle": 0, "worldtime": 12, "interior": 0}


def test_bot_detail_scan_tools(app):
    players = [{"id": 1, "x": 1.0, "y": 2.0, "z": 3.0, "health": 100.0, "armor": 0.0, "weapon": 0, "vehicle": 0, "in_vehicle": False}]
    vehicles = [{"id": 1, "health": 800.0, "speed": 20.0, "x": 1.0, "y": 2.0, "z": 3.0, "model": 411}]
    assert _t(app, "bot_scan_players_detail")() == {"players": players}
    assert _t(app, "bot_scan_vehicles_detail")() == {"vehicles": vehicles}


def test_bot_combat_tools(app):
    assert _t(app, "bot_fire")() == {"ok": True}
    assert _t(app, "bot_send_command")("/help") == {"ok": True}


def test_bot_ping_raises_when_bridge_down(tmp_path):
    server_exe = tmp_path / "server.exe"
    server_exe.write_text("placeholder", encoding="utf-8")
    app = create_mcp_server(
        OpenMpServer(OpenMpConfig(executable=server_exe)),
        remote=DeadRemote(),
    )
    with pytest.raises(RemoteControlError):
        _t(app, "bot_ping")()
