--!strict
-- Remote control bridge: lets an MCP agent drive the bot through the shared file store.
require("addon") -- exposes sendInput/sendClickTextdraw/sendPickedUpPickup/sendTargetUpdate globals
--
-- Protocol (pipe-delimited, no JSON available in the script env):
--   queue key  "rcq": <id>|<kind>|<arg>|...
--   resp key   "rcr": <id>|ok|<result>|...   or   <id>|err|<message>
--
-- The MCP side (mcp_gta_samp/remote.py) writes one command per value, waits for the
-- matching <id> response, and deletes both keys. This script polls the queue every 10th
-- update tick, so commands need no client restart.
--
-- Kinds: walk_to|x|y|z|[mode]  walk_stop  teleport|x|y|z  face_heading|deg
--        face_point|x|y  jump  get_position  get_rotation  is_walking  alive
--        scan_players  scan_vehicles  key_hold|mask  key_release
--        enter_vehicle|id|seat  exit_vehicle  get_vehicle
--        animation|id|flags  set_velocity|x|y|z  get_money  get_nick
--        get_interior  get_server_addr  spawn  reconnect|ms  get_weapon
--        get_camera  get_keys  dialog|id|button|listItem|input
--        vehicle_drive|accel|brake|steer  vehicle_horn  vehicle_health
--        vehicle_position  vehicle_velocity|x|y|z  vehicle_speed
--        get_dialog  wait_dialog|timeout  wait_message|marker|timeout
--        click_textdraw|id  pickup_pickup|id  target_entity|object|vehicle|player|actor
--        scan_textlabels  scan_pickups  scan_objects
--        set_nick|nick  anim|name  list_anims  get_server_info  get_state
--        scan_players_detail  scan_vehicles_detail  fire|pulse  send_command|cmd
-- mode: walk|jog (default)|sprint, prefix "direct " for a straight-line seek.

local QUEUE_KEY = "rcq"
local RESP_KEY = "rcr"
local KEY_JUMP = 32 -- SA-MP on-foot keyset: 32 = jump (4 is fire, 8 sprint, 1024 walk)

-- Vehicle keyset (SA-MP incar keys): 1=fire, 4=accelerate, 8=brake, 16=left, 32=right, 64=horn.
local VKEY_FIRE, VKEY_ACCEL, VKEY_BRAKE = 1, 4, 8
local VKEY_LEFT, VKEY_RIGHT, VKEY_HORN = 16, 32, 64

-- Shared state polled by MCP via the command queue.
local vehicle_state = { health = 0, speed = 0.0, x = 0.0, y = 0.0, z = 0.0, keys = 0 }
local dialog_state = { active = false, id = 0, style = 0, title = "", button1 = "", button2 = "", text = "" }
local last_message = ""
local world_textlabels: { { id: number, color: number, x: number, y: number, z: number, text: string } } = {}
local world_pickups: { { id: number, model: number, pickupType: number, x: number, y: number, z: number } } = {}
local world_objects: { { id: number, model: number, x: number, y: number, z: number } } = {}
local players_detail: { { id: number, x: number, y: number, z: number, health: number, armor: number, weapon: number, vehicle: number, in_vehicle: boolean } } = {}
local vehicles_detail: { { id: number, health: number, speed: number, x: number, y: number, z: number, model: number } } = {}
local server_info = { worldtime = -1, weather = -1, gravity = 0.008 }
local spawned = false
local last_death_at = 0

-- Named animations (id, flags). id from GTA-SA anim index; flags 0x8004 = loop+walk-velocity.
local ANIMS = {
    sit = { 1189, 0x8004 }, dance = { 1185, 0x8004 }, wave = { 222, 0x8004 },
    cheer = { 1413, 0x8004 }, clap = { 1470, 0x8004 }, cry = { 1444, 0x8004 },
    laugh = { 1163, 0x8004 }, salute = { 1500, 0x8004 }, point = { 1500, 0x8004 },
    fall = { 1200, 0x8004 }, dodge = { 1135, 0x8004 }, punch = { 290, 0x8004 },
    kick = { 295, 0x8004 }, dead = { 1203, 0x8004 }, crouch = { 1231, 0x8004 },
}

