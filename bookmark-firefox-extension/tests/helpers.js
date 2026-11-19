export const TOKEN = `bkt_${"a".repeat(43)}`;
export const SETTINGS = {baseUrl: "https://bookmarks.example.com", token: TOKEN};

export function mockBrowser(settings = SETTINGS) {
  const store = settings ? {settings: structuredClone(settings)} : {};
  const origins = new Set(settings ? [`${new URL(settings.baseUrl).protocol}//${new URL(settings.baseUrl).hostname}/*`] : []);
  const calls = {requests: [], removed: [], messages: [], options: 0};
  const api = {
    runtime: {
      id: "firefox@bookmarks-app.local",
      getURL: path => `moz-extension://test-id/${path}`,
      openOptionsPage: async () => { calls.options++; },
      sendMessage: async message => { calls.messages.push(message); return {ok: true, message: "Bookmark guardado."}; },
    },
    tabs: {query: async () => [{url: "https://example.org/article?q=test#section", title: "Una página"}]},
    permissions: {
      contains: async request => request.origins.every(origin => origins.has(origin)),
      request: async request => { calls.requests.push(request); request.origins.forEach(origin => origins.add(origin)); return true; },
      getAll: async () => ({origins: [...origins]}),
      remove: async request => { calls.removed.push(request); request.origins.forEach(origin => origins.delete(origin)); return true; },
    },
    storage: {local: {
      get: async key => ({[key]: structuredClone(store[key])}),
      set: async values => { Object.assign(store, structuredClone(values)); },
      remove: async key => { delete store[key]; },
    }},
  };
  return {api, store, origins, calls};
}

export const trustedSender = api => ({id: api.runtime.id, url: api.runtime.getURL("popup.html")});
export const settle = () => new Promise(resolve => setImmediate(resolve));
