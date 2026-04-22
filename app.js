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