local tick = 0

local function respond(id: string, parts: { string })
    local out = { id }
    for _, p in ipairs(parts) do
        table.insert(out, p)
    end
    sharedSet(RESP_KEY, table.concat(out, "|"))
end

local function execute(id: string, kind: string, args: { string })
    if kind == "walk_to" then
        walkTo(tonumber(args[1]), tonumber(args[2]), tonumber(args[3]), args[4])
        respond(id, { "ok" })
    elseif kind == "walk_stop" then
        walkStop()
        respond(id, { "ok" })
    elseif kind == "teleport" then
        setBotPosition(tonumber(args[1]), tonumber(args[2]), tonumber(args[3]))
        updateSync()
        respond(id, { "ok" })
    elseif kind == "face_heading" then
        -- SA-MP yaw: 0 = +Y, 90 = +X, clockwise.
        local rad = math.rad(tonumber(args[1]) or 0)
        setBotFacing(math.sin(rad), math.cos(rad))
        updateSync()
        respond(id, { "ok" })
    elseif kind == "face_point" then
        local px, py = getBotPosition()
        local dx, dy = tonumber(args[1]) - px, tonumber(args[2]) - py
        if dx ~= 0 or dy ~= 0 then
            setBotFacing(dx, dy)
            updateSync()
        end
        respond(id, { "ok" })
    elseif kind == "jump" then
        -- Pulse: hold -> sync -> release -> sync, so the server sees OnPlayerKeyStateChange.
        setBotKeys(KEY_JUMP)
        updateSync()
        setBotKeys(0)
        updateSync()
        respond(id, { "ok" })
    elseif kind == "get_position" then
        local x, y, z = getBotPosition()
        respond(id, { "ok", tostring(x), tostring(y), tostring(z) })
    elseif kind == "get_rotation" then
        respond(id, { "ok", tostring(getBotRotation()) })
    elseif kind == "is_walking" then
        respond(id, { "ok", isWalking() and "1" or "0" })
    elseif kind == "get_vehicle" then
        respond(id, { "ok", tostring(getBotVehicle()) })
    elseif kind == "alive" then
        respond(id, { "ok", "alive" })
    elseif kind == "scan_players" then
        local players = getStreamedPlayers()
        local out: { string } = {}
        for _, p in ipairs(players) do
            table.insert(out, tostring(p.id) .. "," .. tostring(p.x) .. "," .. tostring(p.y) .. "," .. tostring(p.z))
        end
        respond(id, { "ok", table.concat(out, ";") })
    elseif kind == "scan_vehicles" then
        local vehicles = getStreamedVehicles()
        local out: { string } = {}
        for _, v in ipairs(vehicles) do
            -- include model when known: id,x,y,z[,model]
            local row = tostring(v.id) .. "," .. tostring(v.x) .. "," .. tostring(v.y) .. "," .. tostring(v.z)
            if v.model ~= nil then
                row = row .. "," .. tostring(v.model)
            end
            table.insert(out, row)
        end
        respond(id, { "ok", table.concat(out, ";") })
    elseif kind == "key_hold" then
        -- Hold a key mask (e.g. 8=sprint, 4=fire, 128=crouch) until key_release.
        setBotKeys(tonumber(args[1]) or 0)
        updateSync()
        respond(id, { "ok" })
    elseif kind == "key_release" then
        setBotKeys(0)
        updateSync()
        respond(id, { "ok" })
    elseif kind == "enter_vehicle" then
        -- RPC 26 (EnterVehicle): vehicle id + passenger flag. We claim driver seat (0).
        local vid = tonumber(args[1]) or 0
        local bs = bitStream.new()
        bs:writeUInt16(vid)
        bs:writeUInt8(0) -- passenger? 0 = driver
        bs:sendRPC(26)
        setBotVehicle(vid, 0) -- mirror locally so getBotVehicle reports it
        updateSync()
        respond(id, { "ok" })
    elseif kind == "exit_vehicle" then
        -- RPC 154 (ExitVehicle): vehicle id.
        local vid = getBotVehicle()
        if vid ~= 0 then
            local bs = bitStream.new()
            bs:writeUInt16(vid)
            bs:sendRPC(154)
            setBotVehicle(0, 0)
            updateSync()
        end
        respond(id, { "ok" })
    elseif kind == "animation" then
        -- Force an on-foot animation (id, flags). e.g. 1189 = idle, 0x8004 flags.
        setBotAnimation(tonumber(args[1]) or 0, tonumber(args[2]) or 0)
        updateSync()
        respond(id, { "ok" })
    elseif kind == "set_velocity" then
        setBotVelocity(tonumber(args[1]), tonumber(args[2]), tonumber(args[3]))
        updateSync()
        respond(id, { "ok" })
    elseif kind == "get_money" then
        respond(id, { "ok", tostring(getBotMoney()) })
    elseif kind == "get_nick" then
        respond(id, { "ok", getBotNick() })
    elseif kind == "get_interior" then
        respond(id, { "ok", tostring(getBotInterior()) })
    elseif kind == "get_server_addr" then
        respond(id, { "ok", getServerAddress() })
    elseif kind == "spawn" then
        sampSpawnPlayer()
        updateSync()
        respond(id, { "ok" })
    elseif kind == "reconnect" then
        reconnect(tonumber(args[1]) or 500)
        respond(id, { "ok" })
    elseif kind == "get_weapon" then
        respond(id, { "ok", tostring(getBotWeapon()) })
    elseif kind == "get_camera" then
        local cx, cy, cz = getBotCameraPos()
        respond(id, { "ok", tostring(cx), tostring(cy), tostring(cz) })
    elseif kind == "get_keys" then
        respond(id, { "ok", tostring(getBotKeys()) })
    elseif kind == "dialog" then
        local did, btn, item, inp = tonumber(args[1]) or 0, tonumber(args[2]) or 0, tonumber(args[3]) or 0, args[4] or ""
        sampSendDialogResponse(did, btn, item, inp)
        dialog_state.active = false
        respond(id, { "ok" })
    elseif kind == "vehicle_drive" then
        -- accel(0/1) brake(0/1) steer(-1/0/1). Combines into the incar keyset.
        local accel, brake, steer = tonumber(args[1]) or 0, tonumber(args[2]) or 0, tonumber(args[3]) or 0
        local keys = 0
        if accel ~= 0 then keys += VKEY_ACCEL end
        if brake ~= 0 then keys += VKEY_BRAKE end
        if steer < 0 then keys += VKEY_LEFT elseif steer > 0 then keys += VKEY_RIGHT end
        setBotKeys(keys)
        updateSync()
        respond(id, { "ok" })
    elseif kind == "vehicle_horn" then
        setBotKeys(VKEY_HORN)
        updateSync()
        setBotKeys(0)
        updateSync()
        respond(id, { "ok" })
    elseif kind == "vehicle_health" then
        respond(id, { "ok", tostring(vehicle_state.health) })
    elseif kind == "vehicle_position" then
        respond(id, { "ok", tostring(vehicle_state.x), tostring(vehicle_state.y), tostring(vehicle_state.z) })
    elseif kind == "vehicle_velocity" then
        setBotVelocity(tonumber(args[1]), tonumber(args[2]), tonumber(args[3]))
        updateSync()
        respond(id, { "ok" })
    elseif kind == "vehicle_speed" then
        respond(id, { "ok", tostring(vehicle_state.speed) })
    elseif kind == "get_dialog" then
        if not dialog_state.active then
            respond(id, { "ok", "none" })
        else
            respond(id, { "ok", tostring(dialog_state.id), tostring(dialog_state.style), dialog_state.title, dialog_state.button1, dialog_state.button2, dialog_state.text })
        end
    elseif kind == "wait_dialog" then
        local timeout = tonumber(args[1]) or 5.0
        local deadline = (os.clock() * 1000) + timeout * 1000
        while (os.clock() * 1000) < deadline do
            if dialog_state.active then
                respond(id, { "ok", tostring(dialog_state.id), tostring(dialog_state.style), dialog_state.title, dialog_state.button1, dialog_state.button2, dialog_state.text })
                return
            end
            wait(50)
        end
        respond(id, { "err", "no dialog within " .. tostring(timeout) .. "s" })
    elseif kind == "wait_message" then
        local marker = args[1] or ""
        local timeout = tonumber(args[2]) or 5.0
        local deadline = (os.clock() * 1000) + timeout * 1000
        while (os.clock() * 1000) < deadline do
            if last_message ~= "" and (marker == "" or last_message:find(marker, 1, true) ~= nil) then
                local m = last_message
                last_message = ""
                respond(id, { "ok", m })
                return
            end
            wait(50)
        end
        respond(id, { "err", "no message within " .. tostring(timeout) .. "s" })
    elseif kind == "click_textdraw" then
        sendClickTextdraw(tonumber(args[1]) or 0)
        respond(id, { "ok" })
    elseif kind == "pickup_pickup" then
        sendPickedUpPickup(tonumber(args[1]) or 0)
        respond(id, { "ok" })
    elseif kind == "target_entity" then
        sendTargetUpdate(tonumber(args[1]) or 0, tonumber(args[2]) or 0, tonumber(args[3]) or 0, tonumber(args[4]) or 0)
        respond(id, { "ok" })
    elseif kind == "scan_textlabels" then
        local out: { string } = {}
        for _, t in ipairs(world_textlabels) do
            table.insert(out, tostring(t.id) .. "," .. tostring(t.color) .. "," .. tostring(t.x) .. "," .. tostring(t.y) .. "," .. tostring(t.z) .. "," .. tostring(t.text))
        end
        respond(id, { "ok", table.concat(out, ";") })
    elseif kind == "scan_pickups" then
        local out: { string } = {}
        for _, p in ipairs(world_pickups) do
            table.insert(out, tostring(p.id) .. "," .. tostring(p.model) .. "," .. tostring(p.pickupType) .. "," .. tostring(p.x) .. "," .. tostring(p.y) .. "," .. tostring(p.z))
        end
        respond(id, { "ok", table.concat(out, ";") })
    elseif kind == "scan_objects" then
        local out: { string } = {}
        for _, o in ipairs(world_objects) do
            table.insert(out, tostring(o.id) .. "," .. tostring(o.model) .. "," .. tostring(o.x) .. "," .. tostring(o.y) .. "," .. tostring(o.z))
        end
        respond(id, { "ok", table.concat(out, ";") })
    elseif kind == "set_nick" then
        setBotNick(args[1] or "")
        respond(id, { "ok" })
    elseif kind == "anim" then
        local anim = ANIMS[args[1]]
        if anim == nil then
            respond(id, { "err", "unknown anim: " .. (args[1] or "?") })
        else
            setBotAnimation(anim[1], anim[2])
            updateSync()
            respond(id, { "ok" })
        end
    elseif kind == "list_anims" then
        local names: { string } = {}
        for name, _ in pairs(ANIMS) do
            table.insert(names, name)
        end
        respond(id, { "ok", table.concat(names, ",") })
    elseif kind == "get_server_info" then
        respond(id, { "ok", tostring(server_info.worldtime), tostring(server_info.weather), tostring(server_info.gravity) })
    elseif kind == "get_state" then
        local x, y, z = getBotPosition()
        local veh = getBotVehicle()
        local hp = 0
        -- approximated: health comes from sync, but on-foot we don't have a global health tracker.
        -- We'll use the vehicle state if in vehicle, or last known from player sync.
        respond(id, { "ok", tostring(x), tostring(y), tostring(z), tostring(veh), tostring(server_info.worldtime), tostring(getBotInterior()) })
    elseif kind == "scan_players_detail" then
        local out: { string } = {}
        for _, p in ipairs(players_detail) do
            table.insert(out, tostring(p.id) .. "," .. tostring(p.x) .. "," .. tostring(p.y) .. "," .. tostring(p.z) .. "," .. tostring(p.health) .. "," .. tostring(p.armor) .. "," .. tostring(p.weapon) .. "," .. tostring(p.vehicle) .. "," .. (p.in_vehicle and "1" or "0"))
        end
        respond(id, { "ok", table.concat(out, ";") })
    elseif kind == "scan_vehicles_detail" then
        local out: { string } = {}
        for _, v in ipairs(vehicles_detail) do
            table.insert(out, tostring(v.id) .. "," .. tostring(v.health) .. "," .. tostring(v.speed) .. "," .. tostring(v.x) .. "," .. tostring(v.y) .. "," .. tostring(v.z) .. "," .. tostring(v.model))
        end
        respond(id, { "ok", table.concat(out, ";") })
    elseif kind == "fire" then
        -- Pulse fire key (4) to simulate a single shot.
        setBotKeys(4)
        updateSync()
        setBotKeys(0)
        updateSync()
        respond(id, { "ok" })
    elseif kind == "send_command" then
        sendInput("/" .. (args[1] or ""))
        respond(id, { "ok" })
    else
        respond(id, { "err", "unknown command: " .. kind })
    end
