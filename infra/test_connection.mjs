import test from "node:test";
import assert from "node:assert/strict";
import { connectionDetails } from "../ui/scripts/connection.js";

test("connections use the public IP, allocated port, and workspace", () => {
  const details = connectionDetails({ publicIP: "203.0.113.8", port: 5345 });
  assert.equal(details.endpoint, "203.0.113.8:5345");
  assert.equal(details.vscode, "vscode://vscode-remote/ssh-remote+root@203.0.113.8:5345/workspace");
  assert.match(details.ssh, /cd \/workspace/);
  assert.match(details.code, /5345 \/workspace$/);
});
test("invalid connection data never becomes a command or link", () => {
  for (const data of [{publicIP: "$(id)", port: 22}, {publicIP: "1.2.3.4", port: 0}, {publicIP: "999.2.3.4", port: 22}]) {
    assert.throws(() => connectionDetails(data));
  }
});
