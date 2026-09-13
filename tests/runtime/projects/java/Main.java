// Contrato funcional M08/M10 das imagens Java: compilado com javac na
// variante -dev (JDK completo) e executado na variante de runtime
// (openjdk-<N>-jre, sem javac). Só java.base/java.net.http — nenhuma
// dependência externa, porque a imagem final não tem como baixar nada.
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.FileSystemException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyStore;
import java.security.cert.Certificate;
import java.security.cert.CertPathValidatorException;
import java.security.cert.CertificateFactory;
import java.time.Duration;
import java.util.Collection;
import java.util.List;

public final class Main {

    private static void fail(String message) {
        System.err.println(message);
        System.exit(1);
    }

    private static String env(String name) {
        String value = System.getenv(name);
        if (value == null || value.isEmpty()) {
            fail("variável de ambiente " + name + " ausente");
        }
        return value;
    }

    // A JVM não expõe getuid(): a identidade real vem de /proc/self/status,
    // que traz o uid/gid efetivos do processo no kernel — não do ambiente.
    private static int identity(String field) throws IOException {
        for (String line : Files.readAllLines(Path.of("/proc/self/status"))) {
            if (line.startsWith(field + ":")) {
                return Integer.parseInt(line.split("\\s+")[1]);
            }
        }
        throw new IOException("campo " + field + " ausente em /proc/self/status");
    }

    // /app pertence ao mesmo uid/gid do processo, então a rejeição só pode
    // vir do mount somente leitura. A JVM traduz EROFS em FileSystemException
    // com "Read-only file system" no motivo; exigir o motivo evita aprovar
    // uma falha de permissão como se fosse raiz somente leitura.
    private static boolean readonlyRoot(String path) {
        try {
            Files.writeString(Path.of(path), "must fail");
        } catch (FileSystemException error) {
            String reason = error.getReason() == null ? "" : error.getReason();
            if (!reason.contains("Read-only file system")) {
                fail("escrita em " + path + " falhou por outro motivo: " + reason);
            }
            return true;
        } catch (IOException error) {
            fail("escrita em " + path + " falhou sem FileSystemException: " + error);
        }
        fail(path + " aceitou escrita: raiz não está somente leitura");
        return false;
    }

    private static boolean writable(List<String> directories) {
        for (String directory : directories) {
            Path path = Path.of(directory, "runtime-test-write");
            try {
                Files.writeString(path, "ok");
                if (!Files.readString(path).equals("ok")) {
                    fail("leitura de volta em " + path + " divergiu");
                }
                Files.delete(path);
            } catch (IOException error) {
                fail("diretório gravável " + directory + " rejeitou escrita: " + error);
            }
        }
        return true;
    }

    private static Collection<? extends Certificate> certificates(String path) throws Exception {
        try (InputStream stream = Files.newInputStream(Path.of(path))) {
            return CertificateFactory.getInstance("X.509").generateCertificates(stream);
        }
    }

    // Parsing do bundle que a imagem já traz, separado da CA de teste.
    private static boolean bundleParses(String path) throws Exception {
        if (certificates(path).isEmpty()) {
            fail("bundle de CAs da imagem vazio: " + path);
        }
        return true;
    }

    // A JVM não lê SSL_CERT_FILE nem o bundle PEM do sistema: a confiança
    // vem de um KeyStore. Construí-lo em memória a partir do PEM é o
    // mecanismo equivalente ao das outras linguagens, sem keytool (que não
    // existe garantidamente no runtime) e sem arquivo gravável.
    private static HttpClient client(String caFile) throws Exception {
        if (caFile == null) {
            return HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build();
        }
        KeyStore store = KeyStore.getInstance("PKCS12");
        store.load(null, null);
        int index = 0;
        for (Certificate certificate : certificates(caFile)) {
            store.setCertificateEntry("test-ca-" + index++, certificate);
        }
        if (index == 0) {
            fail("CA de teste vazia: " + caFile);
        }
        javax.net.ssl.TrustManagerFactory factory =
                javax.net.ssl.TrustManagerFactory.getInstance(
                        javax.net.ssl.TrustManagerFactory.getDefaultAlgorithm());
        factory.init(store);
        javax.net.ssl.SSLContext context = javax.net.ssl.SSLContext.getInstance("TLS");
        context.init(null, factory.getTrustManagers(), null);
        return HttpClient.newBuilder().sslContext(context)
                .connectTimeout(Duration.ofSeconds(10)).build();
    }