end

registerHandler("onUpdate", function()
    tick += 1
    if tick % 10 ~= 0 then
        return -- throttle file reads; 10 updates is a fraction of a second
    end
    local raw = sharedGet(QUEUE_KEY)
    if raw == nil or raw == "" then
        return
    end
    sharedDelete(QUEUE_KEY)
    local parts: { string } = {}
    for part in string.gmatch(raw, "[^|]+") do
        table.insert(parts, part)
    end
    local id = parts[1] or "?"
    local kind = parts[2]
    if kind == nil then
        respond(id, { "err", "malformed command" })
        return
    end
    local args: { string } = {}
    for i = 3, #parts do
        args[i - 2] = parts[i]
    end
    execute(id, kind, args)
end)

-- Incoming vehicle sync → track health/position/speed for MCP reads.
-- PACKET_VEHICLE_SYNC (200): playerId u16, vehicleId u16, leftRight u16, upDown u16, keys u16,
-- quaternion (4 bools + 3x u16), position 3x f32, moveSpeed 3x compressed f32, vehicleHealth u16, ...
registerHandler("onReceivePacket", function(id, bs)
    if id ~= 200 then -- PACKET_VEHICLE_SYNC
        return
    end
    bs:ignoreBits(8) -- packet id
    bs:readUInt16() -- playerId
    bs:readUInt16() -- vehicleId
    bs:readUInt16() -- leftRightKeys
    bs:readUInt16() -- upDownKeys
    local keys = bs:readUInt16()
    bs:readBool() bs:readBool() bs:readBool() bs:readBool() -- quat signs
    bs:readUInt16() bs:readUInt16() bs:readUInt16() -- quat xyz
    vehicle_state.x, vehicle_state.y, vehicle_state.z = bs:readFloat(), bs:readFloat(), bs:readFloat()
    local spdx = bs:readUInt16() / 32767.5 - 1
    local spdy = bs:readUInt16() / 32767.5 - 1
    local spdz = bs:readUInt16() / 32767.5 - 1
    vehicle_state.speed = math.sqrt(spdx * spdx + spdy * spdy + spdz * spdz)
    vehicle_state.health = bs:readUInt16()
    vehicle_state.keys = keys
end)

