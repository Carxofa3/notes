/**
 * Theme Engine State Management
 */

const STORAGE_KEY = 'university_notes_theme';

export function createThemeState() {
  let currentTheme = 'catppuccin-mocha';

  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      currentTheme = saved;
    }
    applyTheme(currentTheme);
  }

  function applyTheme(themeId) {
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', themeId);
      localStorage.setItem(STORAGE_KEY, themeId);
    }
  }

  return {
    get current() {
      return currentTheme;
    },
    set(themeId) {
      currentTheme = themeId;
      applyTheme(themeId);
    }
  };
}

export const theme = createThemeState();
