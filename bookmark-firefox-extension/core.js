export const SETTINGS_KEY = "settings";

export function normalizeBaseUrl(value) {
  let url;
  try {
    url = new URL(value.trim());
  } catch {
    throw new Error("Ingresá una URL válida para el backend.");
  }
  const loopback = ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  if (url.protocol !== "https:" && !(url.protocol === "http:" && loopback)) {
    throw new Error("Usá HTTPS para el backend; HTTP solo se permite en localhost, 127.0.0.1 o [::1].");
  }
  if (url.username || url.password || url.search || url.hash) {
    throw new Error("La URL del backend no debe incluir credenciales, parámetros ni fragmentos.");
  }
  return url.href.replace(/\/+$/, "");
}

export function hostPermission(baseUrl) {
  const url = new URL(baseUrl);
  // Firefox match patterns must omit ports, even for a local development server.
  return `${url.protocol}//${url.hostname}/*`;
}

export function validateSettings(settings) {
  const baseUrl = normalizeBaseUrl(settings?.baseUrl ?? "");
  const token = (settings?.token ?? "").trim();
  if (!/^bkt_[A-Za-z0-9_-]{43}$/.test(token)) {
    throw new Error("Ingresá un bot token válido (bkt_…) creado en Bookmarks App.");
  }
  return {baseUrl, token};
}

export function settingsFromForm(baseUrl, token, savedSettings) {
  const normalizedUrl = normalizeBaseUrl(baseUrl);
  if (!token.trim() && savedSettings?.baseUrl !== normalizedUrl) {
    throw new Error("Al cambiar el servidor, ingresá el token de ese servidor.");
  }
  return validateSettings({baseUrl: normalizedUrl, token: token.trim() || savedSettings?.token});
}

export function validateBookmarkUrl(value) {
  let url;
  try {
    url = new URL(value.trim());
  } catch {
    throw new Error("Ingresá la URL de una página web.");
  }
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) {
    throw new Error("Solo se pueden guardar páginas HTTP o HTTPS sin credenciales en la URL.");
  }
  return url.href;
}

export function parseTags(value) {
  if (typeof value !== "string") throw new Error("Las etiquetas deben ser texto separado por comas.");
  return [...new Set(value.split(",").map(tag => tag.trim().toLowerCase()).filter(Boolean))];
}

export async function createBookmark(settings, bookmark, fetchImpl = fetch, timeoutMs = 20000) {
  const {baseUrl, token} = validateSettings(settings);
  const url = validateBookmarkUrl(bookmark.url);
  const tags = parseTags(bookmark.tags);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(`${baseUrl}/api/bookmarks`, {
      method: "POST",
      headers: {"Content-Type": "application/json", "Authorization": `Bearer ${token}`},
      body: JSON.stringify({url, tags}),
      credentials: "omit",
      redirect: "error",
      cache: "no-store",
      referrerPolicy: "no-referrer",
      signal: controller.signal,
    });
    if (response.status === 401 || response.status === 403) {
      return {ok: false, code: "auth", message: "El token fue rechazado. Puede haber vencido o sido revocado. Revisá la configuración."};
    }
    if (response.status === 400) {
      const body = await response.json().catch(() => null);
      if (body?.detail === "Bookmark already exists") {
        return {ok: false, code: "duplicate", message: "Esta URL ya está guardada en tu cuenta."};
      }
      return {ok: false, code: "metadata", message: "El backend no pudo guardar esta página. Verificá que pueda acceder a su URL."};
    }
    if (response.status !== 201) {
      return {ok: false, code: "server", message: `El servidor respondió con un error (HTTP ${response.status}). Revisá la URL del backend.`};
    }
    return {ok: true, message: "Bookmark guardado."};
  } catch {
    return controller.signal.aborted
      ? {ok: false, code: "timeout", message: "Se agotó el tiempo de espera. Verificá en Bookmarks App si se guardó antes de reintentar."}
      : {ok: false, code: "network", message: "No se pudo conectar. Revisá la URL, el certificado HTTPS, los permisos y que el backend esté disponible. Si se cortó la conexión, verificá si se guardó antes de reintentar."};
  } finally {
    clearTimeout(timer);
  }
}
