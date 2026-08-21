#include <open.mp>

main()
{
    print("MCP test gamemode loaded.");
}

public OnGameModeInit()
{
    SetGameModeText("MCP Test");
    AddPlayerClass(0, 1958.3783, 1343.1572, 15.3746, 270.0, WEAPON_FIST, 0, WEAPON_FIST, 0, WEAPON_FIST, 0);
    CreateVehicle(400, 1968.3783, 1343.1572, 15.8746, 0.0, 0, 0, -1); // Landstalker dekat spawn
    return 1;
}

public OnPlayerConnect(playerid)
{
    SendClientMessage(playerid, 0x00FFFFFF, "Welcome to the MCP test server.");
    SendClientMessage(playerid, 0xFFFFFFFF, "Type /help to test the AI game bridge.");
    SetSpawnInfo(playerid, 0, 0, 1958.3783, 1343.1572, 15.3746, 270.0, WEAPON_FIST, 0, WEAPON_FIST, 0, WEAPON_FIST, 0);
    return 1;
}

handle_mcp_command(playerid, cmdtext[])
{
    printf("MCP_CMD_CALLBACK:%s", cmdtext);
    if (!strcmp(cmdtext, "/help", true))
    {
        SendClientMessage(playerid, 0x00FFFFFF, "MCP Test Commands:");
        SendClientMessage(playerid, 0xFFFFFFFF, "/help - show this command list");
        SendClientMessage(playerid, 0xFFFFFFFF, "/status - show a test response");
        return 1;
    }
    if (!strcmp(cmdtext, "/status", true))
    {
        SendClientMessage(playerid, 0x00FFFFFF, "MCP_STATUS_OK");
        return 1;
    }
    // /health [token] -> MCP_HEALTH:<token>:<hp>:<armor>
    if (!strcmp(cmdtext, "/health", true, 7))
    {
        new token[16] = "0";
        if (cmdtext[7] != '\0')
        {
            // skip leading space/separator
            new start = 7;
            while (cmdtext[start] == ' ' || cmdtext[start] == '\t' || cmdtext[start] == ':')
                start++;
            if (cmdtext[start] != '\0')
                strmid(token, cmdtext, start, strlen(cmdtext), sizeof(token));
        }
        new Float:hp, Float:arm;
        GetPlayerHealth(playerid, hp);
        GetPlayerArmour(playerid, arm);
        new msg[80];
        format(msg, sizeof(msg), "MCP_HEALTH:%s:%.0f:%.0f", token, hp, arm);
        SendClientMessage(playerid, 0x00FFFFFF, msg);
        return 1;
    }
    return 0;
}

public OnPlayerCommandText(playerid, cmdtext[])
{
    return handle_mcp_command(playerid, cmdtext);
}

public OnPlayerRequestClass(playerid, classid)
{
    SetPlayerPos(playerid, 1958.3783, 1343.1572, 15.3746);
    SetPlayerCameraPos(playerid, 1955.3783, 1340.1572, 17.3746);
    SetPlayerCameraLookAt(playerid, 1958.3783, 1343.1572, 15.3746);
    return 1;
}

public OnPlayerSpawn(playerid)
{
    SetCameraBehindPlayer(playerid);
    return 1;
}

public OnPlayerUpdate(playerid)
{
    new Float:x, Float:y, Float:z;
    GetPlayerPos(playerid, x, y, z);
    printf("MCP_BOT_POS: %d -> %.2f, %.2f, %.2f", playerid, x, y, z);
    return 1;
}

public OnPlayerEnterVehicle(playerid, vehicleid, ispassenger)
{
    printf("MCP_VEH_ENTER: %d -> vehicle %d passenger %d", playerid, vehicleid, ispassenger);
    return 1;
}

public OnPlayerExitVehicle(playerid, vehicleid)
{
    printf("MCP_VEH_EXIT: %d -> vehicle %d", playerid, vehicleid);
    return 1;
}

public OnPlayerKeyStateChange(playerid, KEY:newkeys, KEY:oldkeys)
{
    printf("MCP_KEYS: %d -> new %d old %d", playerid, _:newkeys, _:oldkeys);
    return 1;
}

public OnPlayerText(playerid, text[])
{
    if (text[0] == '/')
    {
        return handle_mcp_command(playerid, text);
    }
    return 1;
}

public OnGameModeExit()
{
    return 1;
}

// ponytail: minimal fixture; add scenarios only with a matching live MCP test.
main_test_contract()
{
    return 1;
}
