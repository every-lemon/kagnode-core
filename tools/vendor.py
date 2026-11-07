"""Copy generated pinned offline adapters; all editable UI stays in Core."""

from pathlib import Path
import hashlib, json, shutil, subprocess

ROOT = Path(__file__).resolve().parents[1]


def vendor(name, directory, package):
    root = Path(directory)
    if package:
        shutil.copyfile(
            ROOT / "dist/python/kagnode_core.py", root / package / "kagnode_core.py"
        )
    if name in ("media", "official"):
        (root / "vendor").mkdir(exist_ok=True)
        for filename in ["kagnode-core.mjs", "kagnode-core.d.mts"]:
            shutil.copyfile(ROOT / "dist/node" / filename, root / "vendor" / filename)
    if name in ("cli", "logos"):
        location = root / "assets" if name == "cli" else root / "vendor"
        location.mkdir(exist_ok=True)
        shutil.copyfile(ROOT / "dist/bundle.json", location / "core-bundle.json")
    if name == "cli":
        shutil.copyfile(
            ROOT / "packages/python/manager.py", root / "assets/core_manager.py"
        )
    # The complete editable source and notices travel beside every fallback.
    source = root / "vendor/core-source"
    if source.exists():
        shutil.rmtree(source)
    source.mkdir(parents=True)
    for folder in ["web", "packages", "assets"]:
        shutil.copytree(
            ROOT / folder,
            source / folder,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    shutil.copyfile(ROOT / "LICENSE", source / "LICENSE")
    lock = root / "core.lock.json"
    value = (
        json.loads(lock.read_text())
        if lock.exists()
        else {
            "schema": 1,
            "application": name,
            "repository": "every-lemon/kagnode-core",
            "baseline": "1.0.0",
            "adapter": "1.0.0",
            "ui_api": 1,
            "patch_range": "1.0.x",
            "automatic_ui_patches": True,
            "backend_updates": "reviewed",
        }
    )
    value["fallback_manifest_sha256"] = hashlib.sha256(
        (ROOT / "dist/bundle.json").read_bytes()
    ).hexdigest()
    value["source_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    lock.write_text(json.dumps(value, indent=2) + "\n")
    print(name, "pinned local Core refreshed")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--python-package")
    args = parser.parse_args()
    vendor(args.project, args.target, args.python_package)
