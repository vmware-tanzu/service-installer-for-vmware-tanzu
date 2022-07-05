# Unfortunately, coredns in Kind will always forward DNS queries to whatever nameservers are in
# /etc/resolv.conf. This is a problem if we're using custom DNS servers that are not in the
# /etc/resolv.conf in our appliance.
#
# This helper is a shim that enables and disables modifying /etc/resolv.conf. 
import os

def addNameserverToResolvConf(dns_servers_csv=None):
    """
    Adds a nameserver to /etc/resolv.conf when provided with a list of comma-separated
    DNS servers.
    """
    if dns_servers_csv is None: return

    dns_servers = dns_servers_csv.replace(',', ' ')
    restoreOriginalEtcResolvConfIfFound()
    backupResolvConf()
    os.system(f"sed -Ei 's/nameserver (.*)/nameserver {dns_servers}\\nnameserver \\1/' /etc/resolv.conf")

def removeNameserversFromResolvConf():
    restoreResolvConf()

def restoreOriginalEtcResolvConfIfFound():
    os.system("test -f /etc/resolv.conf.bak && mv /etc/resolv.conf.bak /etc/resolv.conf")
   
def backupResolvConf():
    os.system("cp /etc/resolv.conf /etc/resolv.conf.bak")

def restoreResolvConf():
    os.system("mv /etc/resolv.conf.bak /etc/resolv.conf")
