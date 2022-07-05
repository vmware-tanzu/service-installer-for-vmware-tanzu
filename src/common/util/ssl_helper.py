import base64
import hashlib
import ssl
import dns.resolver
from enum import Enum


class Encryption(str, Enum):
    SHA1 = "sha1"
    SHA256 = "sha256"
    MD5 = "md5"

def resolve_with_custom_dns_server(address, dns_servers_csv):
    resolver = dns.resolver.Resolver()
    for dns_server in dns_servers_csv.split(','):
        if dns_server not in resolver.nameservers:
            resolver.nameservers.insert(0, dns_server)
    answer = resolver.query(address)
    return answer[0].to_text()

def get_pem_cert(address, port=443, dns_servers_csv=None):
    try:
        ip = address
        if dns_servers_csv is not None: 
            ip = resolve_with_custom_dns_server(address, dns_servers_csv)
        cert = ssl.get_server_certificate((ip, port))
    except Exception as ex:
        raise Exception(f"Failed to connect to address: {address}. Exception: {ex}")
    return cert


def get_base64_cert(address, port=443, dns_servers_csv=None) -> str:
    print("in get_base64_cert")
    cert = get_pem_cert(address, port, dns_servers_csv)
    base64_bytes = base64.b64encode(cert.encode("utf-8"))
    return str(base64_bytes, "utf-8")


def get_thumbprint(address, port=443, encryption: Encryption = Encryption.SHA1):
    cert = get_pem_cert(address, port)
    der_cert_bin = ssl.PEM_cert_to_DER_cert(cert)

    if encryption == Encryption.SHA1:
        thumbprint = hashlib.sha1(der_cert_bin).hexdigest()
    elif encryption == Encryption.SHA256:
        thumbprint = hashlib.sha256(der_cert_bin).hexdigest()
    elif encryption == Encryption.MD5:
        thumbprint = hashlib.md5(der_cert_bin).hexdigest()
    else:
        return der_cert_bin
    return thumbprint


def get_colon_formatted_thumbprint(thumbprint: str) -> str:
    thumbprint.upper()
    return ':'.join([thumbprint[i:i + 2] for i in range(0, len(thumbprint), 2)])


def decode_from_b64(text: str) -> str:
    base64_bytes = text.encode('ascii')
    enc_bytes = base64.b64decode(base64_bytes)
    return enc_bytes.decode('ascii').rstrip("\n")
