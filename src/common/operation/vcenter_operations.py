#!/usr/bin/env python
# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import atexit
import os
import os.path
import ssl
import sys
import tarfile
import time
from threading import Timer

from flask import current_app
from pyVim import connect
from pyVim.connect import Disconnect
from pyVmomi import vim, vmodl
from six.moves.urllib.request import Request, urlopen

__author__ = "rupesh"


def get_obj(content, vimtype, name):
    """
    Return an object by name, if name is None the
    first found object is returned
    """
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    if container is not None:
        for host in container.view:
            rp = host.name
            if rp:
                folder_name = rp
                fp = host.parent
                while fp is not None and fp.name is not None and fp != content.rootFolder:
                    folder_name = fp.name + "/" + folder_name
                    try:
                        fp = fp.parent
                    except BaseException:
                        break
                folder_name = "/" + folder_name
                if name:
                    if str(folder_name).endswith(name):
                        return content.searchIndex.FindByInventoryPath(folder_name)
                else:
                    return content.searchIndex.FindByInventoryPath(folder_name)

    return obj


def get_vm_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    if container is not None:
        for c in container.view:
            if name:
                if c.name == name:
                    obj = c
                    break
            else:
                obj = c
                break
    return obj


def get_obj_particular_folder(content, vimtype, folder, datacenter, si, name):
    """
    Return an object by name, if name is None the
    first found object is returned
    """
    obj = None
    container = content.viewManager.CreateContainerView(get_folder(si, datacenter, folder), vimtype, True)
    for c in container.view:
        try:
            c.name
        except Exception:
            pass
        if name:
            if str(c.name.strip()).__contains__(name.strip()):
                obj = c
                break
        else:
            obj = c
            break

    return obj


def checkVmPresent(vcenterhost, username, password, vm_name):
    si = getSi(vcenterhost, username, password)
    return get_obj(si.RetrieveContent(), [vim.VirtualMachine], vm_name)


def getSi(vcenterhost, username, password):
    si = None
    try:
        si = connect.SmartConnectNoSSL(host=vcenterhost, user=username, pwd=password)
    except IOError:
        atexit.register(Disconnect, si)
        raise AssertionError("Failed to connect to vcenter.")
    return si


def destroy_vm(SI, foder, Datacenter, vm_name):
    try:
        content = SI.RetrieveContent()
        datacenter = get_dc(SI, Datacenter)
        VM = get_obj_particular_folder(content, [vim.VirtualMachine], foder, datacenter, SI, vm_name)
        if VM is None:
            current_app.logger.info(f"Unable to locate VirtualMachine. Arguments given: {vm_name}")
            return None
        # while VM:
        if format(VM.runtime.powerState) == "poweredOn":
            current_app.logger.info("Attempting to power off {0}".format(VM.name))
            TASK = VM.PowerOffVM_Task()
            wait_for_task(TASK, SI)
            current_app.logger.info("{0}".format(TASK.info.state))

        current_app.logger.info("Destroying VM from vSphere.")
        TASK = VM.Destroy_Task()
        wait_for_task(TASK, SI)
        current_app.logger.info(f"{vm_name} destroyed.")
    except Exception:
        return None


def checkforIpAddress(si, vm_name):
    content = si.RetrieveContent()
    count = 0
    vm = get_vm_obj(content, [vim.VirtualMachine], vm_name)
    if vm is None:
        return None
    if vm.runtime.powerState == "poweredOff":
        current_app.logger.info("Vm is in Power off state turning it on")
        try:
            task = vm.PowerOn()
            wait_for_task(task, si)
        except Exception as e:
            raise AssertionError("Failed to power on the vm " + str(e))
        while vm.guest.ipAddress is None and count < 300:
            current_app.logger.info("Waiting , retrying.")
            time.sleep(1)
            count = count + 1
    if vm.guest.ipAddress is None:
        raise AssertionError("Failed to get ip address of vm " + vm_name)
    return vm.guest.ipAddress


def getMacAddresses(si, vm_name):
    content = si.RetrieveContent()
    count = 0
    vm = get_obj(content, [vim.VirtualMachine], vm_name)
    if vm is None:
        return None
    if vm.runtime.powerState == "poweredOff":
        print("Vm is in Power off state turning it on")
        try:
            task = vm.PowerOn()
            current_app.logger.info(task)
        except Exception as e:
            raise AssertionError("Failed to power on the vm " + str(e))
        while vm.guest.ipAddress is None and count < 300:
            print("Waiting , retrying.")
            time.sleep(1)
            count = count + 1
    if vm.guest.ipAddress is None:
        raise AssertionError("Failed to get ip address of vm " + vm_name)
    hardware = vm.config.hardware.device
    listOfMac = []
    for h in hardware:
        if isinstance(h, vim.vm.device.VirtualEthernetCard):
            listOfMac.append(h.macAddress)
    return listOfMac


