# SPDX-License-Identifier: Apache-2.0
# Historical adapter; modified for publication: explicit environment credential, no client credential-file access.
"""Import the current Harness DeepSeek account route; never changes defaults."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse
import yaml
from provider_common import TARGETS, backup, request


PROFILE_ID = "llm-profile-deepseek-harness-account"
BASE = "https://api.deepseek.com"
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def account():
    token = os.environ.get("DEEPTUTOR_DEEPSEEK_ACCOUNT_TOKEN")
    if not token:
        raise RuntimeError("Supply an explicitly authorized DeepSeek account token in the process environment.")
    return token

def source_models(token):
    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(BASE + "/models", headers={
        "x-dsh-auth-token": token, "User-Agent": "DeepTutor/1.7.1",
    })
    with opener.open(req, timeout=30) as response:
        catalog = json.load(response)["data"]
    entries = []
    for raw in catalog:
        name = raw["id"]
        if name not in {"deepseek-flash", "deepseek-v4-pro"}:
            continue
        entries.append({
            "id": "llm-model-deepseek-account-" + hashlib.sha256(name.encode()).hexdigest()[:16],
            "name": raw.get("name") or name, "model": name,
            "context_window": str(raw.get("context_window") or 1048576),
            "context_window_source": "metadata", "max_tokens": 8192,
            "reasoning_effort": "high", "supported_reasoning_efforts": ["low", "high", "max"],
            "capabilities": {"tools": True, "json_output": True, "reasoning": True,
                             "vision": name == "deepseek-flash"},
        })
    if not entries:
        raise RuntimeError("This account has no supported DeepSeek models; no settings were changed.")
    return entries

def check_default(before, after):
    b, a = before["services"]["llm"], after["services"]["llm"]
    if (b["active_profile_id"], b["active_model_id"]) != (a["active_profile_id"], a["active_model_id"]):
        raise RuntimeError("Default model changed unexpectedly. Review the saved backup.")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    token = account()
    models = source_models(token)
    targets = []
    for label, api, settings in TARGETS:
        runtime = request(api + "/api/system/runtime")
        if runtime.get("owner_turn_count", 0):
            raise RuntimeError(label + " has a learning request in progress; retry when it is complete.")
        catalog = request(api + "/api/settings/catalog")["catalog"]
        targets.append((label, api, settings, catalog))
    print(json.dumps({"source": "DeepSeek Harness account balance", "models": [m["model"] for m in models],
                      "read_only": args.check, "creates_api_key": False}))
    if args.check:
        return
    dth = {}  # Public export does not read another client's private configuration.
    for label, api, settings, before in targets:
        backup_path = backup(settings)
        previous = next((p for p in before["services"]["llm"]["profiles"] if p["id"] == PROFILE_ID), {})
        profile = copy.deepcopy(previous)
        old_models = {m["id"]: m for m in previous.get("models", [])}
        profile.update({
            "id": PROFILE_ID, "name": "DeepSeek 账号余额（Harness）",
            "binding": "custom", "base_url": BASE,
            # SDK constructor placeholder, not a new API key. Auth is the existing account grant.
            "api_key": "dsh-account", "api_format": "openai_chat", "wire_api": "chat_completions",
            "extra_headers": {"x-dsh-auth-token": token, "User-Agent": "DeepTutor/1.7.1"},
            "models": [],
        })
        for model in models:
            entry = copy.deepcopy(old_models.get(model["id"], model))
            for field in ("name", "model", "context_window", "context_window_source", "supported_reasoning_efforts", "capabilities"):
                entry[field] = model[field]
            profile["models"].append(entry)
        saved = request(api + "/api/settings/apply/provider",
                        {"service": "llm", "profile": profile, "activate": False})["catalog"]
        check_default(before, saved)
        # The chat effort control uses authoritative levels, rather than generic gateway guesses.
        dth_profile = next((p for p in saved["services"]["llm"]["profiles"] if p["id"] == "llm-profile-deepworks-dth"), None)
        if dth_profile:
            dth_profile = copy.deepcopy(dth_profile)
            changed = False
            for model in dth_profile["models"]:
                levels = dth.get(model["model"], {}).get("options", {}).get("__deepworksDthAttributes", {}).get("reasoningEfforts")
                if levels and model.get("supported_reasoning_efforts") != levels:
                    model["supported_reasoning_efforts"] = levels
                    changed = True
            if changed:
                saved = request(api + "/api/settings/apply/provider",
                                {"service": "llm", "profile": dth_profile, "activate": False})["catalog"]
                check_default(before, saved)
        bucket = saved["services"]["llm"]
        default_profile = next(p for p in bucket["profiles"] if p["id"] == bucket["active_profile_id"])
        default_model = next(m for m in default_profile["models"] if m["id"] == bucket["active_model_id"])
        print(json.dumps({"target": label, "imported": len(models), "default": default_model["model"],
                          "default_unchanged": True, "backup": backup_path}, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print("Official account/service request failed: HTTP " + str(exc.code) +
              ". Sign in inside Harness and retry. No token was printed.", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(str(exc) if isinstance(exc, RuntimeError) else "Sync failed (" + type(exc).__name__ + "); credentials were not printed.", file=sys.stderr)
        sys.exit(1)
