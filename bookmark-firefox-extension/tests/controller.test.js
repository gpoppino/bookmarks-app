import test from "node:test";
import assert from "node:assert/strict";
import {createSaveHandler} from "../controller.js";
import {mockBrowser, SETTINGS, trustedSender, settle} from "./helpers.js";

const message = {type: "saveBookmark", url: "https://example.org/article", tags: "Go"};

test("background rejects senders outside the extension and unrelated messages", async () => {
  const {api} = mockBrowser();
  const handler = createSaveHandler(api, () => { assert.fail("Must not fetch"); });
  assert.equal(await handler(message, {id: "other", url: api.runtime.getURL("popup.html")}), undefined);
  assert.equal(await handler(message, {id: api.runtime.id, url: "https://example.org"}), undefined);
  assert.equal(await handler({type: "other"}, trustedSender(api)), undefined);
});

test("missing settings or revoked host permission stop a request", async () => {
  const {api, store, origins} = mockBrowser(null);
  const handler = createSaveHandler(api, () => { assert.fail("Must not fetch"); });
  assert.equal((await handler(message, trustedSender(api))).code, "settings");
  store.settings = SETTINGS;
  origins.clear();
  assert.equal((await handler(message, trustedSender(api))).code, "permission");
});

test("background reads current credentials for every save", async () => {
  const {api, store} = mockBrowser();
  let authorization;
  const handler = createSaveHandler(api, async (_url, options) => {
    authorization = options.headers.Authorization;
    return new Response("{}", {status: 201});
  });
  const replacement = `bkt_${"z".repeat(43)}`;
  store.settings.token = replacement;
  assert.equal((await handler(message, trustedSender(api))).ok, true);
  assert.equal(authorization, `Bearer ${replacement}`);
});

test("concurrent saves for the same URL are coalesced until completion, then allow retry", async () => {
  const {api} = mockBrowser();
  let complete;
  let calls = 0;
  const handler = createSaveHandler(api, async () => {
    calls++;
    return new Promise(resolve => { complete = () => resolve(new Response("{}", {status: 201})); });
  });
  const first = handler(message, trustedSender(api));
  await settle();
  const second = await handler(message, trustedSender(api));
  assert.equal(second.code, "pending");
  assert.equal(calls, 1);
  complete();
  assert.equal((await first).ok, true);
  const third = handler(message, trustedSender(api));
  await settle();
  complete();
  assert.equal((await third).ok, true);
  assert.equal(calls, 2);
});

test("invalid pages and storage failures return safe errors", async () => {
  const {api} = mockBrowser();
  const handler = createSaveHandler(api, () => { assert.fail("Must not fetch"); });
  assert.equal((await handler({...message, url: "about:config"}, trustedSender(api))).code, "invalid");
  api.storage.local.get = async () => { throw new Error("storage unavailable"); };
  assert.equal((await handler(message, trustedSender(api))).code, "invalid");
});
