#include <open.mp>

main()
{
    print("MCP test gamemode loaded.");
}

public OnGameModeInit()
{
    SetGameModeText("MCP Test");
    AddPlayerClass(0, 1958.3783, 1343.1572, 15.3746, 270.0, WEAPON_FIST, 0, WEAPON_FIST, 0, WEAPON_FIST, 0);
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
