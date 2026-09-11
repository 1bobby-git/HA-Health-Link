"""Runtime models for HealthLink."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

if False:  # pragma: no cover
    from .companion import CompanionImporter
    from .coordinator import HealthLinkCoordinator
    from .storage.db import HealthLinkStore

@dataclass(slots=True)
class HealthLinkRuntimeData:
    store: "HealthLinkStore"
    coordinator: "HealthLinkCoordinator"
    companion: "CompanionImporter | None" = None
    webhook_id: str | None = None
    unload_callbacks: list[Any] = field(default_factory=list)
