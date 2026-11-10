"""URLs for images hosted by Discord."""

import re


def guild_icon_url(guild_id: str, icon_hash: object) -> str | None:
    if not isinstance(icon_hash, str) or not re.fullmatch(r"(?:a_)?[0-9a-f]{32}", icon_hash):
        return None
    if not re.fullmatch(r"[0-9]{1,20}", guild_id):
        return None
    return f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.webp?size=128"