def wait_for_task(task, actionName="job", hideResult=False):
    """
    Waits and provides updates on a vSphere task
    """

    while task.info.state == vim.TaskInfo.State.running:
        time.sleep(2)

    if task.info.state == vim.TaskInfo.State.success:
        if task.info.result is not None and not hideResult:
            out = "%s completed successfully, result: %s" % (actionName, task.info.result)
            print(out)
        else:
            out = "%s completed successfully." % actionName
            print(out)
    else:
        out = "%s did not complete successfully: %s" % (actionName, task.info.error)
        print(out)
        raise task.info.error

    return task.info.result


def get_dc(si, name):
    content = si.RetrieveContent()
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.Datacenter], True)
    if name is not None:
        try:
            return content.searchIndex.FindByInventoryPath("/" + name)
        finally:
            container.Destroy()
    else:
        dc_name = []
        try:
            for dc in container.view:
                rp = dc.name
                if rp:
                    folder_name = rp
                    fp = dc.parent
                    while fp is not None and fp.name is not None and fp != si.content.rootFolder:
                        folder_name = fp.name + "/" + folder_name
                        try:
                            fp = fp.parent
                        except BaseException:
                            break
                    folder_name = "/" + folder_name
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


def get_rp(si, datacenter, name):
    """
    Get a resource pool in the datacenter by its names.
    """
    view_manager = si.content.viewManager
    container_view = view_manager.CreateContainerView(datacenter, [vim.ResourcePool], True)
    if name is not None:
        try:
            for resource_pool in container_view.view:
                if resource_pool.name == name:
                    return resource_pool
        finally:
            container_view.Destroy()
        raise Exception("Failed to find resource pool %s in datacenter %s" % (name, datacenter.name))
    else:
        try:
            rp_name = []
            for resource_pool in container_view.view:
                rp = resource_pool.name
                if rp:
                    folder_name = rp
                    fp = resource_pool.parent
                    while fp is not None and fp.name is not None and fp != si.content.rootFolder:
                        folder_name = fp.name + "/" + folder_name
                        try:
                            fp = fp.parent
                        except BaseException:
                            break
                    folder_name = "/" + folder_name
                    first_rp = folder_name[folder_name.find("/Resources") + 11 :]
                    if first_rp:
                        rp_name.append(first_rp)
            if rp_name:
                return rp_name
            else:
                current_app.logger.info("No resource pool found in datacenter " + datacenter.name)
                return None
        finally:
            container_view.Destroy()


def get_folder(si, datacenter, name):
    """
    Get a resource pool in the datacenter by its names.
    """
    view_manager = si.content.viewManager
    container_view = view_manager.CreateContainerView(datacenter, [vim.Folder], True)
    try:
        for resource_pool in container_view.view:
            if resource_pool.name == name:
                return resource_pool
    finally:
        container_view.Destroy()
    raise Exception("Failed to find resource pool %s in datacenter %s" % (name, datacenter.name))


def get_ds(si, datacenter, name):
    """
    Pick a cluster by its name.
    """
    view_manager = si.content.viewManager
    container = view_manager.CreateContainerView(datacenter, [vim.Datastore], True)
    try:
        h_name = []
        if container is not None:
            for host in container.view:
                rp = host.name
                if rp:
                    folder_name = rp
                    fp = host.parent
                    while fp is not None and fp.name is not None and fp != si.content.rootFolder:
                        folder_name = fp.name + "/" + folder_name
                        try:
                            fp = fp.parent
                        except BaseException:
                            break
                    folder_name = "/" + folder_name
                    if name:
                        if str(folder_name).endswith(name):
                            content = si.RetrieveContent()
                            return content.searchIndex.FindByInventoryPath(folder_name)
                    first_rp = folder_name[folder_name.find("/datastore") + 11 :]
                    if first_rp:
                        h_name.append(first_rp.strip("/"))
        if h_name:
            return h_name
    finally:
        container.Destroy()


def get_tarfile_size(tarfile):
    """
    Determine the size of a file inside the tarball.
    If the object has a size attribute, use that. Otherwise seek to the end
    and report that.
    """
    if hasattr(tarfile, "size"):
        return tarfile.size
    size = tarfile.seek(0, 2)
    tarfile.seek(0, 0)
    return size


