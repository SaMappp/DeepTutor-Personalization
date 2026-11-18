// SPDX-License-Identifier: Apache-2.0
// Modified by SaMappp for reading material order; see NOTICE.
"use client";

import { ArrowDown, ArrowUp, FileText } from "lucide-react";
import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { reorderReadingMaterials, type ReadingWorkspace } from "@/lib/reading-workspace-api";

const MOVE_BUTTON =
  "grid size-8 shrink-0 place-items-center rounded-md hover:bg-[var(--muted)] focus-visible:outline-2 focus-visible:outline-[var(--ring)] disabled:opacity-30";

export function ReadingMaterialOrderDialog({
  workspace, onClose, onSaved,
}: {
  workspace: ReadingWorkspace;
  onClose: () => void;
  onSaved: (workspace: ReadingWorkspace) => void;
}) {
  const { t } = useTranslation();
  const heading = useId();
  const modal = useRef<HTMLDialogElement>(null);
  const savingRef = useRef(false);
  const [tabs, setTabs] = useState(workspace.tabs);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);
  const changed = tabs.some((tab, index) =>
    tab.material.material_id !== workspace.tabs[index]?.material.material_id,
  );

  useEffect(() => {
    const dialog = modal.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);

  function move(index: number, step: number) {
    setTabs((current) => {
      const target = index + step;
      if (target < 0 || target >= current.length) return current;
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
    setError(false);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!changed || savingRef.current) return;
    savingRef.current = true;
    setSaving(true);
    setError(false);
    try {
      const updated = await reorderReadingMaterials(
        workspace.workspace_id,
        tabs.map((tab) => tab.material.material_id),
        workspace.content_workspace_id,
      );
      onSaved(updated);
      onClose();
    } catch {
      setError(true);
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  }

  return (
    <dialog
      ref={modal}
      aria-labelledby={heading}
      onCancel={(event) => {
        event.preventDefault();
        if (!savingRef.current) onClose();
      }}
      className="m-auto w-[min(32rem,calc(100%-2rem))] rounded-xl border border-[var(--border)] bg-[var(--popover)] p-0 text-[var(--foreground)] shadow-lg backdrop:bg-[var(--overlay)]"
    >
      <form onSubmit={save} className="flex max-h-[min(37rem,85dvh)] flex-col p-4 sm:p-5">
        <h2 id={heading} className="mb-3 font-serif text-[17px] font-semibold">{t("Reorder materials")}</h2>
        <ol className="min-h-0 divide-y divide-[var(--border)] overflow-y-auto">
          {tabs.map(({ material }, index) => {
            const title = material.title || material.filename;
            return (
              <li key={material.material_id} className="flex min-w-0 items-center gap-2 py-1">
                <span className="w-6 shrink-0 text-right text-xs tabular-nums text-[var(--muted-foreground)]">{index + 1}</span>
                <FileText size={15} aria-hidden className="shrink-0 text-[var(--muted-foreground)]" />
                <span title={title} className="min-w-0 flex-1 truncate text-[13px]">{title}</span>
                <button type="button" className={MOVE_BUTTON} disabled={saving || index === 0}
                  aria-label={t("Move {{title}} up", { title })} onClick={() => move(index, -1)}>
                  <ArrowUp size={16} aria-hidden />
                </button>
                <button type="button" className={MOVE_BUTTON} disabled={saving || index === tabs.length - 1}
                  aria-label={t("Move {{title}} down", { title })} onClick={() => move(index, 1)}>
                  <ArrowDown size={16} aria-hidden />
                </button>
              </li>
            );
          })}
        </ol>
        {error && <p role="alert" className="mt-3 text-xs text-[var(--destructive)]">{t("Could not save the order. Retry, or reload the collection if its materials changed.")}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" onClick={onClose} disabled={saving}
            className="h-8 rounded-lg px-3 text-xs hover:bg-[var(--muted)] disabled:opacity-50">
            {t("Cancel")}
          </button>
          <button type="submit" disabled={!changed || saving}
            className="h-8 rounded-lg bg-[var(--primary)] px-4 text-xs font-semibold text-[var(--primary-foreground)] disabled:opacity-50">
            {t(saving ? "Saving..." : "Save")}
          </button>
        </div>
      </form>
    </dialog>
  );
}
