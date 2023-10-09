# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import atexit
import hashlib
import socket
import ssl
import time

import polling2
from flask import current_app, jsonify
from pyVim import connect
from pyVmomi import vim


class VCenterSSLOperations:
    def __init__(
        self,
        vcenter_host,
        vcenter_username,
        vcenter_password,
        cluster_name=None,
        data_center=None,
        govc_operations=None,
    ):
        """ """
        self.vcenter_host = vcenter_host
        self.vcenter_username = vcenter_username
        self.vcenter_password = vcenter_password
        self.cluster_name = cluster_name
        self.data_center = data_center
        self.path_to_resource = f"/{self.data_center}/host/{self.cluster_name}/"
        self.vcenter_connection = self.connect_to_vcenter()
        self.data_center_object = self.get_data_center(name=self.data_center)
        self.govc_operations = govc_operations

    def connect_to_vcenter(self):
        """
        connect and get vcenter object for further uses
        """
        try:
            connector = connect.SmartConnectNoSSL(
                host=self.vcenter_host, user=self.vcenter_username, pwd=self.vcenter_password
            )
            content = connector.RetrieveContent()
            return content
        except Exception as e:
            atexit.register(connect.Disconnect, connector)
            raise AssertionError("Operation failed " + str(e))

    def iterate_vcenter_objects(self, view_object):
        """
        during listing resource pool, datastore and folder we need to loop entire vcenter objects to find out
        common loop to get all handle
        :param view_object: object to check
        :returns : absolute folder/object name
        """
        v_object = view_object.name
        full_object_name = None
        if v_object:
            full_object_name = v_object
            object_parent = view_object.parent
            while (
                object_parent is not None
                and object_parent.name is not None
                and object_parent != self.vcenter_connection.rootFolder
            ):
                full_object_name = object_parent.name + "/" + full_object_name
                try:
                    object_parent = object_parent.parent
                except BaseException:
                    break
            full_object_name = "/" + full_object_name
        return full_object_name

    def get_datastore(self, data_center_name, name=None):
        """
        get datastore with passed name
        :param data_center_name: name of the data center to search for
        :param name: name of the datastore
        :returns : if name is passed then return else all datastore from vcenter
        """
        view_manager = self.vcenter_connection.viewManager
        data_center = self.get_data_center(data_center_name)
        container = view_manager.CreateContainerView(data_center, [vim.Datastore], True)
        try:
            h_name = []
            if container is not None:
                for host in container.view:
                    folder_name = self.iterate_vcenter_objects(view_object=host)
                    if folder_name:
                        if name:
                            if str(folder_name).endswith(name):
                                content = self.vcenter_connection.RetrieveContent()
                                return content.searchIndex.FindByInventoryPath(folder_name)
                        first_rp = folder_name[folder_name.find("/datastore") + 11 :]
                        if first_rp:
                            h_name.append(first_rp.strip("/"))
            return h_name
        finally:
            container.Destroy()

    def get_data_center(self, name=None):
        """
        find data center object from vcenter using VCENTER SSL connection.
        :param name: data center name
        :returns: find data center object from vcenter and if none is provided then send all datacenter's
        """
        container = self.vcenter_connection.viewManager.CreateContainerView(
            self.vcenter_connection.rootFolder, [vim.Datacenter], True
        )
        if name is not None:
            try:
                return self.vcenter_connection.searchIndex.FindByInventoryPath("/" + name)
            finally:
                container.Destroy()
        else:
            # if name is not given then list all data center's in VCENTER
            dc_name = []
            try:
                for host in container.view:
                    folder_name = self.iterate_vcenter_objects(view_object=host)
                    if folder_name:
                        first_dc = folder_name.strip("/")
                        if first_dc:
                            dc_name.append(first_dc)
                if dc_name:
                    return dc_name
                else:
                    current_app.logger.info("No datacenter found")
                    return None
            finally:
                container.Destroy()

    def vcenter_version(self):
        """
        returns vcenter version using vcenter connection
        """
        return self.vcenter_connection.about.version

    def verify_vcenter_version(self, version):
        """
        verify vcenter version with version name passed and return True/False
        """
        vc_version = self.vcenter_version()
        if vc_version.startswith(version):
            return True
        else:
            return False

    @staticmethod
    def resource_pool_allocation():
        """
        resource pool allocation data for resource pool creation
        :returns: defaults data for pool creation
        """
        resource_pool_allocation = vim.ResourceAllocationInfo()
        sharesInfo = vim.SharesInfo(level="normal")

        resource_pool_allocation.reservation = 0
        resource_pool_allocation.expandableReservation = True
        resource_pool_allocation.shares = sharesInfo
        resource_pool_allocation.limit = -1

        return resource_pool_allocation

    def create_folder(self, folder_name):
        """
        creates a folder in vcenter
        :param folder_name: folder name to be created in vcenter
        :returns: returns SUCCESS if created else None
        """
        try:
            dest_folder = self.get_vcenter_object([vim.Folder], folder_name)
            if dest_folder is None:
                self.data_center_object.vmFolder.CreateFolder(folder_name)
                return "SUCCESS"
            else:
                return "SUCCESS"
        except Exception as e:
            atexit.register(connect.Disconnect, self.vcenter_connection)
            raise AssertionError("Operation failed " + str(e))

    def get_vcenter_object(self, vim_type, name, folder=None):
        """
        Return an object by name, if name is None the
        :param vim_type:
        :param name:
        :param folder: folder to search for
        first found object is returned
        """
        obj = None
        # if folder is specified then search from folder
        if folder:
            container = self.vcenter_connection.viewManager.CreateContainerView(self.get_folder(folder), vim_type, True)
        else:
            container = self.vcenter_connection.viewManager.CreateContainerView(
                self.vcenter_connection.rootFolder, vim_type, True
            )
        if container is not None:
            for host in container.view:
                folder_name = self.iterate_vcenter_objects(view_object=host)
                if name:
                    if str(folder_name).endswith(name):
                        return self.vcenter_connection.searchIndex.FindByInventoryPath(folder_name)
                else:
                    return self.vcenter_connection.searchIndex.FindByInventoryPath(folder_name)

        return obj

    def create_resource_pool(self, name, parent_resource_pool):
        """
        create resource pool along with parent resource pool in vcenter
         :returns: returns SUCCESS if created else None
        """
        create = False
        try:
            cluster = self.get_vcenter_object([vim.ClusterComputeResource], self.cluster_name)
            resource_pool = self.get_vcenter_object([vim.ResourcePool], name)
            if resource_pool is None:
                create = True
            else:
                current_app.logger.info(f"Resource pool {name} is already present in cluster - {self.cluster_name}")
                current_app.logger.info("Checking if it's present in right path...")
                if parent_resource_pool:
                    path = self.path_to_resource + "Resources/" + parent_resource_pool + "/" + name
                else:
                    path = self.path_to_resource + "Resources/" + name
                obj = self.vcenter_connection.searchIndex.FindByInventoryPath(path)
                if obj is None:
                    create = True
            if create:
                # default config spec for Resource pool creation
                config_spec = vim.ResourceConfigSpec()
                config_spec.cpuAllocation = VCenterSSLOperations.resource_pool_allocation()
                config_spec.memoryAllocation = VCenterSSLOperations.resource_pool_allocation()
                # if parent resource pool available
                if parent_resource_pool:
                    path = self.path_to_resource + "/Resources/" + parent_resource_pool
                    resource_pool_obj = self.vcenter_connection.searchIndex.FindByInventoryPath(path)
                    if not resource_pool_obj:
                        return None
                    config_spec.entity = resource_pool_obj
                    resource_pool_obj.CreateResourcePool(name, config_spec)
                else:
                    config_spec.entity = cluster
                    cluster.resourcePool.CreateResourcePool(name, config_spec)
                return "SUCCESS"
            else:
                return None
        except Exception as e:
            atexit.register(connect.Disconnect, self.vcenter_connection)
            raise AssertionError("Operation failed " + str(e))

    def create_resource_folder_and_wait(self, resource_pool_name, folder_name, parent_resource_pool):
        """
        create resource pool and folder by calling sub-sequent methods and wait for its creation
        :param resource_pool_name: name of the resource pool to get created
        :param folder_name: name of the folder name to gets created
        :param parent_resource_pool: name of the folder name to if not gets created
        """
        try:
            is_created = self.create_resource_pool(resource_pool_name, parent_resource_pool)
            if is_created is not None:
                current_app.logger.info("Created resource pool " + resource_pool_name)
        except Exception as e:
            current_app.logger.error("Failed to create resource pool " + str(e))
            d = {"responseType": "ERROR", "msg": "Failed to create resource pool " + str(e), "STATUS_CODE": 500}
            return jsonify(d), 500

        try:
            is_created = self.create_folder(folder_name=folder_name)
            if is_created is not None:
                current_app.logger.info("Created folder " + folder_name)

        except Exception as e:
            current_app.logger.error("Failed to create folder " + str(e))
            d = {"responseType": "ERROR", "msg": "Failed to create folder " + str(e), "STATUS_CODE": 500}
            return jsonify(d), 500
        find = self.govc_operations.validate_folder_and_resources_available(
            folder=folder_name, resources=resource_pool_name, parent_resource_pool=parent_resource_pool
        )
        if not find:
            current_app.logger.error("Failed to find folder and resources")
            error_msg = (
                f"Failed to create resource pool {resource_pool_name}. Please check if {resource_pool_name}"
                f" is already present in {self.cluster_name} and delete it before initiating deployment"
            )
            current_app.logger.error(error_msg)
            d = {"responseType": "ERROR", "msg": error_msg, "STATUS_CODE": 500}
            return jsonify(d), 500
        d = {"responseType": "ERROR", "msg": "Created resources and  folder", "STATUS_CODE": 200}
        return jsonify(d), 200

    def get_vcenter_thumb_print(self):
        """
        fetch the thumbprint from vcenter
        :returns: thumbprint if found else 500
        """
        current_app.logger.info("Fetching VC thumbprint")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        wrapped_socket = ssl.wrap_socket(sock)
        try:
            wrapped_socket.connect((self.vcenter_host, 443))
        except Exception:
            current_app.logger.error("vCenter connection failed")
            return 500
        der_cert_bin = wrapped_socket.getpeercert(True)
        # Thumbprint
        thumb_sha1 = hashlib.sha1(der_cert_bin).hexdigest()
        wrapped_socket.close()
        if thumb_sha1:
            thumb_sha1 = thumb_sha1.upper()
            thumb_sha1 = ":".join(thumb_sha1[i : i + 2] for i in range(0, len(thumb_sha1), 2))
            current_app.logger.info("SHA1 : " + thumb_sha1)
            return thumb_sha1
        else:
            current_app.logger.error("Failed to obtain VC SHA1")
            return 500

    def get_network(self, network_name=None):
        """
        search and get the network object from vCenter
        :param network_name: name of the network to search for
        :returns: returns the network object if name is found else return all network objects
        """
        networks = self.data_center_object.networkFolder.childEntity
        if network_name is not None:
            for network in networks:
                if network.name == network_name:
                    return network
                elif hasattr(network, "childEntity"):
                    ports = network.childEntity
                    for item in ports:
                        if item.name == network_name:
                            return item
            raise Exception("Failed to find port named %s" % network_name)
        else:
            network_list = []
            try:
                for network in networks:
                    if hasattr(network, "childEntity"):
                        ports = network.childEntity
                        for item in ports:
                            network_list.append(item.name)
                    else:
                        network_list.append(network.name)
                return network_list
            except Exception as e:
                raise Exception(f"Encountered errors {e} while fetching networks {self.data_center.name}")

    def get_dvs_port_group_id(self, network_name):
        """
        fetch DvS group id of passed network.
        :param network_name: name the network to find DVS port group
        :return: port group id of the network if found else None
        """
        try:
            network = self.get_network(network_name)
            switch = network.config.distributedVirtualSwitch
            for port_group in switch.portgroup:
                if port_group.name == network_name:
                    return port_group.config.key
            return None
        except Exception as e:
            current_app.logger.error(str(e))
            return None

    def get_folder(self, folder_name):
        """
        Get a resource folder from vcenter with passed name
        :param folder_name: name of the folder to search for
        :returns: returns folder object if found else raise exception
        """
        view_manager = self.vcenter_connection.viewManager
        data_center = self.get_data_center(self.data_center)
        container_view = view_manager.CreateContainerView(data_center, [vim.Folder], True)
        try:
            for folder in container_view.view:
                if folder.name == folder_name:
                    return folder
        finally:
            container_view.Destroy()
        raise Exception("Failed to find resource pool %s in datacenter %s" % (folder_name, self.data_center))

    @staticmethod
    def wait_for_task(task, action_name="job", hide_result=False):
        """
        Waits and provides updates on a vSphere task
        """

        while task.info.state == vim.TaskInfo.State.running:
            time.sleep(2)

        if task.info.state == vim.TaskInfo.State.success:
            if task.info.result is not None and not hide_result:
                current_app.logger.info("%s completed successfully, result: %s" % (action_name, task.info.result))
            else:
                current_app.logger.info("%s completed successfully." % action_name)
        else:
            current_app.logger.info("%s did not complete successfully: %s" % (action_name, task.info.error))
            raise task.info.error

        return task.info.result

    def power_on_vm_if_off(self, vm):
        """
        power on the VM
        :param vm: VM object
        """
        if vm.runtime.powerState == "poweredOff":
            current_app.logger.info("Vm is in Power off state turning it on")
            try:
                task = vm.PowerOn()
                self.wait_for_task(task, action_name="power-on")
            except Exception as e:
                raise AssertionError("Failed to power on the vm " + str(e))
            try:
                polling2.poll(lambda: vm.guest.ipAddress is not None, timeout=300, step=1)
                return True
            except polling2.TimeoutException:
                # if object not found return False
                return False
        return True

    def get_mac_addresses(self, vm_name):
        """
        power on the VM and get mac address of the VM
        """

        vm = self.get_vcenter_object([vim.VirtualMachine], vm_name)
        if vm is None:
            return None
        if not self.power_on_vm_if_off(vm):
            raise AssertionError("Failed to power on vm " + vm_name)
        if vm.guest.ipAddress is None:
            raise AssertionError("Failed to get ip address of vm " + vm_name)
        hardware = vm.config.hardware.device
        list_of_mac = []
        for h in hardware:
            if isinstance(h, vim.vm.device.VirtualEthernetCard):
                list_of_mac.append(h.macAddress)
        return list_of_mac

    def get_ip_address(self, vm_name):
        """
        power on the VM and get IP address of the VM
        """
        vm = self.get_vcenter_object([vim.VirtualMachine], vm_name)
        if vm is None:
            return None
        if not self.power_on_vm_if_off(vm):
            raise AssertionError("Failed to power on vm " + vm_name)
        if vm.guest.ipAddress is None:
            raise AssertionError("Failed to get ip address of vm " + vm_name)
        return vm.guest.ipAddress

    def destroy_vm(self, folder, vm_name):
        """
        destroy VM from vCenter with passed name
        :param folder: folder name to look in to for vm destroy
        :param vm_name: VM name to destroy
        :return: None if failed to destroy
        """
        try:
            vm = self.get_vcenter_object([vim.VirtualMachine], vm_name, folder=folder)
            if vm is None:
                current_app.logger.info(f"Unable to locate VirtualMachine. Arguments given: {vm_name}")
                return None
            # while VM:
            if format(vm.runtime.powerState) == "poweredOn":
                current_app.logger.info("Attempting to power off {0}".format(vm_name))
                task = vm.PowerOffVM_Task()
                VCenterSSLOperations.wait_for_task(task, action_name="power-off")
                current_app.logger.info("{0}".format(task.info.state))

            current_app.logger.info("Destroying VM from vSphere.")
            task = vm.Destroy_Task()
            VCenterSSLOperations.wait_for_task(task, action_name="power-off")
            current_app.logger.info(f"{vm_name} destroyed.")
        except Exception:
            return None

    def check_VM_present(self, vm_name):
        """
        check whether a VM is present or not.
        """
        return self.get_vcenter_object([vim.VirtualMachine], vm_name)

    def get_resource_pool(self, data_center, name=None):
        """
        Get a resource pool in the datacenter by its names.
        """
        view_manager = self.vcenter_connection.viewManager
        data_center_object = self.get_data_center(name=data_center)
        container_view = view_manager.CreateContainerView(data_center_object, [vim.ResourcePool], True)
        if name is not None:
            try:
                for resource_pool in container_view.view:
                    if resource_pool.name == name:
                        return resource_pool
            finally:
                container_view.Destroy()
            raise Exception("Failed to find resource pool %s in datacenter %s" % (name, data_center))
        else:
            try:
                rp_name = []
                resource_pools = container_view.view
                for resource_pool in resource_pools:
                    folder_name = self.iterate_vcenter_objects(view_object=resource_pool)
                    rp_name.append(folder_name[folder_name.find("/Resources") + 11 :])
                # remove all occurrences of '' string
                rp_name = [i for i in rp_name if i != ""]
                if rp_name:
                    return rp_name
                else:
                    current_app.logger.info("No resource pool found in datacenter " + data_center_object)
                    return None
            finally:
                container_view.Destroy()
