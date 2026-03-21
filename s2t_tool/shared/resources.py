from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from typing import Any


def load_text_resource(filename: str) -> str:
    module_dir = Path(__file__).resolve().parent
    search_dirs = [
        module_dir,
        module_dir.parent,
        module_dir.parent.parent,
    ]
    for base_dir in search_dirs:
        file_path = base_dir / filename
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")

    archive_path = Path(sys.argv[0]).resolve()
    if archive_path.exists() and archive_path.suffix == ".pyz":
        with zipfile.ZipFile(archive_path, "r") as archive:
            try:
                with archive.open(filename, "r") as resource_file:
                    return resource_file.read().decode("utf-8")
            except KeyError:
                pass

    raise FileNotFoundError(f"Resource not found: {filename}")


def load_json_resource(filename: str) -> dict[str, Any]:
    return json.loads(load_text_resource(filename))

