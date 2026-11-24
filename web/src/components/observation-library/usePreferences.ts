import { useCallback, useEffect, useState } from "react";
import { READABLE_IDS } from "./catalog";
import { normalizePins, PINS_CHANGE_EVENT, PINS_STORAGE_KEY, readPins, writePins } from "./preferences";

type PinState = { ids: string[]; warning: string | null };

function browserStorage(): Storage | undefined {
  if (typeof window === "undefined") return undefined;
  try { return window.localStorage; } catch { return undefined; }
}

function initialState(): PinState { return readPins(browserStorage()); }

export function useObservationPreferences() {
  const [state, setState] = useState<PinState>(initialState);

  useEffect(() => {
    const sameTab = (event: Event) => {
      const detail = (event as CustomEvent<PinState>).detail;
      if (detail) setState({ ids: normalizePins(detail.ids), warning: detail.warning });
    };
    const otherTab = (event: StorageEvent) => {
      if (event.key === PINS_STORAGE_KEY || event.key === null) setState(readPins(browserStorage()));
    };
    window.addEventListener(PINS_CHANGE_EVENT, sameTab);
    window.addEventListener("storage", otherTab);
    return () => {
      window.removeEventListener(PINS_CHANGE_EVENT, sameTab);
      window.removeEventListener("storage", otherTab);
    };
  }, []);

  const setPinned = useCallback((id: string, pinned: boolean) => {
    if (!READABLE_IDS.has(id)) return;
    const ids = normalizePins(pinned ? [...state.ids, id] : state.ids.filter((part) => part !== id));
    const saved = writePins(browserStorage(), ids);
    const next = { ids, warning: saved ? null : "浏览器存储不可用；本次选择只在当前页面有效。" };
    setState(next);
    // Custom events synchronize mounted views in this tab; storage synchronizes other tabs.
    window.dispatchEvent(new CustomEvent(PINS_CHANGE_EVENT, { detail: next }));
  }, [state.ids]);

  return { pinnedIds: state.ids, warning: state.warning, setPinned };
}
