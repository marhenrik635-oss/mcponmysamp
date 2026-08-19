local sampev = require("samp.events")

registerHandler("onSpawn", function()
    sampSendChat("/help")
end)

function sampev.onServerMessage(color: number, text: string)
    print("[MCP_SERVER]", text)
end

function sampev.onChatMessage(playerId: number, text: string)
    print("[MCP_CHAT]", playerId, text)
end
