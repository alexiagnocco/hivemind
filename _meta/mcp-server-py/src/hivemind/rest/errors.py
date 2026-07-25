from __future__ import annotations


class ObsidianRestError(Exception):
    """Base for all REST client errors."""


class AuthenticationError(ObsidianRestError):
    """401 from plugin — API key is wrong or expired."""


class PluginUnavailableError(ObsidianRestError):
    """Connection refused or timeout — Obsidian not running."""


class PluginVersionError(ObsidianRestError):
    """Plugin version below OBSIDIAN_REST_API_VERSION_MIN."""