class OvfHandler(object):
    """
    OvfHandler handles most of the OVA operations.
    It processes the tarfile, matches disk keys to files and
    uploads the disks, while keeping the progress up to date for the lease.
    """

    def __init__(self, ovafile):
        """
        Performs necessary initialization, opening the OVA file,
        processing the files and reading the embedded ovf file.
        """
        self.handle = self._create_file_handle(ovafile)
        self.tarfile = tarfile.open(fileobj=self.handle)
        ovffilename = list(filter(lambda x: x.endswith(".ovf"), self.tarfile.getnames()))[0]
        ovffile = self.tarfile.extractfile(ovffilename)
        self.descriptor = ovffile.read().decode()

    def _create_file_handle(self, entry):
        """
        A simple mechanism to pick whether the file is local or not.
        This is not very robust.
        """
        if os.path.exists(entry):
            return FileHandle(entry)
        return WebHandle(entry)

    def get_descriptor(self):
        return self.descriptor

    def set_spec(self, spec):
        """
        The import spec is needed for later matching disks keys with
        file names.
        """
        self.spec = spec

    def get_disk(self, file_item):
        """
        Does translation for disk key to file name, returning a file handle.
        """
        ovffilename = list(filter(lambda x: x == file_item.path, self.tarfile.getnames()))[0]
        return self.tarfile.extractfile(ovffilename)

    def get_device_url(self, file_item, lease):
        for device_url in lease.info.deviceUrl:
            if device_url.importKey == file_item.deviceId:
                return device_url
        raise Exception("Failed to find deviceUrl for file %s" % file_item.path)

    def upload_disks(self, lease, host):
        """
        Uploads all the disks, with a progress keep-alive.
        """
        self.lease = lease
        try:
            self.start_timer()
            for fileItem in self.spec.fileItem:
                self.upload_disk(fileItem, lease, host)
            lease.Complete()
            print("Finished deploy successfully.")
            return 0
        except vmodl.MethodFault as ex:
            print("Hit an error in upload: %s" % ex)
            lease.Abort(ex)
        except Exception as ex:
            print("Lease: %s" % lease.info)
            print("Hit an error in upload: %s" % ex)
            lease.Abort(vmodl.fault.SystemError(reason=str(ex)))
        return 1

    def upload_disk(self, file_item, lease, host):
        """
        Upload an individual disk. Passes the file handle of the
        disk directly to the urlopen request.
        """
        ovffile = self.get_disk(file_item)
        if ovffile is None:
            return
        device_url = self.get_device_url(file_item, lease)
        url = device_url.url.replace("*", host)
        headers = {"Content-length": get_tarfile_size(ovffile)}
        if hasattr(ssl, "_create_unverified_context"):
            ssl_context = ssl._create_unverified_context()
        else:
            ssl_context = None
        req = Request(url, ovffile, headers)
        urlopen(req, context=ssl_context)

    def start_timer(self):
        """
        A simple way to keep updating progress while the disks are transferred.
        """
        Timer(5, self.timer).start()

    def timer(self):
        """
        Update the progress and reschedule the timer if not complete.
        """
        try:
            prog = self.handle.progress()
            self.lease.Progress(prog)
            if self.lease.state not in [vim.HttpNfcLease.State.done, vim.HttpNfcLease.State.error]:
                self.start_timer()
            sys.stderr.write("Progress: %d%%\r" % prog)
        except Exception:  # Any exception means we should stop updating progress.
            pass


class FileHandle(object):
    def __init__(self, filename):
        self.filename = filename
        self.fh = open(filename, "rb")

        self.st_size = os.stat(filename).st_size
        self.offset = 0

    def __del__(self):
        self.fh.close()

    def tell(self):
        return self.fh.tell()

    def seek(self, offset, whence=0):
        if whence == 0:
            self.offset = offset
        elif whence == 1:
            self.offset += offset
        elif whence == 2:
            self.offset = self.st_size - offset

        return self.fh.seek(offset, whence)

    def seekable(self):
        return True

    def read(self, amount):
        self.offset += amount
        result = self.fh.read(amount)
        return result

    # A slightly more accurate percentage
    def progress(self):
        return int(100.0 * self.offset / self.st_size)


class WebHandle(object):
    def __init__(self, url):
        self.url = url
        r = urlopen(url)
        if r.code != 200:
            raise FileNotFoundError(url)
        self.headers = self._headers_to_dict(r)
        if "accept-ranges" not in self.headers:
            raise Exception("Site does not accept ranges")
        self.st_size = int(self.headers["content-length"])
        self.offset = 0

    def _headers_to_dict(self, r):
        result = {}
        if hasattr(r, "getheaders"):
            for n, v in r.getheaders():
                result[n.lower()] = v.strip()
        else:
            for line in r.info().headers:
                if line.find(":") != -1:
                    n, v = line.split(": ", 1)
                    result[n.lower()] = v.strip()
        return result

    def tell(self):
        return self.offset

    def seek(self, offset, whence=0):
        if whence == 0:
            self.offset = offset
        elif whence == 1:
            self.offset += offset
        elif whence == 2:
            self.offset = self.st_size - offset
        return self.offset

    def seekable(self):
        return True

    def read(self, amount):
        start = self.offset
        end = self.offset + amount - 1
        req = Request(self.url, headers={"Range": "bytes=%d-%d" % (start, end)})
        r = urlopen(req)
        self.offset += amount
        result = r.read(amount)
        r.close()
        return result

    # A slightly more accurate percentage
    def progress(self):
        return int(100.0 * self.offset / self.st_size)


