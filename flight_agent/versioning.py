"""Artifact-versioning helper, modeled on starter_v0/versioning.py.

Tracks the two files that define the LLM-facing contract — the system
prompt and the tool-calling declarations — as a single hash-derived
"artifact_version". Any change to either bumps the hash; a change to only
one of them leaves the other's hash unchanged (mirrors starter_v0's
convention, see artifacts/version_log.csv).

The human-readable `version` tag (v0, v1, v2, ...) is tracked separately in
VERSION and bumped manually whenever a change is logged in
artifacts/version_log.csv — it does not have to change in lockstep with the
hash (a UI-only change, for example, bumps `version` without touching
prompt_hash/tools_hash).
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SYSTEM_PROMPT_PATH = ROOT / "artifacts" / "system_prompt.md"
TOOLS_SCHEMA_PATH = ROOT / "tools" / "schemas.py"
VERSION_FILE = ROOT / "VERSION"
VERSION_LOG_PATH = ROOT / "artifacts" / "version_log.csv"


@dataclass(frozen=True)
class ArtifactVersion:
    version: str
    artifact_version: str
    prompt_hash: str
    tools_hash: str


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def short_hash(value: str, length: int = 12) -> str:
    return value[:length]


def build_artifact_version(
    version: str,
    system_prompt_path: Path = SYSTEM_PROMPT_PATH,
    tools_path: Path = TOOLS_SCHEMA_PATH,
) -> ArtifactVersion:
    prompt_hash = file_hash(system_prompt_path)
    tools_hash = file_hash(tools_path)
    artifact_version = f"{version}+p{short_hash(prompt_hash)}+t{short_hash(tools_hash)}"
    return ArtifactVersion(
        version=version,
        artifact_version=artifact_version,
        prompt_hash=prompt_hash,
        tools_hash=tools_hash,
    )


def artifact_version_dict(version: ArtifactVersion) -> dict[str, str]:
    return asdict(version)


def current_version_tag() -> str:
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text(encoding="utf-8").strip() or "v0"
    return "v0"


def current_artifact_version() -> ArtifactVersion:
    return build_artifact_version(current_version_tag())
