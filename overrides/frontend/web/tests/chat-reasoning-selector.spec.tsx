// SPDX-License-Identifier: Apache-2.0
// Modified by SaMappp from HKUDS/DeepTutor v1.7.1; see NOTICE and docs/CHANGE_INVENTORY.md.
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { initI18n } from "@/i18n/init";
import type { LLMOption } from "@/lib/llm-options";
import ModelSelector from "@/components/chat/home/ModelSelector";
import ReasoningEffortSelector from "@/components/chat/home/ReasoningEffortSelector";
import { saveChatReasoningEffort } from "@/lib/chat-reasoning";
import { apiFetch } from "@/lib/api";
import { setCodexReasoningEffort } from "@/lib/codex-oauth";

initI18n("en");
vi.mock("@/lib/api", () => ({ apiUrl: (path: string) => path, apiFetch: vi.fn() }));
vi.mock("@/lib/codex-oauth", () => ({ setCodexReasoningEffort: vi.fn() }));
vi.mock("@/shared/ui/Tooltip", () => ({ default: ({children}: {children: React.ReactNode}) => children }));

const custom: LLMOption = {
  profile_id: "deepworks", model_id: "flash", profile_name: "DeepWorks credits",
  model_name: "DeepSeek Flash", model: "DeepSeek-V4-Flash", provider: "custom",
  is_active_default: false, reasoning_effort: "low", supported_reasoning_efforts: ["low", "high", "max"],
};
beforeEach(() => {
  vi.mocked(apiFetch).mockResolvedValue(new Response("{}", {status: 200}));
  vi.mocked(setCodexReasoningEffort).mockResolvedValue({} as Awaited<ReturnType<typeof setCodexReasoningEffort>>);
});

describe("chat reasoning effort", () => {
  it("shows only the declared provider levels", () => {
    render(<ReasoningEffortSelector option={custom} />);
    fireEvent.click(screen.getByRole("button", {name: "Reasoning effort: Low"}));
    expect(screen.getByRole("option", {name: "Maximum"})).toBeTruthy();
    expect(screen.queryByRole("option", {name: "Medium"})).toBeNull();
  });
  it("saves the selected model without changing defaults or other models", async () => {
    const refresh = vi.fn();
    render(<ReasoningEffortSelector option={custom} onRefresh={refresh} />);
    fireEvent.click(screen.getByRole("button", {name: "Reasoning effort: Low"}));
    fireEvent.click(screen.getByRole("option", {name: "High"}));
    await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
    const args = vi.mocked(apiFetch).mock.calls[0];
    expect(args[0]).toBe("/api/settings/apply/registry");
    const body = JSON.parse(String(args[1]?.body));
    expect(body).toEqual({
      kind: "model", service: "llm", profile_id: "deepworks", model_id: "flash",
      model: {id: "flash", model: "DeepSeek-V4-Flash", reasoning_effort: "high"},
    });
    expect(body.active_model_id).toBeUndefined();
    expect(screen.getByRole("button", {name: "Reasoning effort: High"})).toBeTruthy();
  });
  it("keeps the current value and a retryable menu after a failed save", async () => {
    vi.mocked(apiFetch).mockResolvedValue(new Response("{}", {status: 500}));
    render(<ReasoningEffortSelector option={custom} />);
    fireEvent.click(screen.getByRole("button", {name: "Reasoning effort: Low"}));
    fireEvent.click(screen.getByRole("option", {name: "High"}));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Save failed");
    expect(screen.getByRole("button", {name: "Reasoning effort: Low"})).toBeTruthy();
  });
  it("prevents setting changes while the learning request is running", () => {
    render(<ReasoningEffortSelector option={custom} disabled />);
    fireEvent.click(screen.getByRole("button", {name: "Reasoning effort: Low"}));
    expect(screen.queryByRole("listbox")).toBeNull();
    expect(apiFetch).not.toHaveBeenCalled();
  });
  it("uses Codex's managed preference endpoint and supports provider Auto", async () => {
    const codex = {...custom, provider: "openai_codex", model: "gpt-6.1-sol"};
    await saveChatReasoningEffort(codex, "high");
    expect(setCodexReasoningEffort).toHaveBeenCalledWith("gpt-6.1-sol", "high");
    await saveChatReasoningEffort(codex, "");
    expect(setCodexReasoningEffort).toHaveBeenCalledWith("gpt-6.1-sol", null);
    expect(apiFetch).not.toHaveBeenCalled();
  });
  it("rejects undeclared levels before writing settings", async () => {
    await expect(saveChatReasoningEffort(custom, "ultra")).rejects.toThrow("Unsupported");
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("locks model selection and reports pending state until the save finishes", async () => {
    let finish!: (response: Response) => void;
    vi.mocked(apiFetch).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
    const pending = vi.fn();
    render(<ModelSelector options={[custom]} activeDefault={custom} value={null}
      loading={false} error={false} onChange={vi.fn()} showReasoning onReasoningSavingChange={pending} />);
    fireEvent.click(screen.getByRole("button", {name: "Reasoning effort: Low"}));
    fireEvent.click(screen.getByRole("option", {name: "High"}));
    expect(pending).toHaveBeenLastCalledWith(true);
    expect(screen.getByRole("button", {name: "Select model"})).toBeDisabled();
    await act(async () => finish(new Response("{}", {status: 200})));
    expect(pending).toHaveBeenLastCalledWith(false);
    expect(screen.getByRole("button", {name: "Select model"})).not.toBeDisabled();
  });
});
