# SPDX-License-Identifier: Apache-2.0
# Sanitized historical tool; configure runtime/workspace environment before use.
"""Two real turns with synthetic text in a disposable desktop session."""
from pathlib import Path
import base64
import json
import os
import time
import uuid
import httpx
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:18801"
WID = os.environ["DEEPTUTOR_WORKSPACE_ID"]
SID = None  # The server allocates new sessions; caller-supplied ids must exist.
OUT = ROOT / "verification/live-check.json"


def main():
    global SID
    client = httpx.Client(base_url=BASE, trust_env=False, timeout=15)
    record = {"session_id": SID, "turns": [], "status": "running", "synthetic_only": True}
    if OUT.exists():
        previous = json.loads(OUT.read_text(encoding="utf-8"))
        if previous.get("status") == "rejected" and len(previous.get("turns", [])) == 1:
            record = previous
            record["status"] = "running"
            record.pop("rejection", None)
            SID = record["session_id"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2), encoding="utf-8")
    def session():
        r = client.get("/api/sessions/" + SID, params={"dt_workspace": WID})
        r.raise_for_status()
        return r.json()
    def turn(question, parent, attachments=None):
        global SID
        if SID:
            # DONE can arrive just before the coordinator releases the lease.
            deadline_idle = time.monotonic() + 30
            while time.monotonic() < deadline_idle:
                rows = client.get("/api/sessions", params={"dt_workspace": WID, "limit": 200}).json()["sessions"]
                row = next(r for r in rows if r["id"] == SID)
                if not row.get("active_turn_id"):
                    break
                time.sleep(0.25)
            else:
                raise RuntimeError("Test conversation still active; wait rather than interrupt")
        payload = {"protocol_version": "2.0", "type": "start_turn", "session_id": SID,
                   "parent_message_id": parent, "workspace_id": WID, "workspace_mode": "chat",
                   "capability": "chat", "content": question, "language": "zh", "tools": [],
                   "knowledge_bases": [], "skills": [], "mcp": [], "memory_references": [],
                   "client_submission_id": str(uuid.uuid4())}
        if attachments: payload["attachments"] = attachments
        started = time.monotonic()
        stages, calls, statuses = [], [], []
        with connect(f"ws://127.0.0.1:18801/ws?dt_workspace={WID}", open_timeout=10) as ws:
            ws.send(json.dumps(payload, ensure_ascii=False))
            deadline = time.monotonic() + 240
            while time.monotonic() < deadline:
                try:
                    event = json.loads(ws.recv(timeout=10))
                except TimeoutError:
                    continue
                kind = event.get("type")
                if SID is None and event.get("session_id"):
                    SID = event["session_id"]
                    record["session_id"] = SID
                if kind == "stage_start":
                    stages.append(event.get("stage"))
                    print("Stage: " + str(event.get("stage")), flush=True)
                if kind == "tool_call":
                    calls.append({"content": event.get("content"), "metadata": event.get("metadata")})
                if kind in {"error", "protocol_error"}:
                    record["rejection"] = {k: event.get(k) for k in ("type", "error_code", "content", "message")}
                    record["status"] = "rejected"
                    OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
                    raise RuntimeError(str(record["rejection"]))
                if kind == "done":
                    statuses.append(event.get("metadata", {}).get("status"))
                    break
            else:
                raise RuntimeError("Turn did not complete within its live-check budget")
        s = session()
        assistant = next(m for m in reversed(s["messages"]) if m["role"] == "assistant")
        result = {"duration_seconds": round(time.monotonic() - started, 3), "stages": stages,
                  "tool_calls": calls, "answer": assistant["content"], "assistant_id": assistant["id"],
                  "statuses": statuses}
        record["turns"].append(result)
        OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in result.items() if k != "tool_calls"}, ensure_ascii=False), flush=True)
        return result
    text = "Synthetic test document.\nALPHA = blue-247\nBETA = sapphire-731\nNo personal information.\n"
    a = record["turns"][0] if record["turns"] else turn("临时功能验证。只回复附件中 ALPHA 的值，不要解释，不要摘录 BETA。", None,
             [{"id": "context-reuse-smoke-doc", "type": "file", "filename": "context-reuse-smoke.txt",
               "mime_type": "text/plain", "base64": base64.b64encode(text.encode()).decode()}])
    assert "context_exploration" in a["stages"], "First investigation did not run"
    assert "blue-247" in a["answer"]
    b = turn("请调用 read_source 重新读取刚才的附件原文，再只回复 BETA 的值。", a["assistant_id"])
    assert "context_exploration" not in b["stages"], "Unchanged-source follow-up ran full prepass again"
    assert "sapphire-731" in b["answer"], "Original detail was not recoverable"
    assert any("read_source" in json.dumps(call) for call in b["tool_calls"]), "No on-demand source tool call"
    record["status"] = "passed"
    OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    # Remove only the test session this script created. Original chats are never touched.
    r = client.delete("/api/sessions/" + SID, params={"dt_workspace": WID})
    r.raise_for_status()
    record["temporary_session_removed"] = True
    OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Live source-reuse check passed; temporary synthetic conversation removed.", flush=True)


if __name__ == "__main__":
    main()