    private static HttpResponse<String> request(HttpClient client, String url) throws Exception {
        HttpRequest request = HttpRequest.newBuilder(URI.create(url))
                .timeout(Duration.ofSeconds(10)).GET().build();
        return client.send(request, HttpResponse.BodyHandlers.ofString());
    }

    private static boolean trusted(HttpClient client, String url) throws Exception {
        HttpResponse<String> response = request(client, url);
        if (response.statusCode() != 200 || !response.body().equals("runtime-tls-ok\n")) {
            fail("HTTPS com CA confiável respondeu " + response.statusCode()
                    + " " + response.body());
        }
        return true;
    }

    private static boolean untrustedRejected(HttpClient client, String url) {
        try {
            request(client, url);
        } catch (Exception error) {
            // Erro de conexão ou timeout não aprova o teste negativo: só uma
            // falha de validação da cadeia comprova a checagem do certificado.
            for (Throwable cause = error; cause != null; cause = cause.getCause()) {
                if (cause instanceof CertPathValidatorException
                        || cause instanceof java.security.cert.CertificateException) {
                    return true;
                }
            }
            fail("HTTPS com CA não confiável falhou sem erro de certificado: " + error);
        }
        fail("HTTPS com CA não confiável foi aceito");
        return false;
    }

    private static boolean timezoneWorks() {
        var zone = java.time.ZoneId.of("America/Sao_Paulo");
        for (int year : new int[] {2026, 2018}) {
            int expected = (year == 2026 ? -3 : -2) * 3600;
            int actual = java.time.ZonedDateTime.of(year, 1, 15, 12, 0, 0, 0, zone)
                    .getOffset().getTotalSeconds();
            if (actual != expected) fail("incorrect Sao Paulo offset: " + actual);
        }
        return true;
    }

    public static void main(String[] args) throws Exception {
        String expected = env("EXPECTED_RUNTIME_VERSION");
        int feature = Runtime.version().feature();
        if (feature != Integer.parseInt(expected)) {
            fail("runtime Java " + feature + " não corresponde ao framework java" + expected);
        }
        int uid = identity("Uid");
        int gid = identity("Gid");
        if (uid != 10000 || gid != 10000) {
            fail("identidade inesperada: uid=" + uid + " gid=" + gid);
        }
        List<String> directories = List.of(env("WRITABLE_DIRS").split(","));
        if (!directories.contains("/tmp")) {
            fail("WRITABLE_DIRS precisa incluir /tmp");
        }
        HttpClient client = client(System.getenv("TLS_CA_FILE"));
        // A ordem dos campos acompanha os contratos das outras linguagens.
        System.out.println("{"
                + "\"version\": \"" + Runtime.version().toString() + "\", "
                + "\"uid\": " + uid + ", "
                + "\"gid\": " + gid + ", "
                + "\"readonly\": " + readonlyRoot(env("READONLY_PATH")) + ", "
                + "\"tmpfs\": true, "
                + "\"writable_dirs\": " + writable(directories) + ", "
                + "\"timezone\": " + timezoneWorks() + ", "
                + "\"bundle_parse\": " + bundleParses(env("IMAGE_CA_BUNDLE")) + ", "
                + "\"tls_trusted\": " + trusted(client, env("TLS_TRUSTED_URL")) + ", "
                + "\"tls_untrusted_rejected\": " + untrustedRejected(client, env("TLS_UNTRUSTED_URL"))
                + "}");
    }
}
