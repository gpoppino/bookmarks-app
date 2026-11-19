import {createSaveHandler} from "./controller.js";

const handleSave = createSaveHandler(browser);
// A non-async listener leaves unrelated messages available to other listeners.
browser.runtime.onMessage.addListener((message, sender) => {
  if (message?.type === "saveBookmark") return handleSave(message, sender);
  return undefined;
});
