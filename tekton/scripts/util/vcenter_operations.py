#!/usr/bin/env python

#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
import os.path
import ssl
import sys
import tarfile
import time
import argparse
from threading import Timer
from six.moves.urllib.request import Request, urlopen
from pyVmomi import vim, vmodl
from pyVim import connect
from pyVim.connect import Disconnect
import atexit
from util.logger_helper import LoggerHelper, log
from pathlib import Path
import urllib3
from constants.constants import SegmentsName

logger = LoggerHelper.get_logger(Path(__file__).stem)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append("../")

def get_obj(content, vimtype, name):
    """
    Return an object by name, if name is None the
    first found object is returned
    """
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        try:
            c.name
        except:
            pass
        if name:
            if c.name.strip() == name.strip():
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
    container = content.viewManager.CreateContainerView(
        get_folder(si, datacenter, folder), vimtype, True)
    for c in container.view:
        try:
            c.name
        except:
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


def deploySeOva(vcenterhost, username, password, vm_name, folder, datacenter_name, resource_pool, datastore_name,
                ova_path, host):
    si = None
    try:
        print(f"Trying to connect to VCENTER SERVER . . .{vcenterhost}")
        si = connect.SmartConnectNoSSL(host=vcenterhost, user=username, pwd=password)
    except IOError as e:
        atexit.register(Disconnect, si)
        raise AssertionError("Failed to connect to vcenter.")

    print(f"Connected to VCENTER SERVER ! {vcenterhost}")
    vm = get_obj(si.RetrieveContent(), [vim.VirtualMachine], vm_name)
    if vm is None:
        datacenter = get_dc(si, datacenter_name)
        if resource_pool:
            resource_pool = get_rp(si, datacenter, resource_pool)
        else:
            resource_pool = get_largest_free_rp(si, datacenter)

        if datastore_name:
            datastore = get_ds(datacenter, datastore_name)
        else:
            datastore = get_largest_free_ds(datacenter)

        ovf_handle = OvfHandler(ova_path)

        ovf_manager = si.content.ovfManager
        # CreateImportSpecParams can specify many useful things such as
        # diskProvisioning (thin/thick/sparse/etc)
        # networkMapping (to map to networks)
        # propertyMapping (descriptor specific properties)
        nma = vim.OvfManager.NetworkMapping.Array()
        network1 = get_obj_in_list(SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT, datacenter.network)
        network2 = get_obj_in_list(SegmentsName.DISPLAY_NAME_AVI_DATA_SEGMENT, datacenter.network)
        network3 = get_obj_in_list(SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment, datacenter.network)
        network4 = get_obj_in_list(SegmentsName.DISPLAY_NAME_TKG_WORKLOAD, datacenter.network)
        network5 = get_obj_in_list(SegmentsName.DISPLAY_NAME_TKG_WORKLOAD, datacenter.network)
        network6 = get_obj_in_list(SegmentsName.DISPLAY_NAME_TKG_WORKLOAD, datacenter.network)
        network7 = get_obj_in_list(SegmentsName.DISPLAY_NAME_TKG_WORKLOAD, datacenter.network)
        network8 = get_obj_in_list(SegmentsName.DISPLAY_NAME_TKG_WORKLOAD, datacenter.network)
        network9 = get_obj_in_list(SegmentsName.DISPLAY_NAME_TKG_WORKLOAD, datacenter.network)
        network10 = get_obj_in_list(SegmentsName.DISPLAY_NAME_TKG_WORKLOAD, datacenter.network)
        # Let the name equal to VM Network and not the name of the portgroup network
        nm1 = vim.OvfManager.NetworkMapping(name="Management", network=network1)
        nm2 = vim.OvfManager.NetworkMapping(name="Data Network 1", network=network2)
        nm3 = vim.OvfManager.NetworkMapping(name="Data Network 2", network=network3)
        nm4 = vim.OvfManager.NetworkMapping(name="Data Network 3", network=network4)
        nm5 = vim.OvfManager.NetworkMapping(name="Data Network 4", network=network5)
        nm6 = vim.OvfManager.NetworkMapping(name="Data Network 5", network=network6)
        nm7 = vim.OvfManager.NetworkMapping(name="Data Network 6", network=network7)
        nm8 = vim.OvfManager.NetworkMapping(name="Data Network 7", network=network8)
        nm9 = vim.OvfManager.NetworkMapping(name="Data Network 8", network=network9)
        nm10 = vim.OvfManager.NetworkMapping(name="Data Network 9", network=network10)
        nma.append(nm1)
        nma.append(nm2)
        nma.append(nm3)
        nma.append(nm4)
        nma.append(nm5)
        nma.append(nm6)
        nma.append(nm7)
        nma.append(nm8)
        nma.append(nm9)
        nma.append(nm10)
        cisp = vim.OvfManager.CreateImportSpecParams(entityName=vm_name, diskProvisioning="thin",
                                                     networkMapping=nma)
        cisr = ovf_manager.CreateImportSpec(
            ovf_handle.get_descriptor(), resource_pool, datastore, cisp)

        # These errors might be handleable by supporting the parameters in
        # CreateImportSpecParams
        if cisr.error:
            logger.error("The following errors will prevent import of this OVA:")
            for error in cisr.error:
                logger.error("%s" % error)
            return 1
        ovf_handle.set_spec(cisr)
        lease = resource_pool.ImportVApp(cisr.importSpec, get_folder(si, datacenter, folder))
        while lease.state == vim.HttpNfcLease.State.initializing:
            logger.info("Waiting for lease to be ready...")
            time.sleep(1)
        if lease.state == vim.HttpNfcLease.State.error:
            logger.error("Lease error: %s" % lease.error)
            return 1
        if lease.state == vim.HttpNfcLease.State.done:
            return 0
        logger.info("Starting deploy...")
        ovf_handle.upload_disks(lease, host)

    return checkforIpAddress(si, vm_name)


