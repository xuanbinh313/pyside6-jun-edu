import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

REQUIRED_FIELDS = {
    "id",
    "name",
    "version",
    "api_version",
    "entry",
    "enabled",
    "execution",
}

EXCLUDED_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "build",
    "dist",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".log",
}

REQUIRED_WORKERS = {
    "agent": Path("workers/agent-worker.exe"),
    "ocr": Path("workers/ocr-worker.exe"),
}


def _read_manifest(path: Path) -> Dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid plugin manifest JSON: {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"Plugin manifest must be an object: {path}")
    return raw


def _validate_manifest(plugin_dir: Path, manifest: Mapping[str, Any]) -> None:
    missing = sorted(REQUIRED_FIELDS - set(manifest))
    if missing:
        raise ValueError(
            f"{plugin_dir / 'plugin.json'} is missing: {', '.join(missing)}"
        )

    entry = manifest.get("entry")
    if not isinstance(entry, str) or not entry.strip():
        raise ValueError(f"{plugin_dir / 'plugin.json'} has an invalid entry field")
    if ".." in Path(entry).parts:
        raise ValueError(f"{plugin_dir / 'plugin.json'} entry cannot contain '..'")
    entry_path = (plugin_dir / entry).resolve()
    plugin_root = plugin_dir.resolve()
    try:
        entry_path.relative_to(plugin_root)
    except ValueError as exc:
        raise ValueError(
            f"{plugin_dir / 'plugin.json'} entry must stay inside the plugin folder"
        ) from exc
    if not entry_path.is_file():
        raise ValueError(f"Plugin entry does not exist: {entry_path}")

    plugin_id = manifest.get("id")
    if isinstance(plugin_id, str):
        required_worker = REQUIRED_WORKERS.get(plugin_id)
        if required_worker is not None:
            worker_path = plugin_dir / required_worker
            if not worker_path.is_file():
                raise ValueError(
                    "Missing plugin worker executable: "
                    f"{worker_path}. Run cmd/build_plugin_workers.py before staging."
                )


def _plugin_dirs(source_dir: Path) -> Iterable[Path]:
    if not source_dir.exists():
        return []
    return sorted(path for path in source_dir.iterdir() if path.is_dir())


def _ignore_names(directory: str, names: list[str]) -> set[str]:
    _ = directory
    ignored: set[str] = set()
    for name in names:
        path = Path(name)
        if name in EXCLUDED_DIRS or path.suffix in EXCLUDED_SUFFIXES:
            ignored.add(name)
    return ignored


def stage_plugins(source_dir: Path, output_dir: Path, clean: bool) -> list[str]:
    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    staged: list[str] = []
    for plugin_dir in _plugin_dirs(source_dir):
        manifest_path = plugin_dir / "plugin.json"
        if not manifest_path.is_file():
            continue
        manifest = _read_manifest(manifest_path)
        _validate_manifest(plugin_dir, manifest)
        target_dir = output_dir / plugin_dir.name
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(plugin_dir, target_dir, ignore=_ignore_names)
        staged.append(str(manifest.get("id") or plugin_dir.name))
    return staged


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate and stage Jun Edu plugins for a built app."
    )
    parser.add_argument("--src", default="plugins", help="Source plugins directory.")
    parser.add_argument(
        "--out", default="dist/plugins", help="Destination plugins directory."
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove the destination plugins directory before staging.",
    )
    args = parser.parse_args()

    staged = stage_plugins(Path(args.src), Path(args.out), clean=args.clean)
    if staged:
        print("staged plugins: " + ", ".join(staged))
    else:
        print("no plugins staged")


if __name__ == "__main__":
    main()
