/**
 * Runs before styles.css so :root[data-theme] tokens apply to the whole document on first paint.
 * Keep in sync with app.js: THEME_STORAGE_KEY, DEFAULT_THEME, VALID_THEMES, bright→dark migration.
 */
(function () {
    const THEME_STORAGE_KEY = "insite-theme";
    const DEFAULT_THEME = "light";
    const VALID_THEMES = new Set(["light", "dark", "meadow", "forest", "twilight"]);

    function normalizeTheme(name) {
        if (!name) return DEFAULT_THEME;
        let t = String(name).trim().toLowerCase();
        if (t === "bright") t = "dark";
        return VALID_THEMES.has(t) ? t : DEFAULT_THEME;
    }

    try {
        const raw = globalThis.localStorage?.getItem(THEME_STORAGE_KEY);
        const theme = normalizeTheme(raw);
        const el = globalThis.document?.documentElement;
        if (el) {
            el.dataset.theme = theme;
        }
    } catch {
        const el = globalThis.document?.documentElement;
        if (el) {
            el.dataset.theme = DEFAULT_THEME;
        }
    }
})();
