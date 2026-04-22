async function parseJsonSafe(response) {
    try {
        return await response.json();
    } catch {
        return {};
    }
}

async function signInWithGoogleCredential(credential) {
    const response = await fetch("/api/auth/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ credential }),
    });
    const body = await parseJsonSafe(response);
    if (!response.ok) {
        throw new Error(body.error || "Google sign-in failed");
    }
    if (body.user) {
        sessionStorage.setItem("user", JSON.stringify(body.user));
    }
    return body;
}

async function getSession() {
    const response = await fetch("/api/auth/session", {
        method: "GET",
        credentials: "same-origin",
    });
    if (!response.ok) {
        return null;
    }
    const body = await parseJsonSafe(response);
    if (body.user) {
        sessionStorage.setItem("user", JSON.stringify(body.user));
    }
    return body;
}

async function requireAuth() {
    const session = await getSession();
    if (!session?.user) {
        sessionStorage.setItem("returnUrl", globalThis.location.href);
        globalThis.location.href = "login.html";
        return null;
    }
    return session;
}

async function logout() {
    await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "same-origin",
    });
    sessionStorage.removeItem("user");
    sessionStorage.removeItem("credential");
    globalThis.location.href = "login.html";
}

globalThis.signInWithGoogleCredential = signInWithGoogleCredential;
globalThis.getSession = getSession;
globalThis.requireAuth = requireAuth;
globalThis.logout = logout;

const THEME_STORAGE_KEY = "insite-theme";
const DEFAULT_THEME = "light";
const VALID_THEMES = new Set(["light", "dark", "meadow", "forest", "twilight"]);

function normalizeTheme(themeName) {
    if (!themeName) return DEFAULT_THEME;
    const normalized = String(themeName).trim().toLowerCase();
    // Migrate old "bright" theme name to the new "dark" label.
    if (normalized === "bright") return "dark";
    return VALID_THEMES.has(normalized) ? normalized : DEFAULT_THEME;
}

function applyTheme(themeName) {
    const theme = normalizeTheme(themeName);
    const root = globalThis.document?.documentElement;
    if (root) {
        root.dataset.theme = theme;
    }
    const body = globalThis.document?.body;
    if (body) {
        body.dataset.theme = theme;
    }
    return theme;
}

function setTheme(themeName) {
    const theme = applyTheme(themeName);
    globalThis.localStorage?.setItem(THEME_STORAGE_KEY, theme);
    return theme;
}

function getTheme() {
    return normalizeTheme(globalThis.localStorage?.getItem(THEME_STORAGE_KEY));
}

// Apply as early as possible to avoid flash of default theme.
applyTheme(getTheme());

globalThis.addEventListener("DOMContentLoaded", () => {
    applyTheme(getTheme());
});

globalThis.setTheme = setTheme;
globalThis.getTheme = getTheme;
globalThis.applyTheme = applyTheme;
