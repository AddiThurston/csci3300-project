const THEME_STORAGE_KEY = "insiteful-theme";
const DEFAULT_THEME = "midnight";
const AVAILABLE_THEMES = ["midnight", "bright", "meadow", "forest"];

function getPreferredTheme() {
    const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
    if (savedTheme && AVAILABLE_THEMES.includes(savedTheme)) {
        return savedTheme;
    }
    return DEFAULT_THEME;
}

function applyTheme(themeName) {
    const normalizedTheme = AVAILABLE_THEMES.includes(themeName) ? themeName : DEFAULT_THEME;
    document.documentElement.dataset.theme = normalizedTheme;
    localStorage.setItem(THEME_STORAGE_KEY, normalizedTheme);
    return normalizedTheme;
}

function initTheme() {
    applyTheme(getPreferredTheme());
}

function addSettingsGear() {
    const path = globalThis.location?.pathname || "";
    if (path.endsWith("/login.html") || path === "/login.html") {
        return;
    }

    const topBar = document.querySelector("header.top-bar");
    if (!topBar || topBar.querySelector(".settings-gear-link")) {
        return;
    }

    const settingsLink = document.createElement("a");
    settingsLink.href = "settings.html";
    settingsLink.className = "settings-gear-link";
    settingsLink.ariaLabel = "Open settings";
    settingsLink.title = "Settings";
    settingsLink.innerHTML = '<span class="settings-gear-icon" aria-hidden="true">&#9881;</span>';
    topBar.appendChild(settingsLink);
}

initTheme();

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
globalThis.applyTheme = applyTheme;
globalThis.getPreferredTheme = getPreferredTheme;
globalThis.availableThemes = [...AVAILABLE_THEMES];

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", addSettingsGear);
} else {
    addSettingsGear();
}
