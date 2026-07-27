import argparse
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence


@dataclass(frozen=True)
class PluginWorkerBuild:
    plugin_id: str
    source: Path
    name: str
    excludes: Sequence[str]
    hidden_imports: Sequence[str]
    collect_submodules: Sequence[str]
    copy_metadata: Sequence[str]


WORKERS: Sequence[PluginWorkerBuild] = (
    PluginWorkerBuild(
        plugin_id="agent",
        source=Path("plugins/agent/worker.py"),
        name="agent-worker",
        excludes=("paddle", "paddleocr", "paddlepaddle", "torch", "torchvision"),
        hidden_imports=(),
        collect_submodules=("google.genai",),
        copy_metadata=("google-genai",),
    ),
    PluginWorkerBuild(
        plugin_id="ocr",
        source=Path("plugins/ocr/worker.py"),
        name="ocr-worker",
        excludes=(
            "google.genai",
            "matplotlib",
            "PySide6",
            "qtpy",
            "shiboken6",
            "torch",
            "torchvision",
        ),
        hidden_imports=("fitz", "paddleocr"),
        collect_submodules=("paddleocr",),
        copy_metadata=("paddleocr",),
    ),
)


def _python_path() -> Path:
    candidate = Path(".venv/Scripts/python.exe")
    if candidate.is_file():
        return candidate
    candidate = Path(".venv/Scripts/python")
    if candidate.is_file():
        return candidate
    return Path("python")


def _pyinstaller_command_prefix() -> list[str]:
    script = (
        "import sys; "
        "sys.setrecursionlimit(10000); "
        "from PyInstaller.__main__ import run; "
        "run(sys.argv[1:])"
    )
    return [str(_python_path()), "-c", script]


def _build_worker(worker: PluginWorkerBuild, clean: bool) -> None:
    if not worker.source.is_file():
        raise FileNotFoundError(f"Missing worker source: {worker.source}")

    output_dir = Path("plugins") / worker.plugin_id / "workers"
    work_dir = Path("build") / "plugin-workers" / worker.plugin_id
    if clean:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(work_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    command: List[str] = [
        *_pyinstaller_command_prefix(),
        "--onefile",
        "--clean",
        "--noconfirm",
        "--name",
        worker.name,
        "--distpath",
        str(output_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(work_dir),
    ]
    for excluded in worker.excludes:
        command.extend(["--exclude-module", excluded])
    for hidden_import in worker.hidden_imports:
        command.extend(["--hidden-import", hidden_import])
    for module_name in worker.collect_submodules:
        command.extend(["--collect-submodules", module_name])
    for distribution_name in worker.copy_metadata:
        command.extend(["--copy-metadata", distribution_name])
    command.append(str(worker.source))

    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build plugin worker executables for Jun Edu."
    )
    parser.add_argument(
        "--plugin",
        action="append",
        choices=[worker.plugin_id for worker in WORKERS],
        help="Build only the selected plugin id. Can be repeated.",
    )
    parser.add_argument("--clean", action="store_true", help="Clean worker outputs.")
    args = parser.parse_args()

    selected = set(args.plugin or [worker.plugin_id for worker in WORKERS])
    for worker in WORKERS:
        if worker.plugin_id in selected:
            print(f"building {worker.plugin_id} worker...")
            _build_worker(worker, clean=args.clean)
    print("plugin workers built")


if __name__ == "__main__":
    main()
