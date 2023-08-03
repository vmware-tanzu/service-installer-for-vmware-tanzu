# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause


from enum import Enum


class GOVCConstants:
    RESOURCE_PATH = "/Resources/{resource_pool}"
    VM_PATH = "/vm/{vm_name}"


class VmPowerState(str, Enum):
    ON = "poweredOn"
    OFF = "poweredOff"


class GovcCommands(str, Enum):
    FIND_VMS_BY_NAME = "govc find . -type m -name {vm_name} {options}"
    FIND_OBJECTS_BY_NAME = "govc find -name {object_name} {options}"
    FIND_DATACENTER_BY_NAME = "govc find . -type d -name {dc_name} {options}"
    FIND_CLUSTERS_BY_NAME = "govc find . -type c -name {clu_name} {options}"
    FIND_FOLDERS_BY_NAME = "govc find . -type f -name {folder_name} {options}"
    FIND_RESOURCE_POOLS_BY_NAME = "govc find . -type p -name {rp_name} {options}"
    FIND_NETWORKS_BY_NAME = "govc find . -type n -name {network_name} {options}"
    CREATE_RESOURCE_POOL = "govc pool.create {options} {pool}"
    CREATE_FOLDER = "govc folder.create {options} {folder}"
    CREATE_CONTENT_LIB = "govc library.create -dc={data_center} -ds={data_store} {lib}"
    DEPLOY_LIBRARY_OVA = "govc library.deploy {options} {location} {name}"
    GET_VM_IP = "govc vm.ip -dc={datacenter} {options} {name}"
    GET_VM_PATH = "govc vm.info -dc={datacenter} {name}"
    DELETE_VM = "govc vm.destroy {vm_path}"
    DELETE_RESOURCE_POOL = "govc pool.destroy {path} {options}"
    POWER_OFF_VM = "govc vm.power -off -force {vm_path}"
    POWER_ON_VM = "govc vm.power -dc={data_center} -on=true {vm_name}"
    SET_VM_CONFIG = "govc vm.change -dc={data_center} -vm={vm_name} -c={cpu} -m={memory}"
    GET_CONTENT_LIBRARIES = "govc library.ls {options}"
    GET_CONTENT_LIBRARY_INFO = r"govc library.info /{name}"
    IMPORT_OVA_TO_CONTENT_LIB = "govc library.import {content_lib} {local_path}"
    CREATE_SUBSCRIBED_CONTENT_LIB = (
        "govc library.create -sub={url} -ds={data_store} -dc={datacenter} "
        "-sub-autosync=true -sub-ondemand=true {name}"
    )
    CREATE_SUBSCRIBED_CONTENT_LIB_WITH_THUMB_PRINT = (
        "govc library.create -sub={url} -ds={data_store} "
        "-dc={datacenter} -sub-autosync=true -sub-ondemand=true "
        "-thumbprint={thumb_print} {name}"
    )
