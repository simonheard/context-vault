from __future__ import annotations

from contextvault.repository import VaultRepository
from contextvault.services import ProfileService


class SummaryService:
    def __init__(self, repository: VaultRepository):
        self.repository = repository
        self.profile = ProfileService(repository)

    def render(self, summary_type: str, space: str = "personal") -> str:
        if summary_type in {"personal", "full"}:
            return self.profile.markdown_profile(space)
        if summary_type in {"work", "project"}:
            prefixes = (
                ("employment.", "skill.", "project.", "goal.")
                if summary_type == "work"
                else ("project.", "goal.", "skill.")
            )
            claims = [
                claim
                for claim in self.profile.current_claims(space)
                if claim.attribute.startswith(prefixes)
            ]
            title = "Work profile" if summary_type == "work" else "Project context"
            lines = [f"# {title}", ""]
            lines.extend(f"- {claim.attribute}: {claim.value_text}" for claim in claims)
            return "\n".join(lines).rstrip() + "\n"
        if summary_type == "devices":
            lines = ["# Devices and development environments", ""]
            for device in self.repository.list_devices():
                config = device["config"]
                lines.extend(
                    [
                        f"## {device['display_name']}",
                        "",
                        f"- OS: {config.get('os')} {config.get('os_release')}",
                        f"- Model: {config.get('model')}",
                        f"- Architecture: {config.get('architecture')}",
                        f"- Memory bytes: {config.get('memory_bytes')}",
                    ]
                )
                tools = config.get("tools", {})
                if tools:
                    lines.append("- Tools: " + ", ".join(f"{key} ({value})" for key, value in tools.items()))
                lines.append("")
            return "\n".join(lines).rstrip() + "\n"
        if summary_type == "recent":
            events = self.repository.list_events(limit=50)
            lines = ["# Recent ContextVault changes", ""]
            lines.extend(
                f"- {event.created_at}: {event.event_type} ({event.aggregate_type})"
                for event in reversed(events)
            )
            return "\n".join(lines).rstrip() + "\n"
        raise ValueError(f"Unsupported summary type: {summary_type}")
