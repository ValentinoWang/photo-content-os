#!/usr/bin/env python3
"""Generate confirmed Wan shots through a local DreamVerse service."""

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
from http.client import HTTPException
import http.cookiejar
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, ProxyHandler, Request, build_opener
from uuid import uuid4

FACTS_PATH = (
    Path(__file__).resolve().parents[2] / "integrations/dreamverse/wanxiang-provider/model-facts.json"
)
SHOT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", re.ASCII)
TASK_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", re.ASCII)
DIGEST = re.compile(r"[a-f0-9]{64}", re.ASCII)


class BridgeError(Exception):
    pass


class TransportError(BridgeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


class DreamVerse:
    def __init__(self, url):
        parsed = urlsplit(url)
        if (
            parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parsed.username or parsed.password or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment
        ):
            raise BridgeError("DreamVerse URL must be a bare loopback HTTP origin.")
        self.url = url.rstrip("/")
        self.cookies = http.cookiejar.CookieJar()
        self.opener = build_opener(ProxyHandler({}), NoRedirect(), HTTPCookieProcessor(self.cookies))

    def authenticate(self, launch_url):
        if not launch_url.startswith(self.url + "/?token="):
            raise BridgeError("DreamVerse launch URL must match the loopback origin.")
        try:
            with self.opener.open(launch_url, timeout=10):
                pass
        except HTTPError as error:
            if error.code != 303:
                raise TransportError(f"DreamVerse authentication returned HTTP {error.code}.") from None
        except (OSError, HTTPException):
            raise TransportError("DreamVerse authentication connection failed.") from None
        if not self.cookies:
            raise BridgeError("DreamVerse did not issue an authenticated session.")

    def open(self, route, data=None):
        request = Request(self.url + route, data=None if data is None else encode(data))
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            return self.opener.open(request, timeout=60)
        except HTTPError as error:
            raise TransportError(f"DreamVerse {route} returned HTTP {error.code}.") from None
        except (OSError, HTTPException):
            raise TransportError(f"DreamVerse {route} connection failed.") from None

    def json(self, route, data=None):
        with self.open(route, data) as response:
            try:
                payload = response.read(4 * 1024 * 1024 + 1)
                if len(payload) > 4 * 1024 * 1024:
                    raise BridgeError(f"DreamVerse {route} response exceeds 4 MiB.")
                return json.loads(payload)
            except (ValueError, OSError, HTTPException):
                raise TransportError(f"DreamVerse {route} response could not be read.") from None

    def download(self, asset_id, destination):
        if not isinstance(asset_id, str) or not DIGEST.fullmatch(asset_id):
            raise BridgeError("DreamVerse returned an invalid asset ID.")
        with self.open(f"/dv/assets/{asset_id}") as response:
            with atomic_file(destination) as (file, temporary):
                digest = hashlib.sha256()
                while chunk := response.read(1024 * 1024):
                    digest.update(chunk)
                    file.write(chunk)
                if digest.hexdigest() != asset_id:
                    raise BridgeError("Downloaded DreamVerse asset does not match its ID.")
                publish(file, temporary, destination)


@contextmanager
def atomic_file(path):
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as file:
        temporary = Path(file.name)
        try:
            yield file, temporary
        finally:
            temporary.unlink(missing_ok=True)


def publish(file, temporary, path):
    file.flush()
    os.fsync(file.fileno())
    os.replace(temporary, path)
    # The file and its directory entry must survive independently of the CLI.
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def read_shots(path):
    facts = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(path.read_text(encoding="utf-8"))
    shots = manifest.get("shots") if isinstance(manifest, dict) else manifest
    if not isinstance(shots, list) or not shots:
        raise BridgeError("The shot list must contain at least one shot.")
    normalized = {}
    for index, raw in enumerate(shots, 1):
        shot_id = raw.get("shot_id") if isinstance(raw, dict) else None
        if not isinstance(shot_id, str) or not SHOT_ID.fullmatch(shot_id) or shot_id in normalized:
            raise BridgeError(f"Shot {index} has an invalid or duplicate shot_id.")
        prompt = raw.get("prompt")
        seconds = raw.get("seconds")
        ratio = raw.get("aspect_ratio")
        resolution = raw.get("resolution", "720p")
        model = raw.get("model", facts["modelId"])
        if (
            type(seconds) is not int or seconds not in facts["durationsSec"]
            or ratio not in facts["aspectRatios"] or resolution not in facts["resolutions"]
            or model != facts["modelId"] or not isinstance(prompt, str)
            or not prompt.strip() or len(prompt) > 1500
        ):
            raise BridgeError(f"{shot_id}: use a valid Wan 2.6 prompt, duration, aspect ratio and resolution.")
        normalized[shot_id] = {
            "prompt": prompt, "model": model, "seconds": seconds, "aspect_ratio": ratio, "resolution": resolution,
        }
    return normalized


def specification_hash(spec):
    return digest([spec[k] for k in ("model", "seconds", "aspect_ratio", "resolution", "prompt")])


def write_ledger(path, ledger):
    with atomic_file(path) as (file, temporary):
        file.write((json.dumps(ledger, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        publish(file, temporary, path)


class Bridge:
    def __init__(self, service, directory, wait_seconds, poll_interval):
        self.service = service
        self.directory = directory
        self.path = directory / "ledger.json"
        self.wait_seconds = wait_seconds
        self.poll_interval = poll_interval
        if self.path.exists():
            self.ledger = json.loads(self.path.read_text(encoding="utf-8"))
            if self.ledger.get("version") != 1 or self.ledger.get("dreamverse_url") != service.url:
                raise BridgeError("Ledger version or DreamVerse origin does not match this run.")
        else:
            self.ledger = {
                "version": 1, "dreamverse_url": service.url,
                "project_title": f"Production Desk {uuid4().hex}", "dreamverse_project_id": None, "shots": {},
            }

    def save(self):
        write_ledger(self.path, self.ledger)

    def project(self):
        if self.ledger["dreamverse_project_id"] is None:
            self.save()
            title = self.ledger["project_title"]
            projects = self.service.json("/api/dv/projects")
            existing = next((item for item in projects if item["title"] == title), None)
            project = existing or self.service.json("/api/dv/projects", {"title": title, "surface": "asset_pool"})
            project_id = project["id"]
            if not isinstance(project_id, str) or not TASK_ID.fullmatch(project_id):
                raise BridgeError("DreamVerse returned an invalid project ID.")
            self.ledger["dreamverse_project_id"] = project_id
            self.save()
        return self.ledger["dreamverse_project_id"]

    def operation(self, project, key, spec):
        return {
            "project": project, "operation": "shot.render", "surface": "asset_pool", "inputs": [],
            "intent": f"desk-bridge:{key}",
            "params": {
                "modality": "video", "task": "t2v", "provider": "wanxiang", "model": spec["model"],
                "prompt": spec["prompt"], "duration_sec": spec["seconds"], "aspect_ratio": spec["aspect_ratio"],
                "resolution": spec["resolution"], "seed": int(key[:7], 16), "extra": {"bridge_confirmation": key},
            },
        }

    def run(self, shots, confirmations):
        staged = self.ledger["shots"]
        if set(confirmations) - shots.keys():
            raise BridgeError("Confirmation names a shot absent from the manifest.")
        for shot_id, spec in shots.items():
            old = staged.get(shot_id)
            if old is not None and old["spec_hash"] == specification_hash(spec):
                continue
            if old is not None and old["status"] not in {"completed", "failed", "canceled", "rejected"}:
                raise BridgeError(f"{shot_id}: resolve the previous task before changing its specification.")
            if shot_id not in confirmations:
                raise BridgeError(f"{shot_id}: confirm {spec['model']} / {spec['seconds']}s / "
                                  f"{spec['aspect_ratio']} / {spec['resolution']} with --confirm {shot_id}.")
        project = self.project()
        for shot_id, spec in shots.items():
            hash_value = specification_hash(spec)
            key = digest([project, shot_id, hash_value])
            operation = self.operation(project, key, spec)
            row = staged.get(shot_id)
            if row is None or row["spec_hash"] != hash_value:
                check = self.service.json("/api/dv/operation/check", operation)
                if not isinstance(check, dict) or check.get("problems") != []:
                    raise BridgeError(f"{shot_id}: DreamVerse rejected the render specification.")
                row = {
                    "status": "submitting", "confirmation_key": key, "spec_hash": hash_value,
                    "model": spec["model"], "seconds": spec["seconds"], "aspect_ratio": spec["aspect_ratio"],
                    "resolution": spec["resolution"], "task_id": None, "cloud_status": None,
                    "billed_video_seconds": None, "dreamverse_record_id": None,
                    "dreamverse_video_asset_id": None, "dreamverse_last_frame_asset_id": None,
                    "timeline_clip_id": None, "mp4_path": None, "last_frame_path": None,
                }
                staged[shot_id] = row
                self.save()
                try:
                    reply = self.service.json(
                        "/api/dv/wanxiang/submit", {"project": project, "key": key, "shot_id": shot_id, **spec},
                    )
                except TransportError:
                    self.record_submission(row, None)
                    reply = self.read_receipt(shot_id, key)
                except KeyboardInterrupt:
                    self.record_submission(row, None)
                    raise
                self.record_submission(row, reply)
            elif row["status"] in {"submitting", "unknown"} and row["task_id"] is None:
                self.record_submission(row, None)
                self.record_submission(row, self.read_receipt(shot_id, key))
            if row["status"] == "completed":
                self.restore_missing_outputs(row)
                print(f"{shot_id}: already completed", flush=True)
                continue
            if row["status"] == "rejected" or (row["status"] == "unknown" and row["task_id"] is None):
                raise BridgeError(f"{shot_id}: submission {row['status']}. Check the service receipt before any new submission.")
            if row["status"] in {"failed", "canceled"}:
                raise BridgeError(f"{shot_id}: cloud task ended in {row['status']}.")
            deadline = time.monotonic() + self.wait_seconds
            self.poll_cloud(shot_id, row, deadline)
            self.collect_outputs(shot_id, row, operation, deadline)
            print(f"{shot_id}: completed", flush=True)

    def read_receipt(self, shot_id, key):
        try:
            return self.service.json("/api/dv/wanxiang/receipt", {"key": key})
        except TransportError:
            raise BridgeError(f"{shot_id}: submission unknown. The service receipt could not be read; check it before any new submission.") from None

    def record_submission(self, row, reply):
        task_id = reply.get("task_id") if isinstance(reply, dict) else None
        if isinstance(task_id, str) and TASK_ID.fullmatch(task_id):
            row.update(status="submitted", task_id=task_id)
        else:
            status = "rejected" if isinstance(reply, dict) and reply.get("status") == "rejected" else "unknown"
            row["status"] = status
            if isinstance(reply, dict):
                http_status = reply.get("submit_http_status")
                if type(http_status) is int and 100 <= http_status <= 599:
                    row["submit_http_status"] = http_status
        self.save()

    def pause(self, shot_id, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BridgeError(f"{shot_id}: local wait ended. Run the same command to check the existing task.")
        time.sleep(min(remaining, self.poll_interval))

    def poll_cloud(self, shot_id, row, deadline):
        if row["cloud_status"] == "SUCCEEDED":
            return
        while True:
            reply = self.service.json(
                "/api/dv/wanxiang/status", {"key": row["confirmation_key"], "task_id": row["task_id"]},
            )
            if reply.get("task_id") != row["task_id"]:
                raise BridgeError(f"{shot_id}: Wan status returned a different task ID.")
            cloud = reply.get("status")
            if cloud not in {"PENDING", "RUNNING", "SUCCEEDED", "FAILED", "CANCELED", "UNKNOWN", "SUSPENDED"}:
                raise BridgeError(f"{shot_id}: Wan returned an unrecognized cloud status.")
            usage = reply.get("billed_video_seconds")
            if type(usage) not in (int, float) or not math.isfinite(usage) or usage < 0:
                usage = None
            status = {
                "SUCCEEDED": "materializing", "FAILED": "failed", "CANCELED": "canceled", "UNKNOWN": "unknown",
            }.get(cloud, "running")
            changes = {"status": status, "cloud_status": cloud, "billed_video_seconds": usage}
            if any(row[field] != value for field, value in changes.items()):
                row.update(changes)
                self.save()
            if cloud == "SUCCEEDED":
                return
            if cloud in {"FAILED", "CANCELED", "UNKNOWN"}:
                raise BridgeError(f"{shot_id}: cloud task returned {cloud}. Check the existing task.")
            self.pause(shot_id, deadline)

    def collect_outputs(self, shot_id, row, operation, deadline):
        history = {"project": operation["project"], "operation": "shot.render", "limit": 200}
        if row["dreamverse_record_id"]:
            history["records"] = [row["dreamverse_record_id"]]
        found = self.service.json("/api/dv/history", history)
        record = next((item["record"] for item in found["entries"] if item["record"]["intent"] == operation["intent"]), None)
        if record is None or record["status"] in {"failed", "cancelled"}:
            # This operation only materializes existing cloud output. Calling it
            # after an interrupted local render never submits to Wan.
            record = self.service.json("/api/dv/operation", operation)
        row["dreamverse_record_id"] = record["id"]
        self.save()
        while record["status"] in {"pending", "running"}:
            self.pause(shot_id, deadline)
            reply = self.service.json("/api/dv/history", {**history, "records": [record["id"]]})
            if not reply["entries"] or reply["entries"][0]["record"]["id"] != record["id"]:
                raise BridgeError(f"{shot_id}: DreamVerse render record could not be read.")
            record = reply["entries"][0]["record"]
        if record["status"] != "done" or len(record.get("outputs", [])) != 2:
            raise BridgeError(f"{shot_id}: DreamVerse could not materialize the confirmed task.")
        video_id, still_id = record["outputs"]
        video, still = (self.directory / f"{shot_id}{ext}" for ext in (".mp4", "-last.png"))
        self.service.download(video_id, video)
        self.service.download(still_id, still)
        row.update(
            status="completed", dreamverse_video_asset_id=video_id, dreamverse_last_frame_asset_id=still_id,
            mp4_path=str(video), last_frame_path=str(still),
        )
        self.save()

    def restore_missing_outputs(self, row):
        for path_key, asset_key in (
            ("mp4_path", "dreamverse_video_asset_id"), ("last_frame_path", "dreamverse_last_frame_asset_id"),
        ):
            path = Path(row[path_key])
            if not path.is_file():
                self.service.download(row[asset_key], path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:49183")
    parser.add_argument("--confirm", metavar="SHOT_ID", action="append", default=[])
    parser.add_argument("--wait-seconds", type=float, default=900)
    parser.add_argument("--poll-interval", type=float, default=5)
    args = parser.parse_args()
    try:
        if any(not math.isfinite(value) or value <= 0 for value in (args.wait_seconds, args.poll_interval)):
            raise BridgeError("Wait and poll intervals must be positive and finite.")
        shots = read_shots(args.manifest)
        service = DreamVerse(args.url)
        launch_url = os.environ.get("DREAMVERSE_LAUNCH_URL")
        if launch_url:
            service.authenticate(launch_url)
        directory = args.output.resolve()
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / ".bridge.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise BridgeError("Another bridge process is already using this output directory.") from None
            Bridge(service, directory, args.wait_seconds, args.poll_interval).run(shots, args.confirm)
    except KeyboardInterrupt:
        print("Local wait interrupted. Run the same command to check the existing task.", file=sys.stderr)
        return 130
    except BridgeError as error:
        print(error, file=sys.stderr)
        return 1
    except (OSError, HTTPException, ValueError, KeyError, TypeError, AttributeError, IndexError):
        print("Could not read a bridge input, a ledger entry, or a DreamVerse response.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
