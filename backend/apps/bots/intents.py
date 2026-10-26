"""Canonical Discord intents used by the API, UI and Runtime."""

from __future__ import annotations

from rest_framework import serializers

GUILDS = "guilds"
GUILD_MEMBERS = "guild_members"
GUILD_MESSAGES = "guild_messages"
MESSAGE_CONTENT = "message_content"
GUILD_MESSAGE_REACTIONS = "guild_message_reactions"
DIRECT_MESSAGES = "direct_messages"
DIRECT_MESSAGE_REACTIONS = "direct_message_reactions"

CANONICAL_INTENTS = (
    GUILDS,
    GUILD_MEMBERS,
    GUILD_MESSAGES,
    MESSAGE_CONTENT,
    GUILD_MESSAGE_REACTIONS,
    DIRECT_MESSAGES,
    DIRECT_MESSAGE_REACTIONS,
)

PRIVILEGED_INTENTS = {GUILD_MEMBERS, MESSAGE_CONTENT}

DEFAULT_INTENTS = (GUILDS, GUILD_MESSAGES, MESSAGE_CONTENT)

_LABELS = {
    "guilds": GUILDS,
    "guild members": GUILD_MEMBERS,
    "guild_members": GUILD_MEMBERS,
    "members": GUILD_MEMBERS,
    "member_events": GUILD_MEMBERS,
    "guild messages": GUILD_MESSAGES,
    "guild_messages": GUILD_MESSAGES,
    "message content": MESSAGE_CONTENT,
    "message_content": MESSAGE_CONTENT,
    "messages": MESSAGE_CONTENT,
    "guild message reactions": GUILD_MESSAGE_REACTIONS,
    "guild_message_reactions": GUILD_MESSAGE_REACTIONS,
    "direct messages": DIRECT_MESSAGES,
    "direct_messages": DIRECT_MESSAGES,
    "dm_messages": DIRECT_MESSAGES,
    "direct message reactions": DIRECT_MESSAGE_REACTIONS,
    "direct_message_reactions": DIRECT_MESSAGE_REACTIONS,
    "dm_reactions": DIRECT_MESSAGE_REACTIONS,
}


def normalize_intent(value: object) -> str:
    key = str(value).strip().lower()
    try:
        return _LABELS[key]
    except KeyError as exc:
        raise serializers.ValidationError(
            f"Unknown intent {value!r}. Allowed: {', '.join(CANONICAL_INTENTS)}"
        ) from exc


def normalize_intents(values: object) -> list[str]:
    if values is None:
        return list(DEFAULT_INTENTS)
    if not isinstance(values, (list, tuple, set)):
        raise serializers.ValidationError("intents must be a list")
    normalized: list[str] = []
    for item in values:
        intent = normalize_intent(item)
        if intent not in normalized:
            normalized.append(intent)
    return normalized


def merge_with_defaults(values: list[str]) -> list[str]:
    merged = list(values)
    for intent in DEFAULT_INTENTS:
        if intent not in merged:
            merged.append(intent)
    return merged
