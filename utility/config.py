"""Configuration loader for FlexSimMCP."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import tomli

logger = logging.getLogger(__name__)


class Config:
    """Configuration management for FlexSimMCP."""

    def __init__(self, config_path: str | Path | None = None):
        """Initialize configuration.

        Args:
            config_path: Path to config.toml file. If None, searches for config.toml
                        in the following order:
                        1. Environment variable FLEXSIM_CONFIG_PATH
                        2. Current working directory
                        3. Project root directory
        """
        self._config: dict[str, Any] = {}
        self._config_path = self._find_config_file(config_path)
        self._load_config()
        self._apply_environment_overrides()

    def _find_config_file(self, config_path: str | Path | None) -> Path | None:
        """Find configuration file."""
        if config_path:
            path = Path(config_path)
            if path.exists():
                return path
            logger.warning(f"Config file not found at {path}")
            return None

        # Check environment variable
        env_path = os.environ.get("FLEXSIM_CONFIG_PATH")
        if env_path:
            path = Path(env_path)
            if path.exists():
                return path
            logger.warning(f"Config file not found at env path {path}")

        # Check current working directory
        cwd_config = Path.cwd() / "config.toml"
        if cwd_config.exists():
            return cwd_config

        # Check project root (parent of mcp_server)
        project_root = Path(__file__).parent.parent / "config.toml"
        if project_root.exists():
            return project_root

        logger.warning("No config.toml file found, using defaults")
        return None

    def _load_config(self) -> None:
        """Load configuration from TOML file."""
        if not self._config_path:
            self._set_defaults()
            return

        try:
            with open(self._config_path, "rb") as f:
                self._config = tomli.load(f)
            logger.info(f"Loaded configuration from {self._config_path}")
        except Exception as e:
            logger.error(f"Failed to load config from {self._config_path}: {e}")
            self._set_defaults()

    def _set_defaults(self) -> None:
        """Set default configuration values."""
        self._config = {
            "flexsim": {
                "install_path": "FlexSimDev/program",
            },
            "python": {
                "version": "3.10",
            },
            "server": {
                "name": "FlexSimPy MCP Server",
                "version": "0.1.0",
                "http_endpoint": "http://127.0.0.1:8088/mcp",
            },
            "session": {
                "reuse_policy": "singleton",
            },
            "logging": {
                "level": "INFO",
            },
        }

    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides."""
        # Override FlexSim install path if env var is set
        flexsim_path = os.environ.get("FLEXSIM_INSTALL_PATH")
        if flexsim_path:
            self._config.setdefault("flexsim", {})["install_path"] = flexsim_path
            logger.info(f"Overriding FlexSim path from environment: {flexsim_path}")

        # Override Python version if env var is set
        python_version = os.environ.get("FLEXSIM_PYTHON_VERSION")
        if python_version:
            self._config.setdefault("python", {})["version"] = python_version
            logger.info(f"Overriding Python version from environment: {python_version}")

        # Override logging level if env var is set
        log_level = os.environ.get("FLEXSIM_LOG_LEVEL")
        if log_level:
            self._config.setdefault("logging", {})["level"] = log_level
            logger.info(f"Overriding log level from environment: {log_level}")

    @property
    def flexsim_install_path(self) -> str:
        """Get FlexSim installation path."""
        return self._config.get("flexsim", {}).get("install_path", "")

    @property
    def flexsim_alternative_paths(self) -> list[str]:
        """Get alternative FlexSim installation paths."""
        return self._config.get("flexsim", {}).get("alternative_paths", [])

    @property
    def python_version(self) -> str:
        """Get Python version for FlexSimPy."""
        return self._config.get("python", {}).get("version", "3.10")

    @property
    def server_name(self) -> str:
        """Get server name."""
        return self._config.get("server", {}).get("name", "FlexSimPy MCP Server")

    @property
    def server_version(self) -> str:
        """Get server version."""
        return self._config.get("server", {}).get("version", "0.1.0")

    @property
    def http_endpoint(self) -> str:
        """Get HTTP endpoint."""
        return self._config.get("server", {}).get("http_endpoint", "http://127.0.0.1:8088/mcp")

    @property
    def session_reuse_policy(self) -> str:
        """Get session reuse policy."""
        return self._config.get("session", {}).get("reuse_policy", "singleton")

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self._config.get("logging", {}).get("level", "INFO")

    @property
    def log_file(self) -> str | None:
        """Get log file path if configured."""
        return self._config.get("logging", {}).get("log_file")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation key.

        Args:
            key: Configuration key in dot notation (e.g., "flexsim.install_path")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value

    def __repr__(self) -> str:
        """String representation."""
        return f"Config(path={self._config_path}, flexsim={self.flexsim_install_path})"


# Global configuration instance
_config: Config | None = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config) -> None:
    """Set global configuration instance."""
    global _config
    _config = config


def reload_config(config_path: str | Path | None = None) -> Config:
    """Reload configuration from file."""
    global _config
    _config = Config(config_path)
    return _config
