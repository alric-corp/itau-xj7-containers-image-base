// Contrato funcional M08/M10 das imagens Go: este programa é compilado na
// variante `-dev` (com toolchain e shell) e executado na variante de runtime
// (sem toolchain, sem shell, sem Go). Só biblioteca padrão — a imagem final
// não tem gerenciador de pacotes para instalar nada.
package main

import (
	"crypto/x509"
	"encoding/json"
	"encoding/pem"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
	"time"
)

type result struct {
	Timezone bool `json:"timezone"`
	Version              string `json:"version"`
	UID                  int    `json:"uid"`
	GID                  int    `json:"gid"`
	Readonly             bool   `json:"readonly"`
	Tmpfs                bool   `json:"tmpfs"`
	WritableDirs         bool   `json:"writable_dirs"`
	BundleParse          bool   `json:"bundle_parse"`
	TLSTrusted           bool   `json:"tls_trusted"`
	TLSUntrustedRejected bool   `json:"tls_untrusted_rejected"`
}

func fail(format string, args ...any) {
	fmt.Fprintf(os.Stderr, format+"\n", args...)
	os.Exit(1)
}

func env(name string) string {
	value := os.Getenv(name)
	if value == "" {
		fail("variável de ambiente %s ausente", name)
	}
	return value
}

// A escrita na raiz precisa falhar por EROFS, não por permissão: /app
// pertence ao mesmo uid/gid que executa o processo, então uma rejeição aqui
// só pode vir do mount somente leitura.
func readonlyRoot(path string) bool {
	err := os.WriteFile(path, []byte("must fail"), 0o644)
	if err == nil {
		fail("%s aceitou escrita: raiz não está somente leitura", path)
	}
	if !errors.Is(err, syscall.EROFS) {
		fail("escrita em %s falhou por outro motivo que não EROFS: %v", path, err)
	}
	return true
}

func writable(dirs []string) bool {
	for _, dir := range dirs {
		path := filepath.Join(dir, "runtime-test-write")
		if err := os.WriteFile(path, []byte("ok"), 0o644); err != nil {
			fail("diretório gravável %s rejeitou escrita: %v", dir, err)
		}
		content, err := os.ReadFile(path)
		if err != nil || string(content) != "ok" {
			fail("leitura de volta em %s falhou: %v", path, err)
		}
		if err := os.Remove(path); err != nil {
			fail("remoção em %s falhou: %v", path, err)
		}
	}
	return true
}

// Parsing do bundle que a imagem já traz, separado da CA de teste injetada.
func bundleParses(path string) bool {
	content, err := os.ReadFile(path)
	if err != nil {
		fail("bundle de CAs da imagem ilegível: %v", err)
	}
	count := 0
	for rest := content; ; {
		var block *pem.Block
		block, rest = pem.Decode(rest)
		if block == nil {
			break
		}
		if block.Type != "CERTIFICATE" {
			continue
		}
		if _, err := x509.ParseCertificate(block.Bytes); err != nil {
			fail("certificado inválido no bundle da imagem: %v", err)
		}
		count++
	}
	if count == 0 {
		fail("bundle de CAs da imagem vazio: %s", path)
	}
	return true
}

// Confiança vem de SSL_CERT_FILE, mecanismo que o crypto/x509 lê do
// ambiente — o mesmo caminho que uma aplicação usaria para uma CA
// corporativa. Não há RootCAs customizado no cliente de propósito.
func request(url string) (int, string, error) {
	client := &http.Client{Timeout: 10 * time.Second}
	response, err := client.Get(url)
	if err != nil {
		return 0, "", err
	}
	defer response.Body.Close()
	body, err := io.ReadAll(response.Body)
	return response.StatusCode, string(body), err
}

func trusted(url string) bool {
	status, body, err := request(url)
	if err != nil {
		fail("HTTPS com CA confiável falhou: %v", err)
	}
	if status != http.StatusOK || body != "runtime-tls-ok\n" {
		fail("HTTPS com CA confiável respondeu %d %q", status, body)
	}
	return true
}

func untrustedRejected(url string) bool {
	_, _, err := request(url)
	if err == nil {
		fail("HTTPS com CA não confiável foi aceito")
	}
	// Erro de conexão ou timeout não aprova o teste negativo: só uma
	// rejeição de verificação de certificado comprova a checagem da cadeia.
	var unknownAuthority x509.UnknownAuthorityError
	var invalidCert x509.CertificateInvalidError
	var hostname x509.HostnameError
	if errors.As(err, &unknownAuthority) || errors.As(err, &invalidCert) || errors.As(err, &hostname) ||
		strings.Contains(err.Error(), "certificate") {
		return true
	}
	fail("HTTPS com CA não confiável falhou sem erro de certificado: %v", err)
	return false
}

func timezoneWorks() bool {
    zone, err := time.LoadLocation("America/Sao_Paulo")
    if err != nil { fail("timezone missing: %v", err) }
    for year, expected := range map[int]int{2026: -3*3600, 2018: -2*3600} {
        _, offset := time.Date(year, 1, 15, 12, 0, 0, 0, zone).Zone()
        if offset != expected { fail("incorrect Sao Paulo offset for %d: %d", year, offset) }
    }
    return true
}

func main() {
	expected := env("EXPECTED_RUNTIME_VERSION")
	if !strings.HasPrefix(runtime.Version(), "go"+expected) {
		fail("runtime %s não corresponde ao framework go%s", runtime.Version(), expected)
	}
	uid, gid := os.Getuid(), os.Getgid()
	if uid != 10000 || gid != 10000 {
		fail("identidade inesperada: uid=%d gid=%d", uid, gid)
	}
	dirs := strings.Split(env("WRITABLE_DIRS"), ",")
	tmpfs := false
	for _, dir := range dirs {
		if dir == "/tmp" {
			tmpfs = true
		}
	}
	if !tmpfs {
		fail("WRITABLE_DIRS precisa incluir /tmp")
	}
	output, err := json.Marshal(result{
		Timezone:             timezoneWorks(),
		Version:              strings.TrimPrefix(runtime.Version(), "go"),
		UID:                  uid,
		GID:                  gid,
		Readonly:             readonlyRoot(env("READONLY_PATH")),
		Tmpfs:                tmpfs,
		WritableDirs:         writable(dirs),
		BundleParse:          bundleParses(env("IMAGE_CA_BUNDLE")),
		TLSTrusted:           trusted(env("TLS_TRUSTED_URL")),
		TLSUntrustedRejected: untrustedRejected(env("TLS_UNTRUSTED_URL")),
	})
	if err != nil {
		fail("serialização do resultado falhou: %v", err)
	}
	fmt.Println(string(output))
}
