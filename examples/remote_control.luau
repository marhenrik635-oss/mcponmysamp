--!strict
-- Remote control bridge: lets an MCP agent drive the bot through the shared file store.
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
--        get_interior  get_server_addr
-- mode: walk|jog (default)|sprint, prefix "direct " for a straight-line seek.

local QUEUE_KEY = "rcq"
local RESP_KEY = "rcr"
local KEY_JUMP = 32 -- SA-MP on-foot keyset: 32 = jump (4 is fire, 8 sprint, 1024 walk)

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
