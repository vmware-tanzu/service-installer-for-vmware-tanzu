import argparse
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from prettytable import PrettyTable
from tenable.sc import TenableSC

nessus_url = "sc2-vuln-scvsecr.infra.vmware.com"
username = os.getenv("nessus_user")
password = os.getenv("nessus_password")

policy_required = "vSECR-Recommended"
scans_zone = "vSECR"
repo_name = "vSECR"
cred_name = "sivt_cli_cred"

emails = ["ashrivastav@vmware.com", "tshakun@vmware.com", "josunil@vmware.com", "sunilsh@vmware.com"]
rp_list = []


class LibNessus:
    def __init__(self, scan_name, ip, ssh_username=None, ssh_password=None, creds_name=None):
        self.url = nessus_url
        self.user_name = username
        self.password = password
        self.scan_name = scan_name
        self.host_machine = ip
        self.host_name = ssh_username
        self.host_password = ssh_password
        self.cred_name = creds_name

    def login_nessus(self):
        nessus_obj = TenableSC(nessus_url)
        nessus_obj.login(username=self.user_name, password=self.password)
        return nessus_obj

    @property
    def get_active_scans(self):
        nessus_obj = self.login_nessus()
        scan_list = nessus_obj.scans.list()
        nessus_obj.logout()
        return scan_list

    @property
    def get_active_credentials(self):
        nessus_obj = self.login_nessus()
        cred_list = nessus_obj.credentials.list()
        nessus_obj.logout()
        return cred_list

    def get_repository_id(self, repository_name=repo_name):
        nessus_obj = self.login_nessus()
        repo_resp = nessus_obj.repositories.list()
        nessus_obj.logout()
        for repo_id in repo_resp:
            if repo_id["name"] == repository_name:
                return repo_id["id"]

    def get_scans_zone_id(self, scans_zones=scans_zone):
        nessus_obj = self.login_nessus()
        scans_zone_resp = nessus_obj.scan_zones.list()
        nessus_obj.logout()
        for scans_id in scans_zone_resp:
            if scans_id["name"] == scans_zones:
                return scans_id["id"]

    def get_policy_id(self, policy_name=policy_required):
        nessus_obj = self.login_nessus()
        policy_resp = nessus_obj.policies.list()
        nessus_obj.logout()
        for k in policy_resp["usable"]:
            if k["name"] == policy_name:
                return k["id"]

    def get_cred_id(self, credentials):
        nessus_obj = self.login_nessus()
        cred_resp = nessus_obj.credentials.list()
        nessus_obj.logout()
        for k in cred_resp["usable"]:
            if k["name"] == credentials:
                return k["id"]

    def get_id_from_scans_name(self):
        for k in self.get_active_scans["usable"]:
            if k["name"] == self.scan_name.strip():
                return k["id"]
            elif k["name"] == self.scan_name.strip() + "_" + str(self.host_machine).strip():
                return k["id"]

    def generate_cred(self):
        if self.host_name == "root" and self.host_password == "VMware1!":
            return self.get_cred_id(cred_name)
        else:
            nessus_obj = self.login_nessus()
            creds_name = self.scan_name + "_cred_" + self.host_machine
            cred_id = self.get_cred_id(creds_name)
            if cred_id:
                nessus_obj.credentials.delete(cred_id)
                time.sleep(30)
            creds = nessus_obj.credentials.create(
                creds_name, "ssh", "password", username=self.host_name, password=self.host_password
            )
            nessus_obj.logout()
            return creds.get("id")

    def get_scans_run_status(self, launch_id):
        nessus_obj = self.login_nessus()
        status = nessus_obj.scan_instances.details(launch_id, fields=["name", "status"])
        nessus_obj.logout()
        return status["status"]

    def get_vuln_with_severity(self, severity, launch_id):
        nessus_obj = self.login_nessus()
        vul_list = nessus_obj.analysis.vulns(("severity", "=", str(severity)), scan_id=str(launch_id))
        nessus_obj.logout()
        return vul_list

    def create_launch_scans(self):
        nessus_obj = self.login_nessus()
        scans_ids = self.get_id_from_scans_name()
        if not scans_ids:
            cred = self.generate_cred()
            resp = nessus_obj.scans.create(
                name=self.scan_name.strip() + "_" + str(self.host_machine).strip(),
                repo=self.get_repository_id(),
                policy_id=self.get_policy_id(),
                targets=[self.host_machine],
                scan_zone=self.get_scans_zone_id(),
                creds=[cred],
                email_complete=True,
            )
            scans_ids = resp["id"]
            resp_launch = nessus_obj.scans.launch(scans_ids)
        else:
            resp_launch = nessus_obj.scans.launch(scans_ids)

        print("scan_id   -> : " + str(scans_ids))
        print("launch_id -> : " + str(resp_launch["scanResult"]["id"]))

        nessus_obj.logout()

        scan = self.get_scans_run_status(resp_launch["scanResult"]["id"])

        while scan != "Completed":
            time.sleep(180)
            scan = self.get_scans_run_status(resp_launch["scanResult"]["id"])
            if scan == "Error":
                break
        scan = self.get_scans_run_status(resp_launch["scanResult"]["id"])
        if scan == "Completed":
            nessus_obj = self.login_nessus()
            html_table = PrettyTable(["S.NO", "pluginID", "severity", "pluginInfo"])
            for index_one, vuln in enumerate(
                nessus_obj.analysis.vulns(("severity", "=", "4"), scan_id=resp_launch["scanResult"]["id"])
            ):
                self.get_nessus_report(html_table, index_one, vuln)
            for index_two, vuln in enumerate(
                nessus_obj.analysis.vulns(("severity", "=", "3"), scan_id=resp_launch["scanResult"]["id"])
            ):
                self.get_nessus_report(html_table, index_two, vuln)
            data = html_table.get_html_string()
            nessus_obj.logout()
            if len(data) <= 137:
                data = "There are no critical and high issues for host machine " + self.host_machine + ".\n"
            self.send_email(data, self.host_machine)

    @staticmethod
    def get_nessus_report(html_table, index, json_dict):
        html_table.add_row([index + 1, json_dict["pluginID"], json_dict["severity"]["name"], json_dict["pluginInfo"]])
        b = {
            "pluginID": json_dict["pluginID"],
            "severity": json_dict["severity"]["name"],
            "pluginInfo": json_dict["pluginInfo"],
        }
        rp_list.append(b)

    @staticmethod
    def send_email(data, ip):
        from_addr = "svc.sivt-sec-scan@vmware.com"
        to_addr = emails
        if isinstance(to_addr, list):
            to_addr = ", ".join(to_addr)
        html = """\
            <html>
                <head>
                <style>
                    table, th, td {
                        border: 1px solid black;
                        border-collapse: collapse;
                    }
                    th, td {
                        padding: 5px;
                        text-align: left;
                    }
                </style>
                </head>
            <body>
            <p>Hi All,<br>
               <br>
               Please find the nessus scan run report.<br>
               <br>
               %s
               <br>
               <br>
               Regards,<br>
               Team SIVT.<br>
            </p>
            </body>
            </html>
            """ % (
            data
        )

        part = MIMEText(html, "html")
        msg = MIMEMultipart("alternative")
        msg["From"] = from_addr
        msg["To"] = to_addr
        msg["Subject"] = "Automated Nessus Report for SIVT ran on %s " % ip
        msg.attach(part)
        debug = False
        if debug:
            print(msg.as_string())
        else:
            server = smtplib.SMTP("smtp.vmware.com")
            text = msg.as_string()
            server.sendmail(from_addr, to_addr, text)
            server.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", type=str, required=True)
    parser.add_argument("--ip", type=str, required=True)
    parser.add_argument("--sshU", type=str, required=False)
    parser.add_argument("--sshP", type=str, required=False)
    parser.add_argument("--cred", type=str, required=False)
    args, unknown = parser.parse_known_args()
    sc_name = args.scan
    target_ip = args.ip
    sshUsername = args.sshU
    sshPassword = args.sshP
    cred = args.cred
    nessus_instance = LibNessus(
        scan_name=sc_name, ip=target_ip, ssh_username=sshUsername, ssh_password=sshPassword, creds_name=cred
    )
    nessus_instance.create_launch_scans()
