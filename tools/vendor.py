"""Copy generated pinned offline adapters; all editable UI stays in Core."""

from pathlib import Path
import hashlib, json, shutil

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
    if name == "proxy-manager":
        destination = root / "vendor/core-rust"
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(
            ROOT / "packages/rust",
            destination,
            ignore=shutil.ignore_patterns("target", "__pycache__", "*.pyc"),
        )
        assets = root / "vendor/core"
        assets.mkdir(parents=True, exist_ok=True)
        bundle = json.loads((ROOT / "dist/bundle.json").read_text())
        import base64

        for filename, item in bundle["files"].items():
            (assets / filename).write_bytes(base64.b64decode(item["data"]))
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
            ignore=shutil.ignore_patterns(
                "target", "node_modules", "__pycache__", "*.pyc"
            ),
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
    bundle = json.loads((ROOT / "dist/bundle.json").read_text())
    value["baseline"] = bundle["version"]
    value["adapter"] = bundle["version"]
    value["patch_range"] = ".".join(bundle["version"].split(".")[:2]) + ".x"
    value["fallback_manifest_sha256"] = hashlib.sha256(
        (ROOT / "dist/bundle.json").read_bytes()
    ).hexdigest()
    # Adoption validates the UI declaration against this signed UI manifest.
    # A full package may be assembled from a later commit with unchanged UI.
    manifest_path = ROOT / "dist/core-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest["version"] != bundle["version"]:
        raise ValueError("Core UI manifest and fallback versions differ")
    value["source_commit"] = manifest["source_commit"]
    value["signed_ui_manifest_sha256"] = hashlib.sha256(
        manifest_path.read_bytes()
    ).hexdigest()
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
