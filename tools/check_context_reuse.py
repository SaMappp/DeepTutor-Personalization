# SPDX-License-Identifier: Apache-2.0
"""Offline regression tests using the installed DeepTutor dependencies."""
from __future__ import annotations
import ast
import asyncio
import faulthandler
from contextlib import ExitStack
import importlib.util
from pathlib import Path
import sys
import os
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
CORE = Path(os.environ["DEEPTUTOR_CORE"]).resolve()
if not (CORE / "deeptutor").is_dir():
    raise SystemExit("DEEPTUTOR_CORE must point to an installed v1.7.1 core with dependencies.")
sys.path.insert(0, str(CORE))
tempfile.tempdir = str(ROOT / "verification/tmp")
Path(tempfile.tempdir).mkdir(parents=True, exist_ok=True)


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / "overrides/desktop/deeptutor" / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


import deeptutor.capabilities.explore_context  # establish the official package
reuse = load("deeptutor.capabilities.explore_context.reuse", "capabilities/explore_context/reuse.py")
capmod = load("deeptutor.capabilities.explore_context.capability", "capabilities/explore_context/capability.py")
pipeline = load("deeptutor.agents.loop.pipeline_reuse", "agents/loop/pipeline.py")
from deeptutor.core.context import UnifiedContext, TurnRuntimeContext, WorkspaceRuntimeContext
from deeptutor.tools.builtin import ReadSourceTool


def context(mid="1", lineage=None, text="alpha; exact detail: sapphire-731"):
    return UnifiedContext(
        session_id="test-session", user_message="Explain alpha", language="zh",
        runtime=TurnRuntimeContext(workspace=WorkspaceRuntimeContext(workspace_id="test-workspace")),
        metadata={"source_index": {"at-doc": text}, "exploration_message_id": mid,
                  "exploration_lineage": list(lineage or []), "llm_model": "test-model",
                  "llm_provider": "test-provider", "llm_reasoning_effort": "high"},
    )


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = reuse.InvestigationCache(Path(self.tmp.name))

    def test_nearest_ancestor_and_sibling_isolation(self):
        self.cache.save("key", "1", "first", "first briefing")
        self.cache.save("key", "3", "sibling", "sibling briefing")
        self.assertEqual(self.cache.load("key", ["1", "2"]), ("first", "first briefing"))
        self.assertIsNone(self.cache.load("key", ["9"]))
        self.assertIsNone(self.cache.load("other", ["1"]))

    def test_source_and_identity_changes_invalidate(self):
        original = context()
        original_key = reuse.cache_key(original)
        for field, value in [("session", "other"), ("workspace", "other"), ("source", "changed"),
                             ("language", "en"), ("model", "other")]:
            changed = context()
            if field == "session": changed.session_id = value
            if field == "workspace": changed.runtime.workspace = WorkspaceRuntimeContext(workspace_id=value)
            if field == "source": changed.metadata["source_index"]["at-doc"] = value
            if field == "language": changed.language = value
            if field == "model": changed.metadata["llm_model"] = value
            self.assertNotEqual(reuse.cache_key(changed), original_key, field)

    def test_untrusted_or_missing_lineage_disables_cache(self):
        ctx = context()
        del ctx.metadata["exploration_lineage"]
        self.assertIsNone(reuse.cache_key(ctx))
        ctx = context()
        ctx.metadata["exploration_message_id"] = ""
        self.assertIsNone(reuse.cache_key(ctx))

    def test_bounded_and_no_empty_or_oversized_summary(self):
        self.assertFalse(self.cache.save("k", "0", "q", " "))
        self.assertFalse(self.cache.save("k", "0", "q", "x" * (reuse.MAX_BRIEFING_CHARS + 1)))
        with patch.object(reuse, "MAX_ENTRIES", 2):
            for i in range(3): self.cache.save("k", str(i), "q", "brief")
        self.assertIsNone(self.cache.load("k", ["0"]))
        self.assertIsNotNone(self.cache.load("k", ["2"]))

    def test_account_directories_are_isolated(self):
        self.cache.save("k", "1", "q", "private")
        other = Path(self.tmp.name) / "other"
        other.mkdir()
        self.assertIsNone(reuse.InvestigationCache(other).load("k", ["1"]))

    def test_corrupt_cache_fails_open(self):
        self.cache.path.write_bytes(b"not sqlite")
        self.assertIsNone(self.cache.load("k", ["1"]))
        self.assertFalse(self.cache.save("k", "1", "q", "brief"))


class CapabilityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = reuse.InvestigationCache(Path(self.tmp.name))
        self.cache_patch = patch.object(reuse, "InvestigationCache", return_value=self.cache)
        self.cache_patch.start()
        self.addCleanup(self.cache_patch.stop)
        header = capmod._load_prompts("zh")["briefing_header"].strip()
        self.explorer = SimpleNamespace(investigate=AsyncMock(return_value=header + "\n\nSource at-doc establishes alpha."))
        self.explorer_patch = patch("deeptutor.capabilities.explore_context.explorer.ContextExplorer", return_value=self.explorer)
        self.explorer_patch.start()
        self.addCleanup(self.explorer_patch.stop)
        self.cap = capmod.ExploreContextCapability()

    async def test_first_turn_then_followup_reuses_without_prepass(self):
        first = context()
        fresh = await self.cap.pre_loop(first, None)
        followup = context("3", ["1", "2"])
        followup.user_message = "Explain it more simply"
        reused = await self.cap.pre_loop(followup, None)
        self.assertEqual(self.explorer.investigate.await_count, 1)
        self.assertEqual(followup.extension("explore_context")["investigation_mode"], "reused")
        self.assertIn("历史调查", reused.content)
        self.assertIn("read_source", reused.content)
        self.assertNotIn("不要调用文件", reused.content)
        self.assertIn("Source at-doc", fresh.content)

    async def test_new_detail_readable_from_original_source(self):
        await self.cap.pre_loop(context(), None)
        followup = context("3", ["1", "2"])
        await self.cap.pre_loop(followup, None)
        kwargs = self.cap.augment_kwargs("read_source", {"source_id": "at-doc", "source_index": {"evil": "fake"}}, followup)
        result = await ReadSourceTool().execute(**kwargs)
        self.assertTrue(result.success)
        self.assertIn("sapphire-731", result.content)
        bad = await ReadSourceTool().execute(**{**kwargs, "source_id": "at-not-present"})
        self.assertFalse(bad.success)

    async def test_changed_or_added_source_requires_fresh_investigation(self):
        await self.cap.pre_loop(context(), None)
        changed = context("3", ["1", "2"], "changed source")
        await self.cap.pre_loop(changed, None)
        added = context("5", ["1", "2", "3", "4"])
        added.metadata["source_index"]["at-new"] = "new source"
        await self.cap.pre_loop(added, None)
        self.assertEqual(self.explorer.investigate.await_count, 3)

    async def test_branch_and_explicit_refresh_require_fresh(self):
        await self.cap.pre_loop(context(), None)
        sibling = context("4", ["9"])
        await self.cap.pre_loop(sibling, None)
        forced = context("5", ["1", "2"])
        forced.config_overrides["explore_context_force"] = True
        await self.cap.pre_loop(forced, None)
        self.assertEqual(self.explorer.investigate.await_count, 3)

    async def test_empty_failure_is_not_cached(self):
        self.explorer.investigate.return_value = ""
        self.assertIsNone(await self.cap.pre_loop(context(), None))
        self.explorer.investigate.return_value = "valid"
        await self.cap.pre_loop(context("3", ["1", "2"]), None)
        self.assertEqual(self.explorer.investigate.await_count, 2)

    async def test_mastery_and_no_sources_preserve_previous_behavior(self):
        ctx = context()
        ctx.metadata["source_index"] = {}
        self.assertIsNone(await self.cap.pre_loop(ctx, None))
        ctx = context()
        ctx.metadata["mastery_mode"] = True
        await self.cap.pre_loop(ctx, None)
        await self.cap.pre_loop(ctx, None)
        self.assertEqual(self.explorer.investigate.await_count, 2)
        self.assertIsNone(self.cap.system_block(ctx, language="zh", prompts={}))
        self.assertEqual(self.cap.augment_kwargs("read_source", {"source_index": {"mastery": "original"}}, ctx),
                         {"source_index": {"mastery": "original"}})


class PipelineTests(unittest.TestCase):
    def compose(self, ctx):
        obj = pipeline.AgenticLoopPipeline.__new__(pipeline.AgenticLoopPipeline)
        obj.registry = SimpleNamespace(get_enabled=lambda _: [], get=lambda _: None)
        obj._tool_view = None
        with ExitStack() as stack:
            for method, value in {"_is_partner_turn": False, "_coexisting_rag_kbs": [],
                                  "_capability_owned_tools": (), "_exclusive_capability_active": False,
                                  "_mastery_nav_available": False}.items():
                stack.enter_context(patch.object(obj, method, return_value=value))
            for name in ("user_has_memory", "user_has_notebooks", "user_has_question_bank",
                         "partner_can_record_questions"):
                stack.enter_context(patch.object(pipeline, name, return_value=False))
            stack.enter_context(patch("deeptutor.modules.catalog.module_enabled", return_value=False))
            stack.enter_context(patch.object(pipeline, "drop_unconfigured_generation_tools", side_effect=lambda x: x))
            return obj._compose_enabled_tools(ctx)

    def test_chat_can_read_sources_and_builtin_restrictions_still_apply(self):
        ctx = context()
        self.assertIn("read_source", self.compose(ctx))
        ctx.allowed_builtin_tools = []
        self.assertNotIn("read_source", self.compose(ctx))
        ctx.allowed_builtin_tools = None
        ctx.metadata["source_index"] = {}
        self.assertNotIn("read_source", self.compose(ctx))
        ctx = context()
        ctx.metadata["mastery_mode"] = True
        self.assertNotIn("read_source", self.compose(ctx))

    def test_all_patch_sources_parse(self):
        for path in (ROOT / "overrides/desktop").rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


if __name__ == "__main__":
    faulthandler.dump_traceback_later(20, repeat=False)
    unittest.main(verbosity=2)