-- Incoming SHOWDIALOG (RPC 61) → record the dialog for MCP.
-- NOTE: onReceiveRPC payload excludes the RPC id byte (raknet wire.rs strips it) — no ignoreBits here.
-- Wire format: dialogId u16, style u8, title string8, button1 string8, button2 string8, text encodedString4096.
registerHandler("onReceiveRPC", function(id, bs)
    if id == 61 then -- RPC_SCRSHOWDIALOG
        dialog_state.id = bs:readUInt16()
        dialog_state.style = bs:readUInt8()
        dialog_state.title = bs:readString(bs:readUInt8())
        dialog_state.button1 = bs:readString(bs:readUInt8())
        dialog_state.button2 = bs:readString(bs:readUInt8())
        dialog_state.text = bs:readEncoded(4096)
        dialog_state.active = true
    end
end)

-- Incoming server message (RPC 93) → capture for wait_message. Payload excludes RPC id.
registerHandler("onReceiveRPC", function(id, bs)
    if id == 93 then -- RPC_SCRCLIENTMESSAGE
        bs:readInt32() -- color
        last_message = bs:readString(bs:readUInt8())
    end
end)

-- Incoming world entities → keep a live view for MCP scans.
-- RPC 36 CREATE3DTEXTLABEL: id u16, color i32, pos 3x f32, distance f32, testLOS bool8,
-- attachPlayer u16, attachVehicle u16, text encodedString4096.
registerHandler("onReceiveRPC", function(id, bs)
    if id == 36 then
        local e = {}
        e.id = bs:readUInt16()
        e.color = bs:readInt32()
        e.x, e.y, e.z = bs:readFloat(), bs:readFloat(), bs:readFloat()
        bs:readFloat() -- distance
        bs:readBool() -- testLOS
        bs:readUInt16() -- attachedPlayerId
        bs:readUInt16() -- attachedVehicleId
        e.text = bs:readEncoded(4096)
        local replaced = false
        for i, t in ipairs(world_textlabels) do
            if t.id == e.id then world_textlabels[i] = e replaced = true break end
        end
        if not replaced then table.insert(world_textlabels, e) end
    elseif id == 45 then -- DESTROY3DTEXTLABEL: labelId u16
        local lid = bs:readUInt16()
        for i, t in ipairs(world_textlabels) do
            if t.id == lid then table.remove(world_textlabels, i) break end
        end
    end
end)

