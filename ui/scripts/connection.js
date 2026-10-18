export function connectionDetails(data) {
  const ip = data.publicIP;
  if (typeof ip !== "string" || !/^\d{1,3}(\.\d{1,3}){3}$/.test(ip) ||
      ip.split(".").some((part) => Number(part) > 255) ||
      !Number.isInteger(data.port) || data.port < 1 || data.port > 65535) {
    throw new Error("No valid public SSH endpoint is available.");
  }
  const authority = `root@${ip}:${data.port}`;
  return {
    endpoint: `${ip}:${data.port}`,
    ssh: `ssh -t -p ${data.port} root@${ip} 'cd /workspace && exec bash -l'`,
    vscode: `vscode://vscode-remote/ssh-remote+${authority}/workspace`,
    code: `code --remote ssh-remote+${authority} /workspace`,
  };
}
