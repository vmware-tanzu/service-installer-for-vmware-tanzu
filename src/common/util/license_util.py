from datetime import datetime

from flask import current_app


class LicenseUtil:
    def __init__(self):
        pass

    def check_tanzu_license(self, assigned_license):
        try:
            for license_str in assigned_license:
                if license_str.assignedLicense.name.__contains__(
                    "Tanzu Standard activation for vSphere"
                ) or license_str.assignedLicense.name.__contains__("Evaluation"):
                    properties = license_str.assignedLicense.properties
                    for prop in properties:
                        if prop.key == "expirationDate":
                            expiration_date = str(prop.value)
                            status = self.verify_expired(expiration_date)
                            if status[1]:
                                current_app.logger.error("Tanzu Standard License expiration check failed")
                                current_app.logger.error(status[0])
                                return expiration_date, False
                            return expiration_date, True
                    current_app.logger.info("Tanzu Standard Expiration is set to Never")
                    return "Never", True
            current_app.logger.error("No license found for Tanzu Standard activation for vSphere")
            return "No license found for Tanzu Standard activation for vSphere, defaulting to Trial License", True
        except Exception as e:
            current_app.logger.error("Exception occurred while validating Tanzu Standard License expiration check")
            return str(e), False

    def check_nsxt_license(self, assigned_license):
        try:
            for license_str in assigned_license:
                if license_str.assignedLicense.name.__contains__("NSX for vShield Endpoint"):
                    properties = license_str.assignedLicense.properties
                    for prop in properties:
                        if prop.key == "expirationDate":
                            expiration_date = str(prop.value)
                            status = self.verify_expired(expiration_date)
                            if status[1]:
                                current_app.logger.error("NSX License expiration check failed")
                                current_app.logger.error(status[0])
                                return expiration_date, False
                            return expiration_date, True
                    current_app.logger.info("NSX License is set to Never")
                    return "Never", True
            current_app.logger.error("No license found for: NSX for vShield Endpoint")
            return "No license found for NSX for vShield Endpoint", False
        except Exception as e:
            current_app.logger.error("ERROR: Exception occurred while validating NSX License expiration check")
            return str(e), False

    def check_vsphere_license(self, assigned_license):
        try:
            evaluation_mode = None
            expiration_date = None
            for license_str in assigned_license:
                if license_str.assignedLicense.name.__contains__("vCenter Server"):
                    properties = license_str.assignedLicense.properties
                    for prop in properties:
                        if prop.key == "expirationDate":
                            expiration_date = str(prop.value)
                            status = self.verify_expired(expiration_date)
                            if status[1]:
                                current_app.logger.error("vCenter Server Standard License expiration check failed")
                                current_app.logger.error(status[0])
                                return expiration_date, False
                            return expiration_date, True
                    current_app.logger.info("vCenter Server Standard License is set to Never")
                    return "Never", True
                elif license_str.assignedLicense.name.__contains__("Evaluation"):
                    properties = license_str.assignedLicense.properties
                    for prop in properties:
                        if prop.key == "ProductName" and prop.value.__contains__("VMware VirtualCenter Server"):
                            for exp in properties:
                                if exp.key == "expirationDate":
                                    expiration_date = str(exp.value)
                            status = self.verify_expired(expiration_date)
                            if status[1]:
                                current_app.logger.warn("vCenter Server Evaluation Mode expiration check failed")
                            else:
                                current_app.logger.info("vCenter Server Evaluation Mode license check passed")
                                evaluation_mode = expiration_date
            if evaluation_mode is not None:
                return evaluation_mode, True
            current_app.logger.error("No license found for: vCenter Server Standard License")
            return "No license found for vCenter Server Standard License", False
        except Exception as e:
            current_app.logger.error(
                "Exception occurred while validating vCenter Server Standard License expiration check"
            )
            return str(e), False

    @staticmethod
    def verify_expired(expiration_date):
        try:
            date = expiration_date[0:10]
            year = date.split("-")[0]
            month = date.split("-")[1]
            day = date.split("-")[2]

            string_date = day + "/" + month + "/" + year
            future = datetime.strptime(string_date, "%d/%m/%Y")
            present = datetime.now()
            if future.date() > present.date():
                return "Verified expiration date is ahead of current date", False
            else:
                return "Expiration date is less than current date", True
        except Exception as e:
            current_app.logger.error("Exception ocurred while verifying expiration date: " + expiration_date)
            return str(e), True
