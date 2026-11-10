// SPDX-License-Identifier: Apache-2.0
// Modified by SaMappp from HKUDS/DeepTutor v1.7.1; see NOTICE and docs/CHANGE_INVENTORY.md.
import { apiFetch, apiUrl } from "@/lib/api";
import type { LLMOption } from "@/lib/llm-options";
import { setCodexReasoningEffort } from "@/lib/codex-oauth";

/** Update only this model's effort; never change provider/model defaults. */
export async function saveChatReasoningEffort(option: LLMOption, effort: string): Promise<void> {
  const supported = option.supported_reasoning_efforts;
  if (effort && supported?.length && !supported.includes(effort)) throw new Error("Unsupported reasoning effort");
  if (option.provider === "openai_codex") {
    await setCodexReasoningEffort(option.model, effort || null);
    return;
  }
  const response = await apiFetch(apiUrl("/api/settings/apply/registry"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      kind: "model", service: "llm", profile_id: option.profile_id, model_id: option.model_id,
      model: { id: option.model_id, model: option.model, reasoning_effort: effort },
    }),
  });
  if (!response.ok) throw new Error("Could not save reasoning effort");
}
