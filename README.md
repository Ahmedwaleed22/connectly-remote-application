# Connectly

A plugin for [Remote](https://github.com/futrx-com/remote.futrx) that enables
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
4. Read the allocated host port on the installed application. Remote prefers
   2222 and allocates a free port on conflict: six projects can receive
   2222–2227, depending on ports already in use. Upgrades preserve that port.
5. Connect to the Remote **server's public IP or directly resolving hostname**:
   `ssh -i ~/.ssh/remote-project -p 2222 root@SERVER_IP`.
   Substitute the actual allocated port. This is raw TCP SSH, not the HTTPS
   dev-server URL. Allow that TCP port in your host/cloud firewall; a proxied
   HTTP hostname cannot carry this connection.

Add this to your local `~/.ssh/config`, using the actual host and port:

```sshconfig
Host remote-project
    HostName SERVER_IP
    Port 2222
    User root
    IdentityFile ~/.ssh/remote-project
    IdentitiesOnly yes
```

In VS Code, install **Remote - SSH**, select **Connect to Host → remote-project**,
then open `/workspace`. SSH grants root access inside that project's container,
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

## Releases

Set `version` in `application.json`, commit and push the changes, then push the
matching tag. For example, with version `0.1.0`:

```bash
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions checks the package, creates a GitHub Release, and attaches
`connectly-0.1.0.zip`. Download that asset to install in Remote. The automatic
GitHub source archives include development files; the attached plugin ZIP holds
only `README.md`, `LICENSE`, `application.json`, and `infra/install.sh` at its root.
A tag/version mismatch fails the workflow before publishing. Use a new version
and tag for each release. No additional GitHub token secret is needed: the
workflow uses its repository-scoped `GITHUB_TOKEN` with `contents: write`.

To build the same ZIP locally:

```bash
python3 -B infra/test_package.py
python3 -B infra/package.py --tag v0.1.0 --output-dir /tmp/ssh-access-release
```

## Verification

Run `python3 infra/test_install.py` as root on a Linux system with OpenSSH
installed. Tests redirect provisioning paths to a temporary directory and check
real OpenSSH configuration, host identity preservation, and rejected inputs.
They temporarily create `/run/sshd` when absent, and run a short-lived loopback
listener to test successful login and rejection of an unrelated key.
Run `bash -n infra/install.sh` for shell syntax. Fresh apt installation, full LXD
lifecycle, VS Code interaction, and external firewall reachability must be verified
on your Remote server after installation.

## License

Licensed under the GNU Affero General Public License, version 3 or later
(`AGPL-3.0-or-later`), matching [Remote's license](https://github.com/futrx-com/remote.futrx/blob/main/LICENSE).
See [LICENSE](LICENSE) for the complete terms. The license is included in release ZIPs.
