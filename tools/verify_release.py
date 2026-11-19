"""Offline verification of the exact files distributed by this product."""

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

try:
    from tools import update_client as update
except ModuleNotFoundError:
    import update_client as update


def verify(archive, manifest, site_manifest):
    archive = Path(archive)
    value = update.validate_manifest(json.loads(Path(manifest).read_text(encoding="utf-8-sig")))
    sha = update.digest(archive)
    if value["sha256"] != sha:
        raise ValueError("Release ZIP/manifest hash mismatch")
    site = Path(site_manifest).read_text(encoding="utf-8-sig").strip()
    prefix = "window.GUANTUIGUANG_LATEST = "
    if not site.startswith(prefix) or not site.endswith(";"):
        raise ValueError("Wrong website manifest assignment")
    site = json.loads(site[len(prefix):-1])
    if site != {"productId": update.PRODUCT, "version": value["version"], "sha256": sha, "fullPackageUrl": value["url"]}:
        raise ValueError("Website/client manifest mismatch")
    with tempfile.TemporaryDirectory(prefix="guantuiguang-package-check-") as temporary:
        update.extract_candidate(archive, Path(temporary) / "stage", value["version"])
    root = f"自动关推广-v{value['version']}/"
    required = {root + name for name in update.ROOT_FILES} | {root + "app/" + name for name in update.APP_FILES}
    with zipfile.ZipFile(archive) as package:
        if set(package.namelist()) != required:
            raise ValueError("Full release must contain the exact safe file set")
        sums = package.read(root + "SHA256SUMS.txt").decode("utf-8")
        expected = {}
        for line in sums.splitlines():
            digest, name = line.split("  ", 1)
            if name in expected:
                raise ValueError("Duplicate manifest filename")
            expected[name] = digest
        actual = {name[len(root):]: hashlib.sha256(package.read(name)).hexdigest() for name in required if not name.endswith("/SHA256SUMS.txt")}
        if expected != actual:
            raise ValueError("Internal SHA256SUMS mismatch")
        config = json.loads(package.read(root + "config.example.json"))
        for account in config["main_accounts"]:
            if account.get("enabled") is not False or not account.get("app_secret", "").startswith("填写"):
                raise ValueError("Configuration template contains enabled or real account values")
    return {"productId": update.PRODUCT, "version": value["version"], "sha256": sha, "bytes": archive.stat().st_size, "url": value["url"], "files": sorted(name[len(root):] for name in required)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--site-manifest", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.manifest, args.site_manifest), ensure_ascii=False))
