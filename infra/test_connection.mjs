import test from "node:test";
import assert from "node:assert/strict";
import { connectionDetails } from "../ui/scripts/connection.js";
import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

test("VS Code alias resolves the allocated port and a non-default identity", () => {
  const details = connectionDetails({ publicIP: "203.0.113.8", port: 5345 }, "/home/me/SSH Keys/container_key");
  assert.equal(typeof details.sshConfig, "string");
  const directory = mkdtempSync(join(tmpdir(), "connectly-ssh-config-"));
  try {
    const config = join(directory, "config");
    writeFileSync(config, details.sshConfig);
    const resolved = execFileSync("ssh", ["-G", "-F", config, details.alias], { encoding: "utf8" });
    assert.match(resolved, /^hostname 203\.0\.113\.8$/m);
    assert.match(resolved, /^port 5345$/m);
    assert.match(resolved, /^identityfile \/home\/me\/SSH Keys\/container_key$/m);
    assert.match(resolved, /^identitiesonly yes$/m);
    assert.equal(details.vscode, `vscode://vscode-remote/ssh-remote+${details.alias}/workspace`);
  } finally { rmSync(directory, { recursive: true, force: true }); }
});

test("connections use the public IP, allocated port, and workspace", () => {
  const details = connectionDetails({ publicIP: "203.0.113.8", port: 5345 });
  assert.equal(details.endpoint, "203.0.113.8:5345");
  assert.equal(details.vscode, "vscode://vscode-remote/ssh-remote+connectly-203-0-113-8-5345/workspace");
  assert.match(details.ssh, /cd \/workspace/);
  assert.match(details.code, /-5345 \/workspace$/);
});
test("custom key paths cannot inject SSH config directives", () => {
  for (const path of ['key"file', "key\nProxyCommand bad", "key\rfile"]) {
    assert.throws(() => connectionDetails({publicIP: "203.0.113.8", port: 5345}, path));
  }
  assert.equal(connectionDetails({publicIP: "203.0.113.8", port: 5345}).sshConfig, "");
});
test("invalid connection data never becomes a command or link", () => {
  for (const data of [{publicIP: "$(id)", port: 22}, {publicIP: "1.2.3.4", port: 0}, {publicIP: "999.2.3.4", port: 22}]) {
    assert.throws(() => connectionDetails(data));
  }
});
