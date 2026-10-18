"""Test Go source and the ZIP through a local Remote checkout's generated builder."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

from package import build_package


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--remote", type=Path, required=True)
parser.add_argument("--go", default=shutil.which("go") or "/usr/local/go/bin/go")
args = parser.parse_args()
app = Path(__file__).resolve().parents[1]
remote = args.remote.resolve()

with tempfile.TemporaryDirectory(prefix="connectly-tests-") as directory:
    root = Path(directory)
    source = root / "source"
    shutil.copytree(app / "backend", source)
    (source / "go.mod").write_text(
        "module futrx.local/catalog/applications/ssh-access/backend\n\ngo 1.25.13\n"
        "require github.com/futrx-com/remote.futrx.com v0.0.0\n"
        f"replace github.com/futrx-com/remote.futrx.com => {remote / 'backend'}\n"
        f"replace futrx.local/catalog => {remote}\n")
    subprocess.run([args.go, "test", "-mod=mod", "./..."], cwd=source, check=True)
    subprocess.run([args.go, "vet", "-mod=mod", "./..."], cwd=source, check=True)
    import json
    version = json.loads((app / "application.json").read_text())["version"]
    archive = build_package(app, root / "package", f"v{version}")
    # The harness must be within Remote's module to import its internal host.
    with tempfile.TemporaryDirectory(prefix="connectly-check-", dir=remote / "backend") as check:
        harness = Path(check) / "main.go"
        harness.write_text('''package main
import (
 "context"
 "fmt"
 "os"
 "encoding/json"
 catalog "github.com/futrx-com/remote.futrx.com/internal/integration/containers/applications"
 host "github.com/futrx-com/remote.futrx.com/internal/integration/applications"
 svc "github.com/futrx-com/remote.futrx.com/internal/service/applications"
 sdk "github.com/futrx-com/remote.futrx.com/pkg/applications"
)
func must(e error) {if e != nil {panic(e)}}
func main() {
 dir,e:=os.MkdirTemp("","connectly-host-"); must(e); defer os.RemoveAll(dir)
 store,e:=catalog.NewPackageStore(dir+"/packages"); must(e)
 registry,e:=catalog.NewRegistry(catalog.EmbeddedCatalog(),store); must(e)
 data,e:=os.ReadFile(os.Args[1]); must(e)
 _,e=registry.AddPackage(svc.PackageUpload{Filename:"connectly.zip",Data:data}); must(e)
 h:=host.New(dir+"/host",registry,host.Options{GoTool:os.Args[2]}); defer h.Shutdown()
 instance:=sdk.Instance{ID:"connectly-test",ApplicationID:"ssh-access",Scope:"project",ProjectID:"test",ExternalPort:5345,Env:map[string]string{"SSH_PUBLIC_IP":"203.0.113.8"}}
 _,e=h.Ensure(context.Background(),instance); must(e)
 reply,e:=h.Call(context.Background(),instance,sdk.Request{Method:"GET",Path:"connection"}); must(e)
 var value struct {PublicIP string; Port int; Workspace string}
 must(json.Unmarshal(reply.Body,&value))
 if reply.Status!=200 || value.PublicIP!="203.0.113.8" || value.Port!=5345 || value.Workspace!="/workspace" {panic(string(reply.Body))}
 fmt.Println("ZIP accepted; Remote generated-module builder and real backend RPC passed")
}
''')
        subprocess.run([args.go, "run", str(harness), str(archive), args.go],
                       cwd=remote / "backend", check=True)
