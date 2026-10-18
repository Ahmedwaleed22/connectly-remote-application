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
      const setup = document.createElement("p");
      setup.textContent = "1. Enter the path to your private key on this computer. 2. Add the generated entry to ~/.ssh/config (Windows: %USERPROFILE%/.ssh/config), before any Host * defaults. 3. Open VS Code.";
      const label = document.createElement("label");
      label.textContent = "Private key path on your computer";
      const keyPath = document.createElement("input");
      keyPath.type = "text";
      keyPath.placeholder = "~/.ssh/my_container_key";
      keyPath.autocomplete = "off";
      keyPath.spellcheck = false;
      label.append(keyPath);
      const hint = document.createElement("p");
      hint.textContent = "Enter a path, not the key contents. This stays in your browser and is never sent to the server.";
      const config = document.createElement("code");
      const actions = document.createElement("div");
      const validation = document.createElement("p");
      validation.setAttribute("role", "status");
      const open = document.createElement("a");
      open.textContent = "Open /workspace in VS Code";
      const command = document.createElement("code");
      const codeCommand = document.createElement("code");
      const preference = `connectly.keyPath.${connection.endpoint}`;
      try { keyPath.value = localStorage.getItem(preference) || ""; } catch { /* Storage can be disabled. */ }
      function update() {
        actions.replaceChildren();
        config.textContent = "";
        command.textContent = "";
        codeCommand.textContent = "";
        open.removeAttribute("href");
        validation.textContent = "";
        if (!keyPath.value.trim()) {
          validation.textContent = "Enter your private key path to generate the SSH config.";
          return;
        }
        try {
          const configured = connectionDetails(data, keyPath.value);
          config.textContent = configured.sshConfig;
          open.href = configured.vscode;
          command.textContent = configured.ssh;
          codeCommand.textContent = configured.code;
          actions.append(copyButton("Copy SSH config", configured.sshConfig), open,
            copyButton("Copy SSH command", configured.ssh), copyButton("Copy VS Code command", configured.code));
          try { localStorage.setItem(preference, keyPath.value); } catch { /* Optional local preference. */ }
        } catch (error) { validation.textContent = error.message; }
      }
      keyPath.addEventListener("input", update);
      details.append(setup, label, hint, validation, config, actions, command, codeCommand);
      update();
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
