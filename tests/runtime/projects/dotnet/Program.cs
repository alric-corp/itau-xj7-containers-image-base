// Contrato funcional M08/M10 das imagens .NET: publicado com o SDK na
// variante -dev e executado na variante de runtime (aspnet-<N>-runtime, sem
// SDK). Só a biblioteca base — a imagem final não tem como restaurar pacote.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Net.Security;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using System.Threading.Tasks;

internal static class Program
{
    private static void Fail(string message)
    {
        Console.Error.WriteLine(message);
        Environment.Exit(1);
    }

    private static string Env(string name)
    {
        string value = Environment.GetEnvironmentVariable(name);
        if (string.IsNullOrEmpty(value))
        {
            Fail($"variável de ambiente {name} ausente");
        }
        return value;
    }

    // .NET não expõe getuid() na API pública: a identidade real vem de
    // /proc/self/status, que traz o uid/gid efetivos no kernel.
    private static int Identity(string field)
    {
        foreach (string line in File.ReadLines("/proc/self/status"))
        {
            if (line.StartsWith(field + ":", StringComparison.Ordinal))
            {
                return int.Parse(line.Split('\t', ' ', StringSplitOptions.RemoveEmptyEntries)[1]);
            }
        }
        Fail($"campo {field} ausente em /proc/self/status");
        return -1;
    }

    // /app pertence ao mesmo uid/gid do processo, então a rejeição só pode
    // vir do mount somente leitura. Exigir a mensagem de EROFS evita
    // aprovar uma falha de permissão como se fosse raiz somente leitura.
    private static bool ReadonlyRoot(string path)
    {
        try
        {
            File.WriteAllText(path, "must fail");
        }
        catch (IOException error)
        {
            if (!error.Message.Contains("Read-only file system", StringComparison.Ordinal))
            {
                Fail($"escrita em {path} falhou por outro motivo: {error.Message}");
            }
            return true;
        }
        Fail($"{path} aceitou escrita: raiz não está somente leitura");
        return false;
    }

    private static bool Writable(IEnumerable<string> directories)
    {
        foreach (string directory in directories)
        {
            string path = Path.Combine(directory, "runtime-test-write");
            try
            {
                File.WriteAllText(path, "ok");
                if (File.ReadAllText(path) != "ok")
                {
                    Fail($"leitura de volta em {path} divergiu");
                }
                File.Delete(path);
            }
            catch (Exception error) when (error is IOException || error is UnauthorizedAccessException)
            {
                Fail($"diretório gravável {directory} rejeitou escrita: {error.Message}");
            }
        }
        return true;
    }

    private static X509Certificate2Collection LoadPem(string path)
    {
        var certificates = new X509Certificate2Collection();
        certificates.ImportFromPemFile(path);
        return certificates;
    }

    // Parsing do bundle que a imagem já traz, separado da CA de teste.
    private static bool BundleParses(string path)
    {
        if (LoadPem(path).Count == 0)
        {
            Fail($"bundle de CAs da imagem vazio: {path}");
        }
        return true;
    }

    // Confiança explícita: a cadeia é validada de verdade (X509Chain), só
    // com a CA de teste como raiz. Não é um callback que aceita tudo — um
    // certificado de outra CA continua sendo rejeitado, e o nome do host
    // continua sendo conferido.
    private static HttpClient Client(string caFile)
    {
        if (caFile == null) return new HttpClient { Timeout = TimeSpan.FromSeconds(10) };
        X509Certificate2Collection testCa = LoadPem(caFile);
        if (testCa.Count == 0)
        {
            Fail($"CA de teste vazia: {caFile}");
        }
        var handler = new HttpClientHandler
        {
            ServerCertificateCustomValidationCallback = (request, certificate, chain, errors) =>
            {
                if ((errors & SslPolicyErrors.RemoteCertificateNameMismatch) != 0
                    || (errors & SslPolicyErrors.RemoteCertificateNotAvailable) != 0)
                {
                    return false;
                }
                using var custom = new X509Chain();
                custom.ChainPolicy.TrustMode = X509ChainTrustMode.CustomRootTrust;
                custom.ChainPolicy.RevocationMode = X509RevocationMode.NoCheck;
                custom.ChainPolicy.CustomTrustStore.AddRange(testCa);
                return custom.Build(certificate);
            },
        };
        return new HttpClient(handler) { Timeout = TimeSpan.FromSeconds(10) };
    }

    private static async Task<bool> TrustedAsync(HttpClient client, string url)
    {
        HttpResponseMessage response = await client.GetAsync(url).ConfigureAwait(false);
        string body = await response.Content.ReadAsStringAsync().ConfigureAwait(false);
        if ((int)response.StatusCode != 200 || body != "runtime-tls-ok\n")
        {
            Fail($"HTTPS com CA confiável respondeu {(int)response.StatusCode} {body}");
        }
        return true;
    }

    private static async Task<bool> UntrustedRejectedAsync(HttpClient client, string url)
    {
        try
        {
            await client.GetAsync(url).ConfigureAwait(false);
        }
        catch (Exception error)
        {
            // Erro de conexão ou timeout não aprova o teste negativo: só uma
            // falha de validação da cadeia comprova a checagem do certificado.
            for (Exception cause = error; cause != null; cause = cause.InnerException)
            {
                if (cause is System.Security.Authentication.AuthenticationException)
                {
                    return true;
                }
            }
            Fail($"HTTPS com CA não confiável falhou sem erro de certificado: {error}");
        }
        Fail("HTTPS com CA não confiável foi aceito");
        return false;
    }

    private static bool TimezoneWorks()
    {
        var zone = TimeZoneInfo.FindSystemTimeZoneById("America/Sao_Paulo");
        foreach (int year in new[] {2026, 2018})
        {
            var date = new DateTime(year, 1, 15, 12, 0, 0, DateTimeKind.Utc);
            if (zone.GetUtcOffset(date) != TimeSpan.FromHours(year == 2026 ? -3 : -2))
                Fail("incorrect Sao Paulo offset");
        }
        return true;
    }

    private static async Task Main()
    {
        string expected = Env("EXPECTED_RUNTIME_VERSION");
        if (Environment.Version.Major != int.Parse(expected))
        {
            Fail($"runtime .NET {Environment.Version} não corresponde ao framework dotnet{expected}");
        }
        int uid = Identity("Uid");
        int gid = Identity("Gid");
        if (uid != 10000 || gid != 10000)
        {
            Fail($"identidade inesperada: uid={uid} gid={gid}");
        }
        string[] directories = Env("WRITABLE_DIRS").Split(',');
        if (!directories.Contains("/tmp"))
        {
            Fail("WRITABLE_DIRS precisa incluir /tmp");
        }
        HttpClient client = Client(Environment.GetEnvironmentVariable("TLS_CA_FILE"));
        var result = new Dictionary<string, object>
        {
            ["version"] = Environment.Version.ToString(),
            ["uid"] = uid,
            ["gid"] = gid,
            ["readonly"] = ReadonlyRoot(Env("READONLY_PATH")),
            ["tmpfs"] = true,
            ["writable_dirs"] = Writable(directories),
            ["timezone"] = TimezoneWorks(),
            ["bundle_parse"] = BundleParses(Env("IMAGE_CA_BUNDLE")),
            ["tls_trusted"] = await TrustedAsync(client, Env("TLS_TRUSTED_URL")).ConfigureAwait(false),
            ["tls_untrusted_rejected"] =
                await UntrustedRejectedAsync(client, Env("TLS_UNTRUSTED_URL")).ConfigureAwait(false),
        };
        Console.WriteLine(JsonSerializer.Serialize(result));
    }
}
