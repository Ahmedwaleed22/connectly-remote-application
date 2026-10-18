import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from package import build_package


class PackageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "source"
        (self.root / "infra").mkdir(parents=True)
        (self.root / "application.json").write_text(json.dumps({"version": "0.1.0"}))
        (self.root / "README.md").write_text("SSH Access")
        (self.root / "LICENSE").write_text("License text")
        (self.root / "infra/install.sh").write_text("#!/bin/bash\n")
        (self.root / "infra/test_install.py").write_text("development-only")
        self.output = Path(temporary.name) / "output"

    def test_installable_zip_has_only_runtime_files(self):
        archive = build_package(self.root, self.output, "v0.1.0")
        self.assertEqual(archive.name, "ssh-access-0.1.0.zip")
        with zipfile.ZipFile(archive) as package:
            self.assertIsNone(package.testzip())
            self.assertEqual(set(package.namelist()),
                             {"README.md", "LICENSE", "application.json", "infra/install.sh"})
            self.assertEqual(package.read("LICENSE"), b"License text")
            self.assertEqual(json.loads(package.read("application.json"))["version"],
                             "0.1.0")

    def test_mismatched_tag_produces_no_archive(self):
        with self.assertRaisesRegex(ValueError, "must match"):
            build_package(self.root, self.output, "v0.2.0")
        self.assertFalse(self.output.exists())

    def test_missing_installer_produces_no_archive(self):
        (self.root / "infra/install.sh").unlink()
        with self.assertRaisesRegex(ValueError, "missing regular"):
            build_package(self.root, self.output, "v0.1.0")
        self.assertFalse(self.output.exists())

    def test_missing_license_produces_no_archive(self):
        (self.root / "LICENSE").unlink()
        with self.assertRaisesRegex(ValueError, "missing regular.*LICENSE"):
            build_package(self.root, self.output, "v0.1.0")
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
