
from backend.integrations.discord.permissions import (
    DiscordPermissions,
    BASE_BOT_PERMISSIONS,
    calculate_permissions_integer,
    calculate_required_intents,
    generate_invite_url,
    check_missing_permissions,
    check_role_hierarchy,
)

def test_base_permissions_calculation():
    perms = calculate_permissions_integer([])
    assert (perms & DiscordPermissions.SEND_MESSAGES) == DiscordPermissions.SEND_MESSAGES
    assert (perms & DiscordPermissions.EMBED_LINKS) == DiscordPermissions.EMBED_LINKS
    assert (perms & DiscordPermissions.USE_APPLICATION_COMMANDS) == DiscordPermissions.USE_APPLICATION_COMMANDS

def test_moderation_module_permissions():
    perms = calculate_permissions_integer(["moderation"])
    assert (perms & DiscordPermissions.BAN_MEMBERS) == DiscordPermissions.BAN_MEMBERS
    assert (perms & DiscordPermissions.KICK_MEMBERS) == DiscordPermissions.KICK_MEMBERS
    assert (perms & DiscordPermissions.MODERATE_MEMBERS) == DiscordPermissions.MODERATE_MEMBERS

def test_required_intents():
    intents = calculate_required_intents(["welcomes", "moderation", "antispam"])
    assert "GUILD_MEMBERS" in intents
    assert "MESSAGE_CONTENT" in intents
    assert "GUILD_MESSAGES" in intents

def test_generate_invite_url():
    url = generate_invite_url(client_id="1234567890", permissions_integer=268453888, guild_id="99887766")
    assert "client_id=1234567890" in url
    assert "permissions=268453888" in url
    assert "guild_id=99887766" in url
    assert "scope=bot+applications.commands" in url or "scope=bot%20applications.commands" in url

def test_missing_permissions():
    bot_has = DiscordPermissions.SEND_MESSAGES
    required = DiscordPermissions.SEND_MESSAGES | DiscordPermissions.BAN_MEMBERS
    missing = check_missing_permissions(bot_has, required)
    assert len(missing) == 1
    assert missing[0]["flag"] == DiscordPermissions.BAN_MEMBERS

def test_role_hierarchy():
    res_ok = check_role_hierarchy(bot_highest_role_pos=10, target_role_pos=5)
    assert res_ok["can_manage"] is True
    assert res_ok["warning"] is None

    res_fail = check_role_hierarchy(bot_highest_role_pos=5, target_role_pos=10)
    assert res_fail["can_manage"] is False
    assert "выше" in res_fail["warning"]
