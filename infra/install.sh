#!/usr/bin/env bash
# Runs inside the project container; Remote owns the service and host proxy.
set -euo pipefail
umask 077

fail() { printf 'install: %s\n' "$1" >&2; exit 1; }
port="${APP_INTERNAL_PORT:-2222}"
[[ "$port" =~ ^[0-9]{1,5}$ ]] && (( 10#$port > 0 && 10#$port <= 65535 )) || fail 'invalid internal port'
public_key="${SSH_PUBLIC_KEY:-}"
[[ -n "$public_key" && "$public_key" != *$'\n'* && "$public_key" != *$'\r'* ]] || fail 'provide one OpenSSH public key'
# Reject authorized_keys options: the input is a public key, not configuration.
[[ "$public_key" =~ ^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(256|384|521)|sk-ssh-ed25519@openssh.com|sk-ecdsa-sha2-nistp256@openssh.com)[[:blank:]] ]] || fail 'unsupported public key format'

export DEBIAN_FRONTEND=noninteractive
if [[ ! -x /usr/sbin/sshd ]] || ! command -v ssh-keygen >/dev/null || ! command -v ssh-keyscan >/dev/null; then
  new_server=false
  if [[ ! -x /usr/sbin/sshd ]]; then new_server=true; fi
  apt-get update -qq
  # Do not auto-start the distribution's separate SSH listener during install.
  # An existing policy is respected and never overwritten.
  policy=/usr/sbin/policy-rc.d
  created_policy=false
  if [[ ! -e "$policy" && ! -L "$policy" ]]; then
    printf '#!/bin/sh\nexit 101\n' > "$policy"
    chmod 755 "$policy"
    created_policy=true
  fi
  cleanup_policy() { if "$created_policy"; then rm -f "$policy"; fi; }
  trap cleanup_policy EXIT
  apt-get install -y --no-install-recommends openssh-server openssh-client
  cleanup_policy
  trap - EXIT
  # A freshly installed distro daemon must not create a second, unmanaged
  # listener on port 22 at the next boot. Preserve pre-existing SSH services.
  if "$new_server"; then
    if systemctl cat ssh.socket >/dev/null 2>&1; then
      systemctl disable --now ssh.socket
    fi
    systemctl disable --now ssh.service
  fi
fi

candidate="$(mktemp)"
trap 'rm -f "$candidate"' EXIT
printf '%s\n' "$public_key" > "$candidate"
ssh-keygen -lf "$candidate" >/dev/null 2>&1 || fail 'invalid SSH public key'

# Workspace storage survives container replacement; never reuse another SSH
# service's authorized_keys or host identity.
state=/workspace/.ssh-access
install -d -m 700 -o root -g root "$state"
install -m 600 -o root -g root "$candidate" "$state/authorized_keys"
if [[ ! -f "$state/ssh_host_ed25519_key" ]]; then
  ssh-keygen -q -t ed25519 -N '' -f "$state/ssh_host_ed25519_key"
fi
chown root:root "$state/ssh_host_ed25519_key"
chmod 600 "$state/ssh_host_ed25519_key"
install -d -m 755 /run/sshd /etc/ssh /etc/profile.d
cat > /etc/profile.d/connectly-workspace.sh <<'EOF'
# Start SSH login shells in the project workspace, leaving command execution alone.
if [ -n "${SSH_CONNECTION:-}" ] && [ -d /workspace ]; then
  cd /workspace
fi
EOF
chmod 644 /etc/profile.d/connectly-workspace.sh
cat > /etc/ssh/ssh-access.conf <<EOF
Port ${port}
ListenAddress 0.0.0.0
HostKey ${state}/ssh_host_ed25519_key
PidFile /run/ssh-access.pid
AuthorizedKeysFile ${state}/authorized_keys
StrictModes yes
AllowUsers root
PermitRootLogin prohibit-password
PubkeyAuthentication yes
AuthenticationMethods publickey
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
UsePAM yes
AllowTcpForwarding yes
GatewayPorts no
AllowAgentForwarding no
X11Forwarding no
PermitTunnel no
PermitUserEnvironment no
PrintMotd no
Subsystem sftp internal-sftp -d /workspace
EOF
/usr/sbin/sshd -t -f /etc/ssh/ssh-access.conf
printf 'install: SSH configured on internal port %s (key authentication only)\n' "$port"
