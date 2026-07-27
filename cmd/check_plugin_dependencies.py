import argparse
import importlib.util
from typing import Dict, List

PLUGIN_IMPORTS: Dict[str, List[str]] = {
    "agent": ["google.genai"],
    "ocr": ["fitz", "paddleocr"],
}


def missing_imports(plugin_ids: List[str]) -> Dict[str, List[str]]:
    missing: Dict[str, List[str]] = {}
    for plugin_id in plugin_ids:
        imports = PLUGIN_IMPORTS.get(plugin_id, [])
        for import_name in imports:
            if importlib.util.find_spec(import_name) is None:
                missing.setdefault(plugin_id, []).append(import_name)
    return missing


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check Python dependencies required by bundled Jun Edu plugins."
    )
    parser.add_argument(
        "plugins",
        nargs="*",
        default=sorted(PLUGIN_IMPORTS),
        help="Plugin ids to check. Defaults to all known bundled plugins.",
    )
    args = parser.parse_args()

    missing = missing_imports(list(args.plugins))
    if missing:
        for plugin_id, imports in missing.items():
            print(f"{plugin_id}: missing {', '.join(imports)}")
        raise SystemExit(1)
    print("plugin dependencies ok")


if __name__ == "__main__":
    main()
