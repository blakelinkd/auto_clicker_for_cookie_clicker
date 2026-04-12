from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """Minimal startup configuration for the application shell."""

    register_hotkeys: bool = True
