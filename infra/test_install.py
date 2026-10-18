"""Isolated provisioning and real OpenSSH authentication checks; no live install."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import unittest


APP = Path(__file__).resolve().parents[1]


class SSHAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # OpenSSH hardcodes this privilege separation directory even when its
        # config and identity are isolated. No listener or unit is changed.
        runtime = Path("/run/sshd")
        if not runtime.exists():
            runtime.mkdir(mode=0o755)
            cls.addClassCleanup(runtime.rmdir)

    def setUp(self):
        # StrictModes rejects writable ancestors such as /tmp for authorized keys.
        self.temp = tempfile.TemporaryDirectory(prefix="ssh-access-test-", dir=APP.parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        self.config_dir = self.root / "etc-ssh"
        self.config_dir.mkdir()
        self.config = self.config_dir / "ssh-access.conf"
        self.key = self.root / "client"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "",
                        "-f", str(self.key)], check=True)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.script = (APP / "infra/install.sh").read_text()
        for original, replacement in (
            ("/workspace/.ssh-access", str(self.state)),
            ("/etc/ssh", str(self.config_dir)),
            ("/run/sshd", str(self.root / "run-sshd")),
            ("/run/ssh-access.pid", str(self.root / "sshd.pid")),
        ):
            self.script = self.script.replace(original, replacement)

    def provision(self, key=None, port=None):
        env = dict(os.environ, SSH_PUBLIC_KEY=key if key is not None else
                   self.key.with_suffix(".pub").read_text().strip(),
                   APP_INTERNAL_PORT=str(self.port if port is None else port))
        return subprocess.run(["bash", "-s"], input=self.script, text=True,
                              capture_output=True, env=env, timeout=30)

    def test_manifest_and_idempotent_install(self):
        manifest = json.loads((APP / "application.json").read_text())
        self.assertEqual(manifest["scopes"], ["project"])
        self.assertEqual(manifest["port"]["bindAddress"], "0.0.0.0")
        self.assertEqual(manifest["connection"]["user"], "root")
        first = self.provision()
        self.assertEqual(first.returncode, 0, first.stderr)
        identity = (self.state / "ssh_host_ed25519_key").read_bytes()
        second = self.provision()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(identity, (self.state / "ssh_host_ed25519_key").read_bytes())
        self.assertEqual((self.state / "authorized_keys").stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)
        effective = subprocess.check_output(
            ["/usr/sbin/sshd", "-T", "-f", str(self.config)], text=True)
        for line in ("passwordauthentication no", "kbdinteractiveauthentication no",
                     "authenticationmethods publickey", "allowusers root",
                     "allowtcpforwarding yes", "allowagentforwarding no"):
            self.assertIn(line, effective.splitlines())

    def test_rejects_invalid_keys_without_writing_state(self):
        for key in ("", "not-a-key", "ssh-ed25519 invalid-base64",
                    "command=\"id\" ssh-ed25519 AAAA", "ssh-ed25519 AAAA\nPort 22",
                    "ssh-ed25519 AAAA\rPort 22"):
            with self.subTest(key=key):
                result = self.provision(key=key)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.state.exists())

    def test_rejects_invalid_port(self):
        for port in ("0", "65536", "-1", "2222\nPermitRootLogin yes", "abc"):
            with self.subTest(port=port):
                self.assertNotEqual(self.provision(port=port).returncode, 0)
                self.assertFalse(self.state.exists())

    def test_login_and_reject_unrelated_key(self):
        result = self.provision()
        self.assertEqual(result.returncode, 0, result.stderr)
        # Test listener stays on loopback and is always terminated by cleanup.
        self.config.write_text(self.config.read_text().replace(
            "ListenAddress 0.0.0.0", "ListenAddress 127.0.0.1"))
        log = open(self.root / "server.log", "w+")
        self.addCleanup(log.close)
        server = subprocess.Popen(["/usr/sbin/sshd", "-D", "-e", "-f",
                                   str(self.config)], stderr=log)

        def stop_server():
            server.terminate()
            server.wait(timeout=10)
        self.addCleanup(stop_server)
        for _ in range(50):
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=.1):
                    break
            except OSError:
                time.sleep(.1)
        known = self.root / "known_hosts"
        host_key = (self.state / "ssh_host_ed25519_key.pub").read_text()
        known.write_text(f"[127.0.0.1]:{self.port} {host_key}")

        def connect(key):
            return subprocess.run([
                "ssh", "-F", "/dev/null", "-o", "BatchMode=yes", "-o",
                "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=yes", "-o",
                f"UserKnownHostsFile={known}", "-o", "ConnectTimeout=3", "-i",
                str(key), "-p", str(self.port), "root@127.0.0.1",
                "printf ssh-access-authenticated"], capture_output=True, text=True,
                timeout=10)

        accepted = connect(self.key)
        log.flush()
        self.assertEqual(accepted.returncode, 0,
                         accepted.stderr + (self.root / "server.log").read_text())
        self.assertEqual(accepted.stdout, "ssh-access-authenticated")
        wrong = self.root / "wrong"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "",
                        "-f", str(wrong)], check=True)
        rejected = connect(wrong)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("Permission denied", rejected.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
