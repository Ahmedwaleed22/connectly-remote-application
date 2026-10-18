"""Build the installable release ZIP without repository or development files."""
import argparse
import json
from pathlib import Path
import re
import zipfile


def build_package(root, output_dir, tag):
    manifest = json.loads((root / "application.json").read_text())
    version = manifest["version"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("release version must have the form 0.1.0")
    if tag != f"v{version}":
        raise ValueError(f"tag {tag!r} must match application.json version v{version}")
    files = ["README.md", "LICENSE", "application.json", "infra/install.sh"]
    for directory, extensions in (("backend", (".go",)), ("ui", (".js", ".css"))):
        files.extend(str(path.relative_to(root)) for path in sorted((root / directory).rglob("*"))
                     if path.is_file() and path.suffix in extensions and not path.name.endswith("_test.go"))
    for name in files:
        if not (root / name).is_file() or (root / name).is_symlink():
            raise ValueError(f"missing regular package file: {name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"connectly-{version}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
        for name in files:
            package.write(root / name, name)
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(build_package(Path(__file__).resolve().parents[1],
                            args.output_dir, args.tag))
    except ValueError as error:
        parser.exit(1, f"package: {error}\n")
