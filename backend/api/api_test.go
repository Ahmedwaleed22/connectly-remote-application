package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/futrx-com/remote.futrx.com/pkg/applications"
)

func TestConnection(t *testing.T) {
	for _, tc := range []struct {
		name, reply, override string
		status, port, want    int
	}{
		{"detected", "203.0.113.8", "", 200, 5345, 200},
		{"override", "invalid", "203.0.113.9", 500, 5346, 200},
		{"private override", "203.0.113.8", "192.168.1.2", 200, 5345, 502},
		{"bad reply", "<html>error</html>", "", 200, 5345, 502},
		{"lookup failure", "203.0.113.8", "", 503, 5345, 502},
		{"unallocated", "203.0.113.8", "", 200, 0, 409},
	} {
		t.Run(tc.name, func(t *testing.T) {
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) { w.WriteHeader(tc.status); w.Write([]byte(tc.reply)) }))
			defer server.Close()
			b := New(server.Client(), server.URL)
			if err := b.Init(applications.Instance{ExternalPort: tc.port, Env: map[string]string{"SSH_PUBLIC_IP": tc.override}}); err != nil {
				t.Fatal(err)
			}
			response, err := b.Handle(applications.Request{Method: "GET", Path: "connection"})
			if err != nil || response.Status != tc.want {
				t.Fatalf("response=%+v err=%v", response, err)
			}
			if tc.want == 200 {
				var data struct {
					PublicIP        string
					Port            int
					Workspace, User string
				}
				if err := json.Unmarshal(response.Body, &data); err != nil {
					t.Fatal(err)
				}
				wantIP := tc.reply
				if tc.override != "" {
					wantIP = tc.override
				}
				if data.PublicIP != wantIP || data.Port != tc.port || data.Workspace != "/workspace" || data.User != "root" {
					t.Fatalf("wrong connection: %+v", data)
				}
			}
		})
	}
}