-- RPC 44 CREATEOBJECT: objectId u16, modelId i32, pos 3x f32, rot 3x f32, drawDist f32, ...
registerHandler("onReceiveRPC", function(id, bs)
    if id == 44 then
        local oid = bs:readUInt16()
        local model = bs:readInt32()
        local x, y, z = bs:readFloat(), bs:readFloat(), bs:readFloat()
        local e = { id = oid, model = model, x = x, y = y, z = z }
        local replaced = false
        for i, o in ipairs(world_objects) do
            if o.id == oid then world_objects[i] = e replaced = true break end
        end
        if not replaced then table.insert(world_objects, e) end
    elseif id == 47 then -- DESTROYOBJECT: objectId u16
        local oid = bs:readUInt16()
        for i, o in ipairs(world_objects) do
            if o.id == oid then table.remove(world_objects, i) break end
        end
    end
end)

-- RPC 95 CREATEPICKUP: id i32, model i32, pickupType i32, pos 3x f32. Payload excludes RPC id.
registerHandler("onReceiveRPC", function(id, bs)
    if id == 95 then
        local pid = bs:readInt32()
        local model = bs:readInt32()
        local ptype = bs:readInt32()
        local x, y, z = bs:readFloat(), bs:readFloat(), bs:readFloat()
        local e = { id = pid, model = model, pickupType = ptype, x = x, y = y, z = z }
        local replaced = false
        for i, p in ipairs(world_pickups) do
            if p.id == pid then world_pickups[i] = e replaced = true break end
        end
        if not replaced then table.insert(world_pickups, e) end
    elseif id == 63 then -- DESTROYPICKUP: id i32
        local pid = bs:readInt32()
        for i, p in ipairs(world_pickups) do
            if p.id == pid then table.remove(world_pickups, i) break end
        end
    end
end)