def getSi(vcenterhost, username, password):
    si = None
    try:
        si = connect.SmartConnectNoSSL(host=vcenterhost, user=username, pwd=password)
    except IOError as e:
        atexit.register(Disconnect, si)
        raise AssertionError("Failed to connect to vcenter.")
    return si


def destroy_vm(SI, foder, Datacenter, vm_name):
    try:
        content = SI.RetrieveContent()
        datacenter = get_dc(SI, Datacenter)
        VM = get_obj_particular_folder(content, [vim.VirtualMachine], foder, datacenter, SI, vm_name)
        if VM is None:
            logger.info(f"Unable to locate VirtualMachine. Arguments given: {vm_name}")
            return None
        # while VM:
        if format(VM.runtime.powerState) == "poweredOn":
            logger.info("Attempting to power off {0}".format(VM.name))
            TASK = VM.PowerOffVM_Task()
            wait_for_task(TASK, SI)
            logger.info("{0}".format(TASK.info.state))

        logger.info("Destroying VM from vSphere.")
        TASK = VM.Destroy_Task()
        wait_for_task(TASK, SI)
        logger.info(f"{vm_name} destroyed.")
    except Exception as e:
        return None


def checkforIpAddress(si, vm_name):
    content = si.RetrieveContent()
    count = 0
    vm = get_obj(content, [vim.VirtualMachine], vm_name)
    if vm is None:
        return None
    if vm.runtime.powerState == 'poweredOff':
        logger.info("Vm is in Power off state turning it on")
        try:
            task = vm.PowerOn()
            wait_for_task(task, si)
        except Exception as e:
            raise AssertionError("Failed to power on the vm " + str(e))
        while vm.guest.ipAddress is None and count < 300:
            logger.info("Waiting , retrying.")
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
    if vm.runtime.powerState == 'poweredOff':
        print("Vm is in Power off state turning it on")
        try:
            task = vm.PowerOn()
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


