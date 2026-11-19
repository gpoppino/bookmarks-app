import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {JSDOM} from "jsdom";
import {initPopup} from "../popup.js";
import {initOptions} from "../options.js";
import {mockBrowser, SETTINGS, TOKEN, settle, trustedSender} from "./helpers.js";
import {createSaveHandler} from "../controller.js";

function page(name) {
  const dom = new JSDOM(readFileSync(new URL(`../${name}.html`, import.meta.url), "utf8"));
  const doc = dom.window.document;
  return {dom, doc, get: selector => doc.querySelector(selector), submit: selector => {
    doc.querySelector(selector).dispatchEvent(new dom.window.Event("submit", {bubbles: true, cancelable: true}));
  }};
}

test("popup captures current tab and submits tags once, showing confirmation", async () => {
  const p = page("popup");
  const {api, calls} = mockBrowser();
  let finish;
  api.runtime.sendMessage = async message => {
    calls.messages.push(message);
    return new Promise(resolve => { finish = resolve; });
  };
  await initPopup(api, p.doc);
  assert.equal(p.get("#url").value, "https://example.org/article?q=test#section");
  assert.equal(p.get("#page-title").textContent, "Una página");
  p.get("#tags").value = "Go, fotografía";
  p.submit("form");
  p.submit("form");
  assert.equal(calls.messages.length, 1);
  assert.equal(calls.messages[0].tags, "Go, fotografía");
  assert.equal(p.get("#save").disabled, true);
  assert.equal(p.get("#url").disabled, true);
  finish({ok: true, message: "Bookmark guardado."});
  await settle();
  assert.equal(p.get("#status").dataset.state, "success");
  assert.equal(p.get("#save").disabled, true);
  assert.equal(p.get("#url").disabled, false);
  p.get("#url").dispatchEvent(new p.dom.window.Event("input", {bubbles: true}));
  assert.equal(p.get("#save").disabled, false);
  p.dom.window.close();
});

test("first-run popup directs user to settings and cannot send a bookmark", async () => {
  const p = page("popup");
  const {api, calls} = mockBrowser(null);
  await initPopup(api, p.doc);
  assert.equal(p.get("#save").disabled, true);
  assert.match(p.get("#status").textContent, /Configuración/);
  p.submit("form");
  assert.equal(calls.messages.length, 0);
  p.get("#options").click();
  await settle();
  assert.equal(calls.options, 1);
  p.dom.window.close();
});

test("restricted tabs cannot save until an HTTP URL is entered; title is treated as text", async () => {
  const p = page("popup");
  const {api, calls} = mockBrowser();
  api.tabs.query = async () => [{url: "about:config", title: "<img src=x onerror=alert(1)>"}];
  await initPopup(api, p.doc);
  assert.equal(p.get("#page-title img"), null);
  p.submit("form");
  await settle();
  assert.equal(calls.messages.length, 0);
  p.get("#url").value = "https://go.dev/";
  p.submit("form");
  await settle();
  assert.equal(calls.messages.length, 1);
  p.dom.window.close();
});

test("popup surfaces backend duplicates and permits correcting or retrying", async () => {
  const p = page("popup");
  const {api} = mockBrowser();
  api.runtime.sendMessage = async () => ({ok: false, code: "duplicate", message: "Esta URL ya está guardada en tu cuenta."});
  await initPopup(api, p.doc);
  p.submit("form");
  await settle();
  assert.match(p.get("#status").textContent, /ya está guardada/);
  assert.equal(p.get("#save").disabled, false);
  p.dom.window.close();
});

test("options keeps the stored token out of the DOM and permits retaining it", async () => {
  const p = page("options");
  const {api, calls, store} = mockBrowser();
  await initOptions(api, p.doc);
  assert.equal(p.get("#token").value, "");
  assert.equal(p.doc.documentElement.outerHTML.includes(TOKEN), false);
  p.submit("form");
  await settle();
  assert.deepEqual(store.settings, SETTINGS);
  assert.deepEqual(calls.requests, [{origins: ["https://bookmarks.example.com/*"]}]);
  assert.equal(p.get("#status").dataset.state, "success");
  p.dom.window.close();
});

test("denied host access preserves previous settings and grants", async () => {
  const p = page("options");
  const {api, store, calls} = mockBrowser();
  api.permissions.request = async () => false;
  await initOptions(api, p.doc);
  p.get("#base-url").value = "https://new.example.com";
  p.get("#token").value = TOKEN;
  p.submit("form");
  await settle();
  assert.deepEqual(store.settings, SETTINGS);
  assert.equal(calls.removed.length, 0);
  assert.match(p.get("#status").textContent, /No se concedió/);
  p.dom.window.close();
});

test("destination change requires a new explicit token and removes old host access", async () => {
  const p = page("options");
  const {api, store, calls, origins} = mockBrowser();
  await initOptions(api, p.doc);
  p.get("#base-url").value = "https://new.example.com:8443/prefix/";
  p.submit("form");
  await settle();
  assert.equal(calls.requests.length, 0);
  assert.deepEqual(store.settings, SETTINGS);
  p.get("#token").value = `bkt_${"z".repeat(43)}`;
  p.submit("form");
  await settle();
  assert.equal(store.settings.baseUrl, "https://new.example.com:8443/prefix");
  assert.deepEqual([...origins], ["https://new.example.com/*"]);
  assert.equal(p.get("#token").value, "");
  p.dom.window.close();
});

test("clearing options removes credentials and host access, without calling backend", async () => {
  const p = page("options");
  const {api, store, origins, calls} = mockBrowser();
  await initOptions(api, p.doc);
  p.get("#forget").click();
  await settle();
  assert.equal(store.settings, undefined);
  assert.equal(origins.size, 0);
  assert.equal(calls.messages.length, 0);
  assert.match(p.get("#status").textContent, /revocar|revoques/);
  p.dom.window.close();
});

test("end-to-end UI contract: configure local server, capture tab, authenticate save", async () => {
  const {api, store, origins} = mockBrowser(null);
  const options = page("options");
  await initOptions(api, options.doc);
  options.get("#base-url").value = "http://127.0.0.1:8000/";
  options.get("#token").value = TOKEN;
  options.submit("form");
  await settle();
  assert.equal(store.settings.baseUrl, "http://127.0.0.1:8000");
  assert.deepEqual([...origins], ["http://127.0.0.1/*"]);
  let saved;
  const handler = createSaveHandler(api, async (url, request) => {
    assert.equal(url, "http://127.0.0.1:8000/api/bookmarks");
    assert.equal(request.headers.Authorization, `Bearer ${TOKEN}`);
    saved = JSON.parse(request.body);
    return new Response(JSON.stringify({id: 42}), {status: 201});
  });
  api.runtime.sendMessage = message => handler(message, trustedSender(api));
  const popup = page("popup");
  await initPopup(api, popup.doc);
  popup.get("#tags").value = " Go, go, fotografía ";
  popup.submit("form");
  await settle();
  assert.deepEqual(saved, {url: "https://example.org/article?q=test#section", tags: ["go", "fotografía"]});
  assert.equal(popup.get("#status").dataset.state, "success");
  options.dom.window.close();
  popup.dom.window.close();
});
