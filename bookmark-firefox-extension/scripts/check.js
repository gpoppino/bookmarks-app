import {readFileSync, readdirSync, existsSync} from "node:fs";
import {spawnSync} from "node:child_process";
import assert from "node:assert/strict";

const manifest = JSON.parse(readFileSync("manifest.json", "utf8"));
assert.equal(manifest.manifest_version, 3);
assert.ok(manifest.browser_specific_settings.gecko.id);
const files = [manifest.action.default_popup, manifest.options_ui.page,
  ...manifest.background.scripts, ...Object.values(manifest.icons)];
for (const file of files) assert.ok(existsSync(file), `Missing extension resource: ${file}`);
for (const file of readdirSync(".").filter(file => file.endsWith(".js"))) {
  const result = spawnSync(process.execPath, ["--check", file], {stdio: "inherit"});
  if (result.status !== 0) process.exit(result.status || 1);
}
console.log("Manifest resources and JavaScript syntax OK.");
