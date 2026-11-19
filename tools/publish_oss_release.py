"""Publish only this product's immutable ZIP, then its JSON/JS after verification.

Credentials stay in the existing Alibaba CLI OAuth store and process memory.
No ACL changes, deletion, broad listing, or other product objects are supported.
"""

import argparse
import hashlib
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

try:
    from tools.verify_release import verify
    from tools.update_client import PRODUCT, ORIGIN, version_tuple
except ModuleNotFoundError:
    from verify_release import verify
    from update_client import PRODUCT, ORIGIN, version_tuple


BUCKET = "luotuoruanjiangengx"
ENDPOINT = "https://oss-cn-beijing.aliyuncs.com"


def public_hash(url):
    sha = hashlib.sha256()
    count = 0
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=45) as remote:
        for chunk in iter(lambda: remote.read(1024 * 1024), b""):
            sha.update(chunk)
            count += len(chunk)
    return sha.hexdigest(), count


def get_bucket(cli, profile):
    import oss2
    response = subprocess.run([str(cli), "sts", "GetCallerIdentity", "--profile", profile], capture_output=True, timeout=45)
    if response.returncode:
        raise RuntimeError("Existing Alibaba CLI OAuth session unavailable; reauthorize through the official CLI, never paste keys into this tool")
    config = json.loads((Path.home() / ".aliyun" / "config.json").read_text(encoding="utf-8-sig"))
    credential = next(value for value in config["profiles"] if value["name"] == profile)
    if credential.get("mode") != "OAuth":
        raise ValueError("This publisher requires an existing temporary OAuth profile")
    auth = oss2.StsAuth(credential["access_key_id"], credential["access_key_secret"], credential["sts_token"])
    return oss2.Bucket(auth, ENDPOINT, BUCKET)


def existing(bucket, key):
    import oss2
    try:
        response = bucket.get_object(key)
        return response.read(), response.etag
    except oss2.exceptions.NoSuchKey:
        return None, None


def publish(directory, version, stage, cli=None, profile=None, dry_run=False):
    version_tuple(version)
    directory = Path(directory)
    archive = directory / f"{PRODUCT}-{version}-windows-x64.zip"
    manifest = directory / f"{PRODUCT}-{version}-latest.json"
    site = directory / f"{PRODUCT}-{version}-latest.js"
    result = verify(archive, manifest, site)
    if result["version"] != version:
        raise ValueError("Requested version and manifest differ")
    package_key = f"packages/{PRODUCT}/{version}/{archive.name}"
    keys = [package_key] if stage == "package" else [f"updates/{PRODUCT}/latest.js", f"updates/{PRODUCT}/latest.json"]
    if dry_run:
        return {"stage": stage, "dryRun": True, "objects": keys, "verified": result}
    if not cli or not profile:
        raise ValueError("--cli and --profile are required for publication")
    bucket = get_bucket(cli, profile)
    old_package, _ = existing(bucket, package_key)
    if old_package is not None:
        if hashlib.sha256(old_package).hexdigest() != result["sha256"]:
            raise ValueError("Immutable version key exists with different bytes; stopped")
    elif stage == "package":
        bucket.put_object_from_file(package_key, str(archive), headers={"x-oss-forbid-overwrite": "true", "Content-Type": "application/zip", "Cache-Control": "public,max-age=31536000,immutable"})
    else:
        raise ValueError("Upload and verify immutable package before manifests")
    sha, count = public_hash(result["url"])
    if sha != result["sha256"] or count != result["bytes"]:
        raise ValueError("Public ZIP download size/hash mismatch; no manifests switched")
    if stage == "manifests":
        changes = [(keys[0], site.read_bytes(), "application/javascript; charset=utf-8"), (keys[1], manifest.read_bytes(), "application/json; charset=utf-8")]
        previous = []
        for key, body, content_type in changes:
            old, etag = existing(bucket, key)
            if key.endswith(".json") and old:
                current = json.loads(old)
                if current.get("productId") != PRODUCT or version_tuple(current["version"]) > version_tuple(version):
                    raise ValueError("Manifest product mismatch or downgrade refused")
                if current["version"] == version and old != body:
                    raise ValueError("Same-version manifest differs; manual inspection required")
            previous.append((key, body, content_type, old, etag))
        # Backups contain public metadata only; never copy CLI credential files.
        backup = directory / ("previous-public-manifests-" + __import__("uuid").uuid4().hex)
        backup.mkdir()
        for key, body, content_type, old, etag in previous:
            if old is not None:
                (backup / Path(key).name).write_bytes(old)
            latest, latest_etag = existing(bucket, key)
            if latest != old or latest_etag != etag:
                raise ValueError("Manifest changed concurrently; stopped")
            if latest != body:
                headers = {"Content-Type": content_type, "Cache-Control": "no-cache"}
                if old is None:
                    headers["x-oss-forbid-overwrite"] = "true"
                bucket.put_object(key, body, headers=headers)
            downloaded = urllib.request.urlopen(urllib.request.Request(ORIGIN + "/" + key, headers={"Cache-Control": "no-cache"}), timeout=30).read()
            if downloaded != body:
                raise ValueError("Public manifest readback differs")
    return {"stage": stage, "objects": keys, "publicZipVerified": True, "sha256": sha, "bytes": count}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--stage", required=True, choices=("package", "manifests"))
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--profile")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(publish(args.directory, args.version, args.stage, args.cli, args.profile, args.dry_run), ensure_ascii=False))
