package main

import (
	"net/http"
	"time"

	"futrx.local/catalog/applications/ssh-access/backend/api"
	"github.com/futrx-com/remote.futrx.com/pkg/applications/rpc"
)

func main() {
	rpc.Serve(api.New(&http.Client{Timeout: 5 * time.Second, Transport: &http.Transport{}}, "https://api.ipify.org"))
}
