import {SETTINGS_KEY, hostPermission, settingsFromForm} from "./core.js";

export async function initOptions(api = browser, doc = document) {
  const form = doc.querySelector("#settings-form");
  const baseUrl = doc.querySelector("#base-url");
  const token = doc.querySelector("#token");
  const save = doc.querySelector("#save-settings");
  const forget = doc.querySelector("#forget");
  const status = doc.querySelector("#status");
  const tokenState = doc.querySelector("#token-state");
  let savedSettings;
  let busy = false;
  const setBusy = value => {
    busy = value;
    for (const element of [save, forget, baseUrl, token]) element.disabled = value;
  };
  const showStatus = (message, state = "error") => {
    status.textContent = message;
    status.dataset.state = state;
  };
  const updateTokenState = () => {
    tokenState.textContent = savedSettings?.token
      ? "Hay un token guardado. Dejá el campo vacío para conservarlo en el mismo servidor."
      : "Todavía no hay un token guardado.";
  };
  setBusy(true);
  async function removeOtherHosts(keep) {
    const {origins = []} = await api.permissions.getAll();
    const remove = origins.filter(origin => origin !== keep);
    if (remove.length) await api.permissions.remove({origins: remove});
  }
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (busy) return;
    let settings;
    try { settings = settingsFromForm(baseUrl.value, token.value, savedSettings); }
    catch (error) { showStatus(error.message); return; }
    setBusy(true);
    try {
      // Must be the first await in the user gesture, before any storage access.
      const granted = await api.permissions.request({origins: [hostPermission(settings.baseUrl)]});
      if (!granted) {
        showStatus("No se concedió acceso al servidor. La configuración anterior sigue vigente.");
        return;
      }
      await api.storage.local.set({[SETTINGS_KEY]: settings});
      savedSettings = settings;
      baseUrl.value = settings.baseUrl;
      token.value = "";
      updateTokenState();
      try {
        await removeOtherHosts(hostPermission(settings.baseUrl));
        showStatus("Configuración guardada. Abrí una página y usá el botón de Bookmarks App.", "success");
      } catch {
        showStatus("Configuración guardada. Revisá en about:addons los permisos de servidores anteriores.", "success");
      }
    } catch {
      showStatus("No se pudo guardar la configuración. Volvé a intentarlo.");
    } finally { setBusy(false); }
  });
  forget.addEventListener("click", async () => {
    if (busy) return;
    setBusy(true);
    try {
      await api.storage.local.remove(SETTINGS_KEY);
      savedSettings = undefined;
      token.value = "";
      baseUrl.value = "";
      updateTokenState();
      try {
        await removeOtherHosts();
        showStatus("Configuración local borrada. El token sigue vigente hasta que lo revoques en el backend.", "success");
      } catch {
        showStatus("Configuración borrada. Quitá los permisos del servidor desde about:addons.", "success");
      }
    } catch { showStatus("No se pudo borrar la configuración. Volvé a intentarlo."); }
    finally { setBusy(false); }
  });
  try {
    const stored = await api.storage.local.get(SETTINGS_KEY);
    savedSettings = stored[SETTINGS_KEY];
    baseUrl.value = savedSettings?.baseUrl || "http://127.0.0.1:8000";
    updateTokenState();
    setBusy(false);
  } catch {
    showStatus("No se pudo leer la configuración. Recargá esta página.");
  }
}

if (typeof browser !== "undefined") void initOptions();
