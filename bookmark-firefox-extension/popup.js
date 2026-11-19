import {SETTINGS_KEY, validateBookmarkUrl, validateSettings} from "./core.js";

export async function initPopup(api = browser, doc = document) {
  const form = doc.querySelector("#bookmark-form");
  const url = doc.querySelector("#url");
  const tags = doc.querySelector("#tags");
  const save = doc.querySelector("#save");
  const status = doc.querySelector("#status");
  let configured = false;
  let busy = false;
  function showStatus(message, state = "error") {
    status.textContent = message;
    status.dataset.state = state;
  }
  doc.querySelector("#options").addEventListener("click", async () => {
    try { await api.runtime.openOptionsPage(); }
    catch { showStatus("No se pudo abrir la configuración. Abrila desde about:addons."); }
  });
  form.addEventListener("input", () => {
    if (!busy) {
      save.disabled = !configured;
      status.textContent = "";
    }
  });
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (busy || !configured) return;
    try { validateBookmarkUrl(url.value); }
    catch (error) { showStatus(error.message); return; }
    busy = true;
    save.disabled = true;
    url.disabled = true;
    tags.disabled = true;
    showStatus("Guardando… Podés cerrar este panel; el envío sigue en segundo plano.", "pending");
    let succeeded = false;
    try {
      const result = await api.runtime.sendMessage({type: "saveBookmark", url: url.value, tags: tags.value});
      if (!result) throw new Error("No response");
      succeeded = result.ok;
      showStatus(result.message, result.ok ? "success" : "error");
    } catch {
      showStatus("No se recibió confirmación. Verificá si el bookmark se guardó antes de reintentar.");
    } finally {
      busy = false;
      url.disabled = false;
      tags.disabled = false;
      save.disabled = succeeded;
    }
  });
  // Query the tab before other awaits, while activeTab refers to the invoking tab.
  const tabQuery = api.tabs.query({active: true, currentWindow: true});
  try {
    const [stored, tabs] = await Promise.all([api.storage.local.get(SETTINGS_KEY), tabQuery]);
    const tab = tabs[0];
    doc.querySelector("#page-title").textContent = tab?.title || "Página actual";
    url.value = tab?.url || "";
    try {
      const settings = validateSettings(stored[SETTINGS_KEY]);
      configured = true;
      doc.querySelector("#destination").textContent = `Destino: ${settings.baseUrl}`;
      save.disabled = false;
    } catch {
      showStatus("Abrí Configuración para indicar tu servidor y bot token.");
      return;
    }
    try { validateBookmarkUrl(url.value); }
    catch { showStatus("Esta pestaña no es una página HTTP/HTTPS. Abrí una página web o ingresá su URL."); }
  } catch {
    showStatus("No se pudo leer la pestaña o la configuración. Cerrá y volvé a abrir el panel.");
  }
}

if (typeof browser !== "undefined") void initPopup();
