// Client-side encryption for InSiteful Mind
// Key is derived from the user's Google account ID (sub) using PBKDF2.
// All encryption/decryption happens in the browser — the server only ever stores ciphertext.

const APP_SALT = new TextEncoder().encode('insiteful-mind-v1');

export async function getEncryptionKey() {
    try {
        const userStr = sessionStorage.getItem('user');
        const user = userStr ? JSON.parse(userStr) : null;
        const secret = user?.sub || localStorage.getItem('username');
        if (!secret) return null;

        const keyMaterial = await crypto.subtle.importKey(
            'raw',
            new TextEncoder().encode(secret),
            { name: 'PBKDF2' },
            false,
            ['deriveKey']
        );

        return await crypto.subtle.deriveKey(
            { name: 'PBKDF2', salt: APP_SALT, iterations: 100000, hash: 'SHA-256' },
            keyMaterial,
            { name: 'AES-GCM', length: 256 },
            false,
            ['encrypt', 'decrypt']
        );
    } catch {
        return null;
    }
}

// Returns a base64 string prefixed with "enc:" so we can tell encrypted from legacy plaintext.
export async function encryptText(key, plaintext) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encoded = new TextEncoder().encode(String(plaintext));
    const ciphertext = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, encoded);
    const combined = new Uint8Array(12 + ciphertext.byteLength);
    combined.set(iv);
    combined.set(new Uint8Array(ciphertext), 12);
    return 'enc:' + btoa(String.fromCharCode(...combined));
}

// Decrypts an "enc:..." string. If data is not encrypted (legacy), returns it as-is.
export async function decryptText(key, data) {
    if (!data || !String(data).startsWith('enc:')) return data;
    try {
        const combined = Uint8Array.from(atob(String(data).slice(4)), c => c.charCodeAt(0));
        const iv = combined.slice(0, 12);
        const ciphertext = combined.slice(12);
        const decrypted = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ciphertext);
        return new TextDecoder().decode(decrypted);
    } catch {
        return '[encrypted — sign in with the original account to view]';
    }
}