-- Incoming player sync (207) → per-player health/armor/weapon/vehicle tracking.
-- playerId u16, lr u16, ud u16, keys u16, pos 3x f32, quat (4 bool + 3x u16), health/armor u8, weapon u8, ...
registerHandler("onReceivePacket", function(id, bs)
    if id ~= 207 then
        return
    end
    bs:ignoreBits(8)
    local pid = bs:readUInt16()
    bs:readUInt16() -- leftRight
    bs:readUInt16() -- upDown
    bs:readUInt16() -- keys
    local x, y, z = bs:readFloat(), bs:readFloat(), bs:readFloat()
    bs:readBool() bs:readBool() bs:readBool() bs:readBool() -- quat signs
    bs:readUInt16() bs:readUInt16() bs:readUInt16() -- quat xyz
    local packed = bs:readUInt8()
    local health = math.min(bit32.rshift(packed, 4) * 7, 100)
    local armor = math.min(bit32.band(packed, 0x0F) * 7, 100)
    local weapon = bs:readUInt8()
    bs:readUInt8() -- special action
    bs:readUInt16() bs:readUInt16() bs:readUInt16() -- move speed compressed
    bs:readUInt16() bs:readUInt16() bs:readUInt16() -- surfing offset
    local veh = bs:readUInt16()
    local replaced = false
    for i, p in ipairs(players_detail) do
        if p.id == pid then
            players_detail[i] = { id = pid, x = x, y = y, z = z, health = health, armor = armor, weapon = weapon, vehicle = veh, in_vehicle = veh ~= 0 }
            replaced = true
            break
        end
    end
    if not replaced then table.insert(players_detail, { id = pid, x = x, y = y, z = z, health = health, armor = armor, weapon = weapon, vehicle = veh, in_vehicle = veh ~= 0 }) end
end)

