# SPDX-License-Identifier: Apache-2.0
# Sanitized historical tool; configure runtime/workspace environment before use.
"""Guarded deployment into the pinned desktop core; never changes user data."""
from pathlib import Path
import ast
import datetime
import difflib
import hashlib
import json
import shutil
import sys
import os
import httpx

ROOT = Path(__file__).resolve().parent
CORE = Path(os.environ["DEEPTUTOR_CORE"]).resolve()
BASE = "http://127.0.0.1:18801"
WID = os.environ["DEEPTUTOR_WORKSPACE_ID"]
PLAN = ROOT / "deployment.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def snapshot():
    with httpx.Client(base_url=BASE, trust_env=False, timeout=10) as client:
        def get(path, **params):
            r = client.get(path, params=params)
            r.raise_for_status()
            return r.json()
        runtime = get("/api/system/runtime")
        if runtime["owner_turn_count"] != 0:
            raise RuntimeError("Desktop has an active turn; wait before deploying/restarting.")
        llm = get("/api/settings/catalog")["catalog"]["services"]["llm"]
        profile = next(p for p in llm["profiles"] if p["id"] == llm["active_profile_id"])
        model = next(m for m in profile["models"] if m["id"] == llm["active_model_id"])
        rows = get("/api/sessions", dt_workspace=WID, limit=200)["sessions"]
        sessions = {}
        for row in rows:
            session = get("/api/sessions/" + row["id"], dt_workspace=WID)
            # No transcript or attachment bytes are saved, only a preservation hash.
            preserved = [
                {k: msg.get(k) for k in ("id", "role", "content", "attachments", "parent_message_id")}
                for msg in session["messages"]
            ]
            encoded = json.dumps(preserved, sort_keys=True, ensure_ascii=False).encode("utf-8")
            sessions[row["id"]] = {"count": len(preserved), "sha256": hashlib.sha256(encoded).hexdigest()}
        return {"worker_id": runtime["worker_id"], "model": {"profile_id": profile["id"],
                "model": model["model"], "reasoning_effort": model.get("reasoning_effort")},
                "sessions": sessions}


def main(action):
    if action == "prepare":
        active = json.loads((Path.home() / "AppData/Local/Open DeepTutor/active.json").read_text(encoding="utf-8"))
        assert active["runtimeId"] == CORE.parent.name
        before = snapshot()
        rows, diffs = [], []
        for source in sorted((ROOT.parents[2] / "overrides/desktop").rglob("*.py")):
            rel = source.relative_to(ROOT.parents[2] / "overrides/desktop")
            ast.parse(source.read_text(encoding="utf-8"))
            target = CORE / rel
            rows.append({"file": rel.as_posix(), "before": digest(target), "after": digest(source)})
            diffs.extend(difflib.unified_diff(target.read_text(encoding="utf-8").splitlines(True) if target.exists() else [],
                source.read_text(encoding="utf-8").splitlines(True), fromfile="a/" + rel.as_posix(), tofile="b/" + rel.as_posix()))
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        write(PLAN, {"status": "prepared", "backup": str(ROOT / "backups" / stamp), "files": rows, "before": before})
        (ROOT / "change.patch").write_text("".join(diffs), encoding="utf-8")
        print(json.dumps({"status": "prepared", "files": len(rows), "sessions": len(before["sessions"]), "model": before["model"]}))
    elif action == "install":
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        assert plan["status"] == "prepared"
        assert snapshot() == plan["before"], "Runtime, model or messages changed since preparation"
        for row in plan["files"]:
            assert digest(CORE / row["file"]) == row["before"], "Deployed source changed"
            assert digest(ROOT.parents[2] / "overrides/desktop" / row["file"]) == row["after"], "Patch changed; prepare again"
        for row in plan["files"]:
            target = CORE / row["file"]
            if target.exists():
                backup = Path(plan["backup"]) / row["file"]
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
            shutil.copy2(ROOT.parents[2] / "overrides/desktop" / row["file"], target)
            assert digest(target) == row["after"]
        plan["status"] = "installed_pending_restart"
        write(PLAN, plan)
        print("Installed four reviewed files; original code backed up. Restart required.")
    elif action == "verify":
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        after = snapshot()
        assert after["worker_id"] != plan["before"]["worker_id"], "Core has not restarted"
        assert after["model"] == plan["before"]["model"], "Model changed"
        for sid, record in plan["before"]["sessions"].items():
            assert after["sessions"].get(sid) == record, "Original messages or attachments changed"
        for row in plan["files"]:
            assert digest(CORE / row["file"]) == row["after"]
        plan.update(status="verified", after=after)
        write(PLAN, plan)
        print("Restart verified; model and original messages/attachments preserved; all deployed hashes match.")
    elif action == "rollback":
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        snapshot()  # idle required
        for row in plan["files"]:
            target = CORE / row["file"]
            assert digest(target) in (row["before"], row["after"]), "Unknown local changes; refusing rollback"
        for row in plan["files"]:
            target = CORE / row["file"]
            if row["before"] is None:
                target.unlink(missing_ok=True)
            else:
                backup = Path(plan["backup"]) / row["file"]
                assert digest(backup) == row["before"]
                shutil.copy2(backup, target)
        plan["status"] = "rolled_back_pending_restart"
        write(PLAN, plan)
        print("Original code restored; restart the desktop core to finish rollback.")
    else:
        raise ValueError(action)


if __name__ == "__main__":
    main(sys.argv[1])
