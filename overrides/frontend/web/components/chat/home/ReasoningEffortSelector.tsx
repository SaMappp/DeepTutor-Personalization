// SPDX-License-Identifier: Apache-2.0
// Modified by SaMappp from HKUDS/DeepTutor v1.7.1; see NOTICE and docs/CHANGE_INVENTORY.md.
"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { Brain, Check, ChevronDown, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useOutsideClick } from "@/hooks/use-outside-click";
import Tooltip from "@/shared/ui/Tooltip";
import type { LLMOption } from "@/lib/llm-options";
import { invalidateLLMOptionsCache } from "@/lib/llm-options";
import { reasoningEffortOptions, reasoningEffortOptionsFromSupportedLevels } from "@/lib/reasoning-effort";
import { saveChatReasoningEffort } from "@/lib/chat-reasoning";

export default function ReasoningEffortSelector({ option, disabled = false, placement = "top", onRefresh, onSavingChange }: {
  option: LLMOption; disabled?: boolean; placement?: "top" | "bottom"; onRefresh?: () => void; onSavingChange?: (saving: boolean) => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [value, setValue] = useState(option.reasoning_effort ?? "");
  const [error, setError] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => { setValue(option.reasoning_effort ?? ""); }, [option.reasoning_effort]);
  const choices = useMemo(() => option.supported_reasoning_efforts?.length
    ? reasoningEffortOptionsFromSupportedLevels(option.supported_reasoning_efforts)
    : reasoningEffortOptions(option.provider, option.model, option.reasoning_effort, option.declared_reasoning),
    [option.provider, option.model, option.reasoning_effort, option.supported_reasoning_efforts, option.declared_reasoning]);
  useOutsideClick(root, open, () => { if (!saving) setOpen(false); });
  if (choices.length < 2) return null;
  const current = choices.find(choice => choice.value === value);
  const label = value ? t(current?.label ?? value) : t("Auto");
  const title = t("Reasoning effort") + ": " + label;
  async function save(next: string) {
    if (saving || disabled) return;
    if (next === value) { setOpen(false); return; }
    setSaving(true); setError(false); onSavingChange?.(true);
    try {
      await saveChatReasoningEffort(option, next);
      invalidateLLMOptionsCache();
      onRefresh?.();
      if (mounted.current) { setValue(next); setOpen(false); }
    } catch {
      if (mounted.current) setError(true);
    } finally {
      onSavingChange?.(false);
      if (mounted.current) setSaving(false);
    }
  }
  return (
    <div ref={root} className="relative shrink-0">
      <Tooltip label={title} suppressed={open} side="top">
        <button ref={trigger} type="button" aria-label={title} aria-haspopup="listbox" aria-expanded={open}
          disabled={disabled || saving} onClick={() => { setOpen(!open); setError(false); }}
          onKeyDown={event => {
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
              event.preventDefault(); setOpen(true);
              requestAnimationFrame(() => root.current?.querySelector<HTMLButtonElement>('[role="option"]')?.focus());
            }
          }}
          className="inline-flex h-8 items-center gap-1 rounded-lg px-2 text-[12px] font-medium text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)]/55 hover:text-[var(--foreground)] disabled:cursor-not-allowed disabled:opacity-40">
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Brain size={14} strokeWidth={1.7} />}
          <span>{label}</span><ChevronDown size={11} />
        </button>
      </Tooltip>
      {open && (
        <div className={"absolute right-0 z-50 " + (placement === "bottom" ? "top-full mt-1.5" : "bottom-full mb-1.5") +
          " w-48 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--popover)] py-1 shadow-lg"}
          role="listbox" aria-label={t("Reasoning effort")} aria-busy={saving}
          onKeyDown={event => {
            if (event.key === "Escape") {
              event.preventDefault(); event.stopPropagation();
              if (!saving) setOpen(false);
              trigger.current?.focus();
            }
            const buttons = Array.from(root.current?.querySelectorAll<HTMLButtonElement>('[role="option"]') ?? []);
            const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
            let next: number | undefined;
            if (event.key === "ArrowDown") next = (index + 1) % buttons.length;
            if (event.key === "ArrowUp") next = (index - 1 + buttons.length) % buttons.length;
            if (event.key === "Home") next = 0;
            if (event.key === "End") next = buttons.length - 1;
            if (next !== undefined) { event.preventDefault(); buttons[next]?.focus(); }
          }}>
          <div className="px-3 py-1.5 text-[11px] text-[var(--muted-foreground)]">{t("Reasoning effort")}</div>
          {choices.map(choice => (
            <button key={choice.value} type="button" role="option" aria-selected={value === choice.value}
              disabled={saving} onClick={() => void save(choice.value)}
              className="flex w-full items-center justify-between px-3 py-1.5 text-left text-[12.5px] text-[var(--foreground)] hover:bg-[var(--muted)]/55 disabled:opacity-50">
              <span>{t(choice.label)}</span>{value === choice.value && <Check size={13} />}
            </button>
          ))}
          {error && <p role="alert" className="px-3 py-2 text-xs text-red-500">{t("Save failed")}</p>}
        </div>
      )}
    </div>
  );
}
