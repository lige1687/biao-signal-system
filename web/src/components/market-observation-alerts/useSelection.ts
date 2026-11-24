import { useCallback, useEffect, useRef, useState } from "react";
import { CANDIDATE_IDS, COLLAPSED_KEY, CORE_IDS, LEGACY_PINS_KEY, migrateSelection, normalizeSelection,
  OVERVIEW_CHANGE_EVENT, OVERVIEW_KEY, PREVIOUS_OVERVIEW_KEY } from "./selection";

function readSelection() {
  try { return { ids: migrateSelection(localStorage.getItem(OVERVIEW_KEY), localStorage.getItem(PREVIOUS_OVERVIEW_KEY),
    localStorage.getItem(LEGACY_PINS_KEY), localStorage.getItem(COLLAPSED_KEY)), failed: false }; }
  catch { return { ids: [...CORE_IDS] as string[], failed: true }; }
}
const WARNING = "浏览器未保存选择，本次调整仅在当前页面有效。";

export function useOverviewSelection() {
  const [initial] = useState(readSelection);
  const [selectedIds, setSelectedIds] = useState(initial.ids);
  const current = useRef(selectedIds);
  const [warning, setWarning] = useState(initial.failed ? WARNING : "");

  useEffect(() => {
    // Preserve all previous keys so a migration can be inspected or recovered.
    const restored = readSelection();
    current.current = restored.ids; setSelectedIds(restored.ids);
    try { localStorage.setItem(OVERVIEW_KEY, JSON.stringify(restored.ids)); }
    catch { setWarning(WARNING); }
    const sync = () => {
      const result = readSelection(); current.current = result.ids; setSelectedIds(result.ids);
      setWarning(result.failed ? WARNING : "");
    };
    const storage = (event: StorageEvent) => { if (event.key === OVERVIEW_KEY || event.key === null) sync(); };
    window.addEventListener("storage", storage);
    window.addEventListener(OVERVIEW_CHANGE_EVENT, sync);
    return () => { window.removeEventListener("storage", storage); window.removeEventListener(OVERVIEW_CHANGE_EVENT, sync); };
  }, []);

  const save = useCallback((ids: readonly string[]) => {
    const next = normalizeSelection(ids);
    current.current = next; setSelectedIds(next);
    try { localStorage.setItem(OVERVIEW_KEY, JSON.stringify(next)); setWarning(""); window.dispatchEvent(new Event(OVERVIEW_CHANGE_EVENT)); }
    catch { setWarning(WARNING); }
  }, []);
  const setPinned = useCallback((id: string, pinned: boolean) => {
    if (!CANDIDATE_IDS.has(id)) return;
    save(pinned ? [...current.current, id] : current.current.filter(entry => entry !== id));
  }, [save]);
  const toggle = useCallback((id: string) => setPinned(id, !current.current.includes(id)), [setPinned]);
  const resetCore = useCallback(() => save(CORE_IDS), [save]);
  return { selectedIds, collapsedIds: [] as string[], warning, setPinned, resetCore, toggle,
    collapse: (id: string) => setPinned(id, false), restore: (id: string) => setPinned(id, true) };
}