def wait_for_task(task, actionName='job', hideResult=False):
    """
    Waits and provides updates on a vSphere task
    """

    while task.info.state == vim.TaskInfo.State.running:
        time.sleep(2)

    if task.info.state == vim.TaskInfo.State.success:
        if task.info.result is not None and not hideResult:
            out = '%s completed successfully, result: %s' % (actionName, task.info.result)
            print(out)
        else:
            out = '%s completed successfully.' % actionName
            print(out)
    else:
        out = '%s did not complete successfully: %s' % (actionName, task.info.error)
        print(out)
        raise task.info.error

    return task.info.result


def get_obj_in_list(obj_name, obj_list):
    """
    Gets an object out of a list (obj_list) whose name matches obj_name.
    """
    for o in obj_list:
        if o.name == obj_name:
            return o
    print("Unable to find object by the name of %s in list:\n%s" %
          (o.name, map(lambda o: o.name, obj_list)))
    exit(1)


def get_dc(si, name):
    """
    Get a datacenter by its name.
    """
    if name is not None:
        for datacenter in si.content.rootFolder.childEntity:
            if datacenter.name == name:
                return datacenter
        raise Exception('Failed to find datacenter named %s' % name)
    else:
        dcs = si.content.rootFolder.childEntity
        if dcs:
            return dcs
        else:
            raise Exception('No datacenters found on provided VC')


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
        raise Exception("Failed to find resource pool %s in datacenter %s" %
                        (name, datacenter.name))
    else:
        try:
            rp_name = []
            resource_pools = container_view.view
            for resource_pool in container_view.view:
                if resource_pool.name != "Resources":
                    rp_name.append(resource_pool.name)
            if rp_name:
                return rp_name
            else:
                logger.info("No resource pool found in datacenter " + datacenter.name)
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
    raise Exception("Failed to find resource pool %s in datacenter %s" %
                    (name, datacenter.name))


def get_largest_free_rp(si, datacenter):
    """
    Get the resource pool with the largest unreserved memory for VMs.
    """
    view_manager = si.content.viewManager
    container_view = view_manager.CreateContainerView(datacenter, [vim.ResourcePool], True)
    largest_rp = None
    unreserved_for_vm = 0
    try:
        for resource_pool in container_view.view:
            if resource_pool.runtime.memory.unreservedForVm > unreserved_for_vm:
                largest_rp = resource_pool
                unreserved_for_vm = resource_pool.runtime.memory.unreservedForVm
    finally:
        container_view.Destroy()
    if largest_rp is None:
        raise Exception("Failed to find a resource pool in datacenter %s" % datacenter.name)
    return largest_rp


def get_ds(datacenter, name):
    """
    Pick a datastore by its name.
    """
    if name is not None:
        for datastore in datacenter.datastore:
            try:
                if datastore.name == name:
                    return datastore
            except Exception:  # Ignore datastores that have issues
                pass
        raise Exception("Failed to find %s on datacenter %s" % (name, datacenter.name))
    else:
        datastore_list = []
        try:
            for ds in datacenter.datastore:
                datastore_list.append(ds.name)
            return datastore_list
        except:
            raise Exception('Encountered errors while fetching datastores %s' % datacenter.name)


def get_largest_free_ds(datacenter):
    """
    Pick the datastore that is accessible with the largest free space.
    """
    largest = None
    largest_free = 0
    for datastore in datacenter.datastore:
        try:
            free_space = datastore.summary.freeSpace
            if free_space > largest_free and datastore.summary.accessible:
                largest_free = free_space
                largest = datastore
        except Exception:  # Ignore datastores that have issues
            pass
    if largest is None:
        raise Exception('Failed to find any free datastores on %s' % datacenter.name)
    return largest


