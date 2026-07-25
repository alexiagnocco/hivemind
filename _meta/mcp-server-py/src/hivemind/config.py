from __future__ import annotations

import logging
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class FallbackMode(StrEnum):
    AUTO = "auto"
    REST_ONLY = "rest_only"
    FS_ONLY = "fs_only"


def _detect_hive_root() -> Path:
    """Default vault root when the HIVE_PATH env var is unset.

    The server conventionally lives inside the vault it serves
    (``<vault>/_meta/mcp-server-py/...``), so walk up from this module to the
    nearest ancestor named ``_meta`` and use its parent. Works regardless of
    the process working directory, launcher, or OS. Falls back to ``~/vault``
    when the package is installed outside a vault tree.
    """
    for ancestor in Path(__file__).resolve().parents:
        if ancestor.name == "_meta":
            return ancestor.parent
    return Path.home() / "vault"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Vault root. Override via the HIVE_PATH env var; defaults to the vault
    # tree this server lives in (see _detect_hive_root), else ~/vault.
    hive_path: Path = Field(default_factory=_detect_hive_root)
    obsidian_rest_url: str = "https://127.0.0.1:27124"
    obsidian_api_key: str = ""
    obsidian_rest_api_version_min: str = "3.6.2"
    obsidian_verify_tls: str = "false"
    obsidian_recheck_interval_sec: int = 30
    obsidian_fallback_mode: FallbackMode = FallbackMode.AUTO
    # Tool surface: "full" registers all 23 tools; "lean" registers the 8-tool
    # core (token-budget clients). server.py reads HIVEMIND_PROFILE from the
    # process environment at import time (FastMCP registration happens at
    # import) and writes the normalized value back, so set the profile via the
    # process env, not the .env file.
    hivemind_profile: Literal["full", "lean"] = "full"
    hivemind_log_level: str = "INFO"
    hivemind_log_file: str = ""

    # Hybrid dense retrieval (hive_retrieve).
    # backend: auto | onnx | hashing | none
    hivemind_embeddings_backend: str = "auto"
    # Directory containing model.onnx + tokenizer.json for the ONNX backend.
    hivemind_embeddings_model_dir: str = ""
    # Vector dimension for the dependency-free hashing fallback backend.
    hivemind_embeddings_dim: int = 256
    # Weight of the z-normalized dense signal vs the keyword base in fusion.
    # Only used by the "znorm" fusion strategy.
    hivemind_dense_weight: float = 1.0
    # Hybrid stage-1 fusion strategy: rrf (Reciprocal Rank Fusion, default)
    # | znorm (score-level z-norm sum, retained for rollback).
    hivemind_fusion: str = "rrf"

    @field_validator("hivemind_fusion")
    @classmethod
    def validate_fusion(cls, v: str) -> str:
        mode = v.strip().lower()
        if mode not in ("rrf", "znorm"):
            logger.warning("Unknown hivemind_fusion %r; falling back to rrf", v)
            return "rrf"
        return mode

    @field_validator("hive_path")
    @classmethod
    def resolve_hive_path(cls, v: Path) -> Path:
        return v.resolve()

    @field_validator("hivemind_profile", mode="before")
    @classmethod
    def normalize_profile(cls, v: object) -> object:
        # Mirror server.py's graceful fallback: an invalid profile must warn
        # and run "full", never crash the server at lifespan startup.
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized not in ("full", "lean"):
                logger.warning("Unknown HIVEMIND_PROFILE %r; defaulting to 'full'", v)
                return "full"
            return normalized
        return v

    @model_validator(mode="after")
    def resolve_api_key_from_keyring(self) -> Settings:
        if self.obsidian_api_key:
            return self
        try:
            import keyring as kr

            secret = kr.get_password("hivemind", "obsidian-rest")
            if secret:
                self.obsidian_api_key = secret
                logger.info("API key resolved from keyring")
                return self
        except Exception:
            logger.debug("keyring fallback failed", exc_info=True)
        logger.warning("No OBSIDIAN_API_KEY found in env or keyring; state will be UNCONFIGURED")
        return self

    @property
    def tls_verify(self) -> bool | str:
        val = self.obsidian_verify_tls.strip().lower()
        if val == "false":
            return False
        if val == "true":
            return True
        return self.obsidian_verify_tls