-- Incoming vehicle sync (200) → per-vehicle health/speed/position tracking.
-- playerId u16, vehicleId u16, lr u16, ud u16, keys u16, quat (4 bool + 3x u16), pos 3x f32,
-- moveSpeed 3x compressed, vehicleHealth u16, ...
registerHandler("onReceivePacket", function(id, bs)
    if id ~= 200 then
        return
    end
    bs:ignoreBits(8)
    bs:readUInt16() -- playerId
    local vid = bs:readUInt16()
    bs:readUInt16() -- leftRight
    bs:readUInt16() -- upDown
    bs:readUInt16() -- keys
    bs:readBool() bs:readBool() bs:readBool() bs:readBool() -- quat signs
    bs:readUInt16() bs:readUInt16() bs:readUInt16() -- quat xyz
    local x, y, z = bs:readFloat(), bs:readFloat(), bs:readFloat()
    local spdx = bs:readUInt16() / 32767.5 - 1
    local spdy = bs:readUInt16() / 32767.5 - 1
    local spdz = bs:readUInt16() / 32767.5 - 1
    local speed = math.sqrt(spdx * spdx + spdy * spdy + spdz * spdz)
    local health = bs:readUInt16()
    local replaced = false
    for i, v in ipairs(vehicles_detail) do
        if v.id == vid then
            vehicles_detail[i] = { id = vid, health = health, speed = speed, x = x, y = y, z = z, model = v.model }
            replaced = true
            break
        end
    end
    if not replaced then table.insert(vehicles_detail, { id = vid, health = health, speed = speed, x = x, y = y, z = z, model = 0 }) end
end)

-- Incoming INITGAME (139) → worldtime, weather, gravity. Payload excludes RPC id.
-- Booleans are 1-bit (readBool), matching samp.events rpc_init_game_reader.
registerHandler("onReceiveRPC", function(id, bs)
    if id == 139 then
        bs:readBool() -- zoneNames
        bs:readBool() -- useCJWalk
        bs:readBool() -- allowWeapons
        bs:readBool() -- limitGlobalChatRadius
        bs:readFloat() -- globalChatRadius
        bs:readBool() -- stuntBonus
        bs:readFloat() -- nametagDrawDist
        bs:readBool() -- disableEnterExits
        bs:readBool() -- nametagLOS
        bs:readBool() -- tirePopping
        bs:readInt32() -- classesAvailable
        bs:readUInt16() -- playerId
        bs:readBool() -- showPlayerTags
        bs:readInt32() -- playerMarkersMode
        server_info.worldtime = bs:readUInt8()
        server_info.weather = bs:readUInt8()
        server_info.gravity = bs:readFloat()
    end
end)

-- Spawn response (129) → spawned flag for wait_for_spawn / death tracking. Payload excludes RPC id.
registerHandler("onReceiveRPC", function(id, bs)
    if id == 129 then
        spawned = true
    end
end)

-- Player death (55) → last death timestamp. Payload excludes RPC id.
registerHandler("onReceiveRPC", function(id, bs)
    if id == 55 then
        last_death_at = os.clock() * 1000
    end
end)