def get_tarfile_size(ctarfile):
    """
    Determine the size of a file inside the tarball.
    If the object has a size attribute, use that. Otherwise seek to the end
    and report that.
    """
    if hasattr(ctarfile, 'size'):
        return ctarfile.size
    size = ctarfile.seek(0, 2)
    ctarfile.seek(0, 0)
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
        ovffilename = list(filter(lambda x: x.endswith(".ovf"),
                                  self.tarfile.getnames()))[0]
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
        ovffilename = list(filter(lambda x: x == file_item.path,
                                  self.tarfile.getnames()))[0]
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
        url = device_url.url.replace('*', host)
        headers = {'Content-length': get_tarfile_size(ovffile)}
        if hasattr(ssl, '_create_unverified_context'):
            ssl_context = ssl.create_unverified_context()
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
            if self.lease.state not in [vim.HttpNfcLease.State.done,
                                        vim.HttpNfcLease.State.error]:
                self.start_timer()
            sys.stderr.write("Progress: %d%%\r" % prog)
        except Exception:  # Any exception means we should stop updating progress.
            pass


class FileHandle(object):
    def __init__(self, filename):
        self.filename = filename
        self.fh = open(filename, 'rb')

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
        if 'accept-ranges' not in self.headers:
            raise Exception("Site does not accept ranges")
        self.st_size = int(self.headers['content-length'])
        self.offset = 0

    def _headers_to_dict(self, r):
        result = {}
        if hasattr(r, 'getheaders'):
            for n, v in r.getheaders():
                result[n.lower()] = v.strip()
        else:
            for line in r.info().headers:
                if line.find(':') != -1:
                    n, v = line.split(': ', 1)
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
        req = Request(self.url,
                      headers={'Range': 'bytes=%d-%d' % (start, end)})
        r = urlopen(req)
        self.offset += amount
        result = r.read(amount)
        r.close()
        return result

    # A slightly more accurate percentage
    def progress(self):
        return int(100.0 * self.offset / self.st_size)


def createResourcePool(vcenterHostName, vcenterUser, vcenterPassword, clusterName, name, parentResourcePool):
    si = None
    try:
        si = connect.SmartConnectNoSSL(host=vcenterHostName, user=vcenterUser, pwd=vcenterPassword)
        content = si.RetrieveContent()
        cluster = get_obj(content, [vim.ClusterComputeResource], clusterName)

        resource_pool = get_obj(content, [vim.ResourcePool], name)
        if resource_pool is None:
            configSpec = vim.ResourceConfigSpec()
            cpuAllocationInfo = vim.ResourceAllocationInfo()
            memAllocationInfo = vim.ResourceAllocationInfo()
            sharesInfo = vim.SharesInfo(level='normal')

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
                resource_pool_obj = get_obj(content, [vim.ResourcePool], parentResourcePool)
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
            elif hasattr(network, 'childEntity'):
                ports = network.childEntity
                for item in ports:
                    if item.name == name:
                        return item
        raise Exception('Failed to find port named %s' % name)
    else:
        network_list = []
        try:
            for port in datacenter.networkFolder.childEntity:
                if hasattr(port, 'childEntity'):
                    ports = port.childEntity
                    for item in ports:
                        network_list.append(item.name)
                else:
                    network_list.append(port.name)
            return network_list
        except:
            raise Exception('Encountered errors while fetching networks %s' % datacenter.name)


def getDvPortGroupId(vcenterIp, vcenterUser, vcenterPassword, networkName, vc_data_center):
    try:
        si = connect.SmartConnectNoSSL(host=vcenterIp, user=vcenterUser, pwd=vcenterPassword)
        try:
            datacenter = get_dc(si, vc_data_center)
        except Exception as e:
            logger.error(str(e))
            return None
        network = getNetwork(datacenter, networkName)
        switch = network.config.distributedVirtualSwitch
        for portgroup in switch.portgroup:
            if portgroup.name == networkName:
                return portgroup.config.key
        return None
    except Exception as e:
        logger.error(str(e))
        return None
