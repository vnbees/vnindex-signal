"use client";

import { useEffect, useState } from "react";

export type Theme = "dark" | "light";

const STORAGE_KEY = "vii-theme";

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    /* ignore */
  }
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    const fromDom = document.documentElement.getAttribute("data-theme") as Theme | null;
    if (fromDom === "light" || fromDom === "dark") {
      setTheme(fromDom);
      return;
    }
    try {
      const stored = localStorage.getItem(STORAGE_KEY) as Theme | null;
      if (stored === "light" || stored === "dark") {
        setTheme(stored);
        applyTheme(stored);
      }
    } catch {
      /* ignore */
    }
  }, []);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    applyTheme(next);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      className="shrink-0 rounded-md border border-tv-border bg-tv-panel px-3 py-1.5 text-xs font-medium text-tv-text shadow-sm transition-colors hover:bg-tv-panel-hover"
      aria-label={theme === "dark" ? "Chuyển giao diện sáng" : "Chuyển giao diện tối"}
    >
      {theme === "dark" ? "Giao diện sáng" : "Giao diện tối"}
    </button>
  );
}
