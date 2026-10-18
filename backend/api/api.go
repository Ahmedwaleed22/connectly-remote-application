package api

import (
	"fmt"
	"io"
	"net"
	"net/http"
	"strings"

	"github.com/futrx-com/remote.futrx.com/pkg/applications"
)

type backend struct {
	client    *http.Client
	lookupURL string
	instance  applications.Instance
	router    *applications.Router
}

func New(client *http.Client, lookupURL string) applications.Backend {
	b := &backend{client: client, lookupURL: lookupURL, router: applications.NewRouter()}
	b.router.GET("connection", "Public SSH endpoint and workspace", b.connection)
	return b
}

func (b *backend) Init(instance applications.Instance) error { b.instance = instance; return nil }
func (b *backend) Describe() (applications.Descriptor, error) {
	return applications.Descriptor{APIVersion: applications.APIVersion, Routes: b.router.Routes()}, nil
}
func (b *backend) Handle(request applications.Request) (applications.Response, error) {
	return b.router.Serve(request), nil
}

func publicIPv4(value string) bool {
	ip := net.ParseIP(value)
	return ip != nil && ip.To4() != nil && ip.IsGlobalUnicast() && !ip.IsPrivate()
}

func (b *backend) publicIP() (string, error) {
	if value := strings.TrimSpace(b.instance.Env["SSH_PUBLIC_IP"]); value != "" {
		if !publicIPv4(value) {
			return "", fmt.Errorf("Public SSH IPv4 address must be a public IPv4 address")
		}
		return value, nil
	}
	response, err := b.client.Get(b.lookupURL)
	if err != nil {
		return "", fmt.Errorf("public IP lookup failed; retry or set Public SSH IPv4 address when installing Connectly")
	}
	defer response.Body.Close()
	data, err := io.ReadAll(io.LimitReader(response.Body, 65))
	value := strings.TrimSpace(string(data))
	if err != nil || response.StatusCode != http.StatusOK || !publicIPv4(value) {
		return "", fmt.Errorf("public IP lookup returned no public IPv4 address; retry or set Public SSH IPv4 address when installing Connectly")
	}
	return value, nil
}

func (b *backend) connection(applications.Request) applications.Response {
	if b.instance.ExternalPort < 1 || b.instance.ExternalPort > 65535 {
		return applications.Errorf(http.StatusConflict, "SSH host port has not been allocated")
	}
	ip, err := b.publicIP()
	if err != nil {
		return applications.Errorf(http.StatusBadGateway, "%s", err)
	}
	return applications.JSON(http.StatusOK, map[string]any{
		"publicIP": ip, "port": b.instance.ExternalPort, "user": "root", "workspace": "/workspace",
	})
}
