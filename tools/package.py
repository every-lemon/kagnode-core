#!/usr/bin/env python3
"""Build deterministic Core UI, Node, Python and source archives. Sign offline."""

import argparse
import base64
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def archive(files, prefix, kind, epoch):
    out = io.BytesIO()
    if kind == "zip":
        with zipfile.ZipFile(
            out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as z:
            for name, data in sorted(files.items()):
                entry = zipfile.ZipInfo(prefix + "/" + name, (2026, 1, 1, 0, 0, 0))
                entry.external_attr = 0o100644 << 16
                entry.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(entry, data)
    else:
        with tarfile.open(fileobj=out, mode="w") as t:
            for name, data in sorted(files.items()):
                info = tarfile.TarInfo(prefix + "/" + name)
                info.size = len(data)
                info.mode = 0o644
                info.mtime = epoch
                t.addfile(info, io.BytesIO(data))
        raw = out.getvalue()
        return (
            gzip.compress(raw, mtime=0)
            if kind == "tar.gz"
            else __import__("lzma").compress(raw, preset=9)
        )
    return out.getvalue()


def build(destination, signing_key=None):
    version = json.loads((ROOT / "package.json").read_text())["version"]
    destination.mkdir(parents=True, exist_ok=True)
    epoch = int(
        os.environ.get(
            "SOURCE_DATE_EPOCH",
            subprocess.check_output(
                ["git", "log", "-1", "--format=%ct"], cwd=ROOT, text=True
            ).strip(),
        )
    )
    bundle = json.loads((ROOT / "dist/bundle.json").read_text())
    manifest = json.loads((ROOT / "dist/manifest.json").read_text())
    files = {
        name: base64.b64decode(item["data"]) for name, item in bundle["files"].items()
    }
    prefix = "kagnode-core-" + version
    for kind in ["tar.gz", "tar.xz", "zip"]:
        (destination / (prefix + "-ui." + kind)).write_bytes(
            archive(files, prefix, kind, epoch)
        )
    # Optional icon assets are deliberately outside the automatic UI manifest.
    icon_files = {
        str(p.relative_to(ROOT / "dist/icons")): p.read_bytes()
        for p in (ROOT / "dist/icons").rglob("*")
        if p.is_file() and not p.is_symlink()
    }
    for kind in ["tar.gz", "zip"]:
        (destination / (prefix + "-icons." + kind)).write_bytes(
            archive(icon_files, prefix + "-icons", kind, epoch)
        )
    (destination / (prefix + "-icons.tgz")).write_bytes(
        archive(icon_files, "package", "tar.gz", epoch)
    )
    primary = destination / (prefix + "-ui.tar.gz")
    manifest["archive"] = {
        "name": primary.name,
        "size": primary.stat().st_size,
        "sha256": digest(primary.read_bytes()),
    }
    (destination / "core-manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n"
    )
    if signing_key:
        subprocess.run(
            [
                "openssl",
                "pkeyutl",
                "-sign",
                "-rawin",
                "-inkey",
                str(signing_key),
                "-in",
                str(destination / "core-manifest.json"),
                "-out",
                str(destination / "core-manifest.sig"),
            ],
            check=True,
        )
    node = {
        "index.mjs": (ROOT / "dist/node/kagnode-core.mjs").read_bytes(),
        "index.d.mts": (ROOT / "dist/node/kagnode-core.d.mts").read_bytes(),
        "LICENSE": (ROOT / "LICENSE").read_bytes(),
        "ARTWORK-LICENSE": (ROOT / "assets/ARTWORK-LICENSE").read_bytes(),
        "README.md": (ROOT / "README.md").read_bytes(),
        "package.json": json.dumps(
            {
                "name": "@kagnode/core",
                "version": version,
                "type": "module",
                "license": "AGPL-3.0-only",
                "main": "index.mjs",
                "types": "index.d.mts",
                "engines": {"node": ">=24"},
                "exports": {".": {"types": "./index.d.mts", "import": "./index.mjs"}},
            },
            indent=2,
        ).encode(),
    }
    (destination / (prefix + "-node.tgz")).write_bytes(
        archive(node, "package", "tar.gz", epoch)
    )
    metadata = f"kagnode_core-{version}.dist-info"
    wheel = {
        "kagnode_core.py": (ROOT / "dist/python/kagnode_core.py").read_bytes(),
        "kagnode_core_manager.py": (ROOT / "packages/python/manager.py").read_bytes(),
        metadata
        + "/METADATA": f"Metadata-Version: 2.4\nName: kagnode-core\nVersion: {version}\nRequires-Python: >=3.10\nLicense-Expression: AGPL-3.0-only\nSummary: Local KagNode UI adapters and signed asset manager\n\n".encode(),
        metadata
        + "/WHEEL": b"Wheel-Version: 1.0\nGenerator: KagNode Core\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        metadata + "/licenses/LICENSE": (ROOT / "LICENSE").read_bytes(),
        metadata + "/licenses/ARTWORK-LICENSE": (
            ROOT / "assets/ARTWORK-LICENSE"
        ).read_bytes(),
    }
    records = []
    for name, data in sorted(wheel.items()):
        records.append(
            [
                name,
                "sha256="
                + base64.urlsafe_b64encode(hashlib.sha256(data).digest())
                .decode()
                .rstrip("="),
                str(len(data)),
            ]
        )
    records.append([metadata + "/RECORD", "", ""])
    record = io.StringIO()
    csv.writer(record, lineterminator="\n").writerows(records)
    wheel[metadata + "/RECORD"] = record.getvalue().encode()
    with zipfile.ZipFile(
        destination / f"kagnode_core-{version}-py3-none-any.whl",
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as z:
        for name, data in sorted(wheel.items()):
            entry = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(entry, data)
    source = {}
    for folder in [
        "assets",
        "web",
        "packages",
        "tools",
        "tests",
        "docs",
        "examples",
        "packaging",
    ]:
        for p in (ROOT / folder).rglob("*"):
            if p.is_file() and not p.is_symlink() and "__pycache__" not in p.parts:
                source[str(p.relative_to(ROOT))] = p.read_bytes()
    for name in [
        "LICENSE",
        "README.md",
        "CHANGELOG.md",
        "package.json",
        "package-lock.json",
    ]:
        source[name] = (ROOT / name).read_bytes()
    for kind in ["tar.gz", "tar.xz", "zip"]:
        (destination / (prefix + "-source." + kind)).write_bytes(
            archive(source, prefix, kind, epoch)
        )
    for filename, source in [
        ("LICENSE.txt", "LICENSE"),
        ("ARTWORK-LICENSE.txt", "assets/ARTWORK-LICENSE"),
        ("INSTALL.md", "docs/OPERATIONS.md"),
    ]:
        (destination / filename).write_bytes((ROOT / source).read_bytes())
    checks = {
        p.name: digest(p.read_bytes())
        for p in sorted(destination.iterdir())
        if p.is_file() and p.name not in ["SHA256SUMS", "release-manifest.json"]
    }
    (destination / "SHA256SUMS").write_text(
        "".join(f"{sha}  {name}\n" for name, sha in checks.items())
    )
    (destination / "release-manifest.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "version": version,
                "source_commit": bundle["source_commit"],
                "packages": [
                    {"name": n, "sha256": s, "size": (destination / n).stat().st_size}
                    for n, s in checks.items()
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Built {len(checks)} Core packages; signed={bool(signing_key)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT / "release")
    p.add_argument("--signing-key", type=Path)
    a = p.parse_args()
    build(a.output, a.signing_key)
