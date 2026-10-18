export function connectionDetails(data, identityFile = "") {
  const ip = data.publicIP;
  if (typeof ip !== "string" || !/^\d{1,3}(\.\d{1,3}){3}$/.test(ip) ||
      ip.split(".").some((part) => Number(part) > 255) ||
      !Number.isInteger(data.port) || data.port < 1 || data.port > 65535) {
    throw new Error("No valid public SSH endpoint is available.");
  }
  const alias = `connectly-${ip.replaceAll(".", "-")}-${data.port}`;
  const path = identityFile.trim().replaceAll("\\", "/");
  if (/[\r\n\0"]/.test(path)) {
    throw new Error("The private key path cannot contain quotes or line breaks.");
  }
  const sshConfig = path ? [
    `Host ${alias}`,
    `    HostName ${ip}`,
    `    Port ${data.port}`,
    "    User root",
    `    IdentityFile "${path}"`,
    "    IdentitiesOnly yes",
    "",
  ].join("\n") : "";
  return {
    alias,
    sshConfig,
    endpoint: `${ip}:${data.port}`,
    ssh: `ssh -t ${alias} 'cd /workspace && exec bash -l'`,
    vscode: `vscode://vscode-remote/ssh-remote+${alias}/workspace`,
    code: `code --remote ssh-remote+${alias} /workspace`,
  };
}