def createResourcePool(
    vcenterHostName, vceneterUser, vcenterPassword, clusterName, name, parentResourcePool, data_center
):
    si = None
    create = False
    try:
        si = connect.SmartConnectNoSSL(host=vcenterHostName, user=vceneterUser, pwd=vcenterPassword)
        content = si.RetrieveContent()
        cluster = get_obj(content, [vim.ClusterComputeResource], clusterName)

        resource_pool = get_obj(content, [vim.ResourcePool], name)
        if resource_pool is None:
            create = True
        else:
            current_app.logger.info("Resource pool " + name + " is already present in cluster - " + clusterName)
            current_app.logger.info("Checking if it's present in right path...")
            if parentResourcePool:
                path = "/" + data_center + "/host/" + clusterName + "/Resources/" + parentResourcePool + "/" + name
            else:
                path = "/" + data_center + "/host/" + clusterName + "/Resources/" + name
            obj = content.searchIndex.FindByInventoryPath(path)
            if obj is None:
                create = True
        if create:
            configSpec = vim.ResourceConfigSpec()
            cpuAllocationInfo = vim.ResourceAllocationInfo()
            memAllocationInfo = vim.ResourceAllocationInfo()
            sharesInfo = vim.SharesInfo(level="normal")

            cpuAllocationInfo.reservation = 0
            cpuAllocationInfo.expandableReservation = True
            cpuAllocationInfo.shares = sharesInfo
            cpuAllocationInfo.limit = -1

            memAllocationInfo.reservation = 0
            memAllocationInfo.expandableReservation = True
            memAllocationInfo.shares = sharesInfo
            memAllocationInfo.limit = -1

            configSpec.cpuAllocation = cpuAllocationInfo
            configSpec.memoryAllocation = memAllocationInfo
            if parentResourcePool:
                path = "/" + data_center + "/host/" + clusterName + "/Resources/" + parentResourcePool
                resource_pool_obj = content.searchIndex.FindByInventoryPath(path)
                configSpec.entity = resource_pool_obj
                resource_pool_obj.CreateResourcePool(name, configSpec)
            else:
                configSpec.entity = cluster
                cluster.resourcePool.CreateResourcePool(name, configSpec)
            return "SUCCESS"
        else:
            return None
    except Exception as e:
        atexit.register(Disconnect, si)
        raise AssertionError("Operation failed " + str(e))
    finally:
        atexit.register(Disconnect, si)


def create_folder(vcenterHostName, vceneterUser, vcenterPassword, datacenter_name, folder_name):
    si = None
    try:
        si = connect.SmartConnectNoSSL(host=vcenterHostName, user=vceneterUser, pwd=vcenterPassword)
        content = si.RetrieveContent()
        datacenter = get_dc(si, datacenter_name)
        destfolder = get_obj(content, [vim.Folder], folder_name)
        if destfolder is None:
            datacenter.vmFolder.CreateFolder(folder_name)
            return "SUCCESS"
        else:
            return None
    except Exception as e:
        atexit.register(Disconnect, si)
        raise AssertionError("Operation failed " + str(e))
    finally:
        atexit.register(Disconnect, si)


def getNetwork(datacenter, name):
    if name is not None:
        networks = datacenter.networkFolder.childEntity
        for network in networks:
            if network.name == name:
                return network
            elif hasattr(network, "childEntity"):
                ports = network.childEntity
                for item in ports:
                    if item.name == name:
                        return item
        raise Exception("Failed to find port named %s" % name)
    else:
        network_list = []
        try:
            for port in datacenter.networkFolder.childEntity:
                if hasattr(port, "childEntity"):
                    ports = port.childEntity
                    for item in ports:
                        network_list.append(item.name)
                else:
                    network_list.append(port.name)
            return network_list
        except Exception:
            raise Exception("Encountered errors while fetching networks %s" % datacenter.name)


def getDvPortGroupId(vcenterIp, vcenterUser, vcenterPassword, networkName, vc_data_center):
    try:
        si = connect.SmartConnectNoSSL(host=vcenterIp, user=vcenterUser, pwd=vcenterPassword)
        try:
            datacenter = get_dc(si, vc_data_center)
        except Exception as e:
            current_app.logger.error(str(e))
            return None
        network = getNetwork(datacenter, networkName)
        switch = network.config.distributedVirtualSwitch
        for portgroup in switch.portgroup:
            if portgroup.name == networkName:
                return portgroup.config.key
        return None
    except Exception as e:
        current_app.logger.error(str(e))
        return None
