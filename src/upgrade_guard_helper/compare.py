"""Diff knobs found in two source trees."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from upgrade_guard_helper.extract import Knob, extract_knobs


@dataclass(frozen=True)
class KnobChange:
    kind: str  # changed, added, removed
    name: str
    old_value: str | None
    new_value: str | None
    language: str
    old_path: str | None = None
    new_path: str | None = None

    def line(self) -> str:
        if self.kind == "changed":
            return f"  changed  {self.name}: {self.old_value} -> {self.new_value}"
        if self.kind == "added":
            return f"  added    {self.name}: {self.new_value}"
        return f"  removed  {self.name}: {self.old_value}"


@dataclass
class Comparison:
    old_label: str
    new_label: str
    changes: list[KnobChange] = field(default_factory=list)

    def report(self) -> str:
        lines = [
            f"upgrade-guard-helper report: {self.old_label} -> {self.new_label}",
        ]
        changed = [c for c in self.changes if c.kind == "changed"]
        added = [c for c in self.changes if c.kind == "added"]
        removed = [c for c in self.changes if c.kind == "removed"]
        if not self.changes:
            lines.append("No knob defaults changed.")
            lines.append("")
            return "\n".join(lines)
        lines.append(
            f"Found {len(changed)} changed, {len(added)} added, {len(removed)} removed knob(s):"
        )
        lines.append("")
        for group in (changed, added, removed):
            for change in group:
                lines.append(change.line())
        lines.append("")
        return "\n".join(lines)


def compare_maps(
    old: dict[str, Knob],
    new: dict[str, Knob],
    old_label: str,
    new_label: str,
) -> Comparison:
    changes: list[KnobChange] = []
    for name in sorted(set(old) | set(new)):
        left = old.get(name)
        right = new.get(name)
        if left and right:
            if left.value != right.value:
                changes.append(
                    KnobChange(
                        kind="changed",
                        name=name,
                        old_value=left.value,
                        new_value=right.value,
                        language=right.language or left.language,
                        old_path=left.path,
                        new_path=right.path,
                    )
                )
        elif right and not left:
            changes.append(
                KnobChange(
                    kind="added",
                    name=name,
                    old_value=None,
                    new_value=right.value,
                    language=right.language,
                    new_path=right.path,
                )
            )
        elif left and not right:
            changes.append(
                KnobChange(
                    kind="removed",
                    name=name,
                    old_value=left.value,
                    new_value=None,
                    language=left.language,
                    old_path=left.path,
                )
            )
    changes.sort(key=lambda c: ({"changed": 0, "added": 1, "removed": 2}[c.kind], c.name))
    return Comparison(old_label=old_label, new_label=new_label, changes=changes)


def compare_trees(old_root: Path, new_root: Path, old_label: str | None = None, new_label: str | None = None) -> Comparison:
    return compare_maps(
        extract_knobs(old_root),
        extract_knobs(new_root),
        old_label or str(old_root),
        new_label or str(new_root),
    )
