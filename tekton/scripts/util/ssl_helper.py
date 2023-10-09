#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import base64
import hashlib
import ssl
from enum import Enum


class Encryption(str, Enum):
    SHA1 = "sha1"
    SHA256 = "sha256"
    MD5 = "md5"


def get_pem_cert(address, port=443):
    try:
        cert = ssl.get_server_certificate((address, port))
    except Exception as ex:
        raise Exception(f"Failed to connect to address: {address}. Exception: {ex}")
    return cert


def get_base64_cert(address, port=443) -> str:
    cert = get_pem_cert(address, port)
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
