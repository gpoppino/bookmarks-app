"""Package an explicit list of runtime files, never local settings or dependencies."""

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parent.parent
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
files = [
    "manifest.json", "background.js", "controller.js", "core.js",
    "popup.html", "popup.js", "options.html", "options.js", "styles.css",
    "icons/bookmark.svg",
]
destination = root / "dist" / f"bookmarks-app-firefox-{manifest['version']}.zip"
destination.parent.mkdir(exist_ok=True)
with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
    for name in files:
        archive.write(root / name, name)
print(f"Created {destination}")
print("Unsigned development package. Mozilla signing is required for permanent installation.")
