# Connectly

An application for [Remote](https://github.com/futrx-com/remote.futrx) that enables
per-container SSH access and connections from VS Code Remote SSH.

Standalone Remote application, uploaded as a ZIP. Install it in each project
whose existing container you want to reach. No Remote core changes or separate
application container are required. Requires the structured manifest-service
contract documented by Remote's installable applications.

## Install and connect

1. On your own computer, create a key if needed:
   `ssh-keygen -t ed25519 -f ~/.ssh/remote-project`.
2. Download the installable ZIP from the
   [latest release](https://github.com/Ahmedwaleed22/connectly-remote-plugin/releases/latest)
   and upload it in **Settings → Applications**.
3. Install **Connectly** in the project's Applications tab. Paste the contents
   of `~/.ssh/remote-project.pub` into **SSH public key**. Keep the private key
   on your computer. Use a different key for each project if desired.
4. Click **Connect** on the Connectly card, or use its panel below the app list.
   **Public SSH** shows the server's public IPv4
   address and this container's allocated SSH port. Enter your private key's
   path on your computer, such as `~/.ssh/remote-project`. Never paste the key
   contents. Use **Copy SSH config** and add the entry to your local
   `~/.ssh/config` before any `Host *` defaults (Windows:
   `%USERPROFILE%/.ssh/config`). Then use **Open /workspace in VS Code** or
   **Copy SSH command**. Both use that entry's exact port and private key.
5. Allow the displayed TCP port in your host/cloud firewall. This is raw SSH,
   not the HTTPS dev-server URL; a proxied HTTP hostname cannot carry it.

Connectly detects the Remote server's outbound public IPv4 address using ipify
from its host backend. If your server uses NAT, a VPN, or a different ingress IP,
set **Public SSH IPv4 address** during installation. The generic Remote connection
panel still shows the listener's bind address (`0.0.0.0`); use Connectly's
**Public SSH** address to connect from your computer.

Connectly generates a separate SSH alias for each public IP and port, so containers
on the same server keep their own connection settings. The key path is remembered
only in this browser; it is never sent to Remote. If VS Code uses a custom
`remote.SSH.configFile`, add the generated entry to that file instead. Update the
entry if you change the container's host port or local private key.

In VS Code, install **Remote - SSH**, then use Connectly's **Open /workspace in
VS Code** link. If the browser cannot open VS Code, use **Copy VS Code command**
and run it locally. SSH login shells and SFTP also start in `/workspace`.
SSH grants root access inside that project's container,
matching the agent's workspace permissions. Only public-key authentication is
enabled; there is no generated password to reveal. The connection identity is
the server host, allocated port, username `root`, and your local private key.
TCP forwarding is enabled for VS Code. Agent forwarding is disabled.

Before accepting a new host key, compare its fingerprint with this command run
in the project's existing Remote terminal:

```bash
ssh-keygen -lf /workspace/.ssh-access/ssh_host_ed25519_key.pub
```

## Lifecycle and state

Remote owns `ssh-access.service`, port allocation, the LXD TCP proxy, and readiness
checks. The installer only provisions OpenSSH, a dedicated config, and key files.
It does not change root's password, root's existing authorized keys, the distro's
SSH configuration, or an existing SSH service. New package installation suppresses
automatic service startup when no pre-existing package policy exists. When this
app installs a previously absent OpenSSH server, it disables the newly installed
distro service/socket so they cannot open an unmanaged port 22 on reboot.

Authorized keys and the per-project host key live in `/workspace/.ssh-access`
with root-only permissions and survive workspace/container reprovisioning.
Repeat installs preserve the host key and replace the app's authorized public key.
To rotate client access, uninstall and reinstall with the replacement public key.
Bump the package version for provisioning changes; re-uploading the same version
does not re-run provisioning.

Stopping the app stops its listener. Uninstall removes the proxy and managed
service, retaining project files, installed OpenSSH packages, and key state.
After uninstall, delete `/workspace/.ssh-access` and
`/etc/ssh/ssh-access.conf` if you want to remove retained state. This does not
manage any other SSH access you previously enabled in the container.

The project container must be running. Container stop/recycle interrupts sessions;
reconnect when Remote has restored the container and application. This package
does not configure firewalls, DNS, NAT, or keep a project awake indefinitely.
Connectly's workspace login setup remains in `/etc/profile.d/connectly-workspace.sh`
after uninstall; remove that file to restore the default SSH login directory.

## License

Licensed under the GNU Affero General Public License, version 3 or later
(`AGPL-3.0-or-later`), matching [Remote's license](https://github.com/futrx-com/remote.futrx/blob/main/LICENSE).
See [LICENSE](LICENSE) for the complete terms. The license is included in release ZIPs.
