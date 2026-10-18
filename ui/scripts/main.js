import { connectionDetails } from "./connection.js";

export default function activate(remote) {
  remote.ui.addButton(remote.slots.applicationCardActions, {
    label: "Connect",
    title: "Public SSH address and workspace connection",
    when: (context) => context.instance?.applicationId === remote.application.id && context.instance.status === "running",
    onClick: (context) => remote.ui.openPopup({
      title: "Connectly · /workspace", width: 640,
      mount: (host) => mountConnection(host, remote, { instanceId: context.instance.id }),
    }),
  });
  remote.ui.register(remote.slots.applicationsPanel,
    (host, context) => mountConnection(host, remote, { projectId: context.projectId }),
    { when: (context) => context.scope === "project" && remote.backend.available });
}

function mountConnection(host, remote, target) {
  const controller = new AbortController();
  let disposed = false;
  host.className = "connectly";
  const status = document.createElement("p");
  status.setAttribute("role", "status");
  const details = document.createElement("div");
  const feedback = document.createElement("p");
  feedback.setAttribute("role", "status");
  const retry = document.createElement("button");
  retry.textContent = "Retry connection details";
  retry.type = "button";
  retry.hidden = true;
  host.append(status, details, retry, feedback);

  function copyButton(label, value) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(value);
        if (!disposed) feedback.textContent = "Copied.";
      } catch {
        if (!disposed) feedback.textContent = "Clipboard access failed. Select and copy the command above.";
      }
    });
    return button;
  }

  async function load() {
    retry.hidden = true;
    details.replaceChildren();
    status.textContent = "Finding the public SSH address…";
    host.setAttribute("aria-busy", "true");
    try {
      const data = await remote.backend.call("connection", {
        ...target, signal: controller.signal,
      });
      if (disposed) return;
      const connection = connectionDetails(data);
      status.textContent = `Public SSH: ${connection.endpoint} · root · /workspace`;
      const open = document.createElement("a");
      open.href = connection.vscode;
      open.textContent = "Open /workspace in VS Code";
      const command = document.createElement("code");
      command.textContent = connection.ssh;
      const codeCommand = document.createElement("code");
      codeCommand.textContent = connection.code;
      details.append(open, copyButton("Copy SSH command", connection.ssh),
        copyButton("Copy VS Code command", connection.code), command, codeCommand);
    } catch (error) {
      if (disposed) return;
      status.textContent = error.message || "Could not load the public SSH address.";
      retry.hidden = false;
    } finally {
      if (!disposed) host.setAttribute("aria-busy", "false");
    }
  }
  retry.addEventListener("click", load);
  void load();
  return () => { disposed = true; controller.abort(); retry.removeEventListener("click", load); };
}
