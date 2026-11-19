import {SETTINGS_KEY, createBookmark, hostPermission, validateBookmarkUrl, validateSettings} from "./core.js";

// Keep requests in the background so closing the popup doesn't cancel a save.
export function createSaveHandler(api, fetchImpl = fetch) {
  const pending = new Set();
  return async function handleSave(message, sender) {
    if (sender.id !== api.runtime.id || !sender.url?.startsWith(api.runtime.getURL(""))) {
      return undefined;
    }
    if (message?.type !== "saveBookmark") return undefined;
    try {
      const stored = await api.storage.local.get(SETTINGS_KEY);
      if (!stored[SETTINGS_KEY]) {
        return {ok: false, code: "settings", message: "Configurá el servidor y el token antes de guardar."};
      }
      const settings = validateSettings(stored[SETTINGS_KEY]);
      if (!await api.permissions.contains({origins: [hostPermission(settings.baseUrl)]})) {
        return {ok: false, code: "permission", message: "Falta permiso para acceder al backend. Abrí Configuración y guardá los ajustes para autorizarlo."};
      }
      const url = validateBookmarkUrl(message.url);
      const key = `${settings.baseUrl}\n${url}`;
      if (pending.has(key)) {
        return {ok: false, code: "pending", message: "Esta página ya se está guardando. Esperá unos segundos."};
      }
      pending.add(key);
      try {
        return await createBookmark(settings, {url, tags: message.tags}, fetchImpl);
      } finally {
        pending.delete(key);
      }
    } catch {
      return {ok: false, code: "invalid", message: "No se pudo guardar. Revisá la URL de la página y la configuración de la extensión."};
    }
  };
}
