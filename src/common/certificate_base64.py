import ssl
import base64
import os


def getBase64CertWriteToFile(host, port):
    os.system("rm -rf cert.txt")
    cert = ssl.get_server_certificate((host, port))
    base64_bytes = base64.b64encode(cert.encode("utf-8"))
    encodedStr = str(base64_bytes, "utf-8")
    with open('cert.txt', 'w') as f:
        f.write(encodedStr)


def repoAdd(repo, port):
    cert = ssl.get_server_certificate((repo, port))
    with open("/etc/pki/tls/certs/ca-bundle.crt", "r") as stream:
        if not stream.read().__contains__(cert):
            with open("/etc/pki/tls/certs/ca-bundle.crt", "a") as streamx:
                streamx.write(cert)
