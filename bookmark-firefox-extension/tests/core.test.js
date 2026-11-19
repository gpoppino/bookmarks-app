import test from "node:test";
import assert from "node:assert/strict";
import {createBookmark, hostPermission, normalizeBaseUrl, parseTags, settingsFromForm, validateBookmarkUrl, validateSettings} from "../core.js";
import {SETTINGS, TOKEN} from "./helpers.js";

test("backend URL supports HTTPS, reverse proxy paths, and loopback HTTP", () => {
  assert.equal(normalizeBaseUrl(" https://example.com/bookmarks/// "), "https://example.com/bookmarks");
  for (const host of ["localhost", "127.0.0.1", "[::1]"]) {
    assert.equal(normalizeBaseUrl(`http://${host}:8000/`), `http://${host}:8000`);
    assert.equal(hostPermission(`http://${host}:8000/prefix`), `http://${host}/*`);
  }
});

test("backend rejects remote plaintext, non-web schemes, credentials, query, and fragment", () => {
  for (const value of ["invalid", "http://example.com", "http://192.168.1.1", "file:///tmp/test", "https://user:pass@example.com", "https://example.com?x=y", "https://example.com#part"]) {
    assert.throws(() => normalizeBaseUrl(value));
  }
});

test("changing destination requires explicitly entering a token", () => {
  assert.deepEqual(settingsFromForm(`${SETTINGS.baseUrl}/`, "", SETTINGS), SETTINGS);
  assert.throws(() => settingsFromForm("https://other.example.com", "", SETTINGS), /cambiar el servidor/);
  assert.deepEqual(settingsFromForm("https://other.example.com", TOKEN, SETTINGS), {baseUrl: "https://other.example.com", token: TOKEN});
  assert.throws(() => validateSettings({...SETTINGS, token: "session-jwt"}), /bot token/);
});

test("bookmark URL preserves query and fragment and rejects restricted schemes and embedded credentials", () => {
  const url = "https://example.org/article?q=a%20b#section";
  assert.equal(validateBookmarkUrl(url), url);
  for (const value of ["about:config", "file:///tmp/test", "javascript:alert(1)", "data:text/html,test", "https://user:pass@example.org", "invalid"]) {
    assert.throws(() => validateBookmarkUrl(value));
  }
  assert.deepEqual(parseTags(" Go, , fotografía, go, Linux, linux "), ["go", "fotografía", "linux"]);
  assert.deepEqual(parseTags(""), []);
});

test("save sends the exact backend contract without cookies or redirects", async () => {
  let request;
  const result = await createBookmark({...SETTINGS, baseUrl: `${SETTINGS.baseUrl}/prefix/`}, {url: "https://go.dev/", tags: "Go, go, Web"}, async (url, options) => {
    request = {url, options};
    return new Response(JSON.stringify({id: 1}), {status: 201});
  });
  assert.equal(result.ok, true);
  assert.equal(request.url, `${SETTINGS.baseUrl}/prefix/api/bookmarks`);
  assert.equal(request.options.method, "POST");
  assert.equal(request.options.headers.Authorization, `Bearer ${TOKEN}`);
  assert.deepEqual(JSON.parse(request.options.body), {url: "https://go.dev/", tags: ["go", "web"]});
  assert.equal(request.options.credentials, "omit");
  assert.equal(request.options.redirect, "error");
  assert.equal(request.options.referrerPolicy, "no-referrer");
});

test("API errors distinguish duplicate, metadata, auth, and server failure without echoing response secrets", async () => {
  for (const [status, detail, code] of [
    [400, "Bookmark already exists", "duplicate"], [400, TOKEN, "metadata"],
    [401, TOKEN, "auth"], [403, TOKEN, "auth"], [422, TOKEN, "server"], [503, TOKEN, "server"], [200, TOKEN, "server"],
  ]) {
    const result = await createBookmark(SETTINGS, {url: "https://go.dev", tags: ""}, async () => new Response(JSON.stringify({detail}), {status}));
    assert.equal(result.code, code);
    assert.equal(result.message.includes(TOKEN), false);
  }
});

test("malformed error JSON and connection failures produce actionable messages", async () => {
  const badJson = await createBookmark(SETTINGS, {url: "https://go.dev", tags: ""}, async () => new Response("not json", {status: 400}));
  assert.equal(badJson.code, "metadata");
  const network = await createBookmark(SETTINGS, {url: "https://go.dev", tags: ""}, async () => { throw new Error(TOKEN); });
  assert.equal(network.code, "network");
  assert.equal(network.message.includes(TOKEN), false);
});

test("timeout aborts the request and warns about uncertain save outcome", async () => {
  const result = await createBookmark(SETTINGS, {url: "https://go.dev", tags: ""}, async (_url, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener("abort", () => reject(new Error("aborted")));
  }), 10);
  assert.equal(result.code, "timeout");
  assert.match(result.message, /si se guardó/);
});

test("invalid settings or page URLs never issue a request", async () => {
  let calls = 0;
  const fetchImpl = async () => { calls++; };
  await assert.rejects(createBookmark({...SETTINGS, token: "bad"}, {url: "https://go.dev", tags: ""}, fetchImpl));
  await assert.rejects(createBookmark(SETTINGS, {url: "about:config", tags: ""}, fetchImpl));
  assert.equal(calls, 0);
});
