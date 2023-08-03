/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
/**
 * Angular Modules
 */
import { Component, OnInit, ViewChild } from '@angular/core';
import { FormControl, Validators } from '@angular/forms';

import { ClrLoadingState } from '@clr/angular';
import { Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';

/**
 * App imports
 */
import { AppEdition } from 'src/app/shared/constants/branding.constants';
import { APP_ROUTES, Routes } from 'src/app/shared/constants/routes.constants';
import { VsphereTkgsService } from 'src/app/shared/service/vsphere-tkgs-data.service';
import { APIClient } from 'src/app/swagger/api-client.service';
import { SSLThumbprintModalComponent } from 'src/app/views/landing/wizard/shared/components/modals/ssl-thumbprint-modal/ssl-thumbprint-modal.component';
import { FormMetaDataStore } from 'src/app/views/landing/wizard/shared/FormMetaDataStore';
import { StepFormDirective } from 'src/app/views/landing/wizard/shared/step-form/step-form';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';


const SupervisedField = ['vcenterAddress', 'username', 'password'];
/**
 * vSphere Version Info definition
 */
export interface VsphereVersioninfo {
    version: string,
    build: string;
}

@Component({
    selector: 'app-env-details-step',
    templateUrl: './env-details.component.html',
    styleUrls: ['./env-details.component.scss']
})
export class EnvDetailsComponent extends StepFormDirective implements OnInit {
    @ViewChild(SSLThumbprintModalComponent) sslThumbprintModal: SSLThumbprintModalComponent;

    APP_ROUTES: Routes = APP_ROUTES;

    loading: boolean = false;
    connected: boolean = false;
    validateToken = false;
    loadData: boolean = false;
    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    dataLoadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    validateLoadingState: ClrLoadingState = ClrLoadingState.DEFAULT;

    fetchResources: boolean = false;
    fetchCluster: boolean = false;
    fetchOvaImage = false;
    datacenters = [];
    clusters = [];
    contentLibs = [];

    vsphereHost: string;
    thumbprint: string;
    edition: AppEdition = AppEdition.TCE;
    clusterError = false;
    clusterChangeErrorNotification = "";
    clusterErrorMsg = 'Provided Cluster is not found, please select again.';
    datacenterError = false;
    datacenterErrorMsg = 'Provided Datacenter is not found, please select again.';
    contentLibError = false;
    contentLibErrorMsg = 'Provided Content Library is not found, please select again.'
    subscription: Subscription;
    uploadStatus: boolean;
    customerConnect = false;

    private VcFqdn;
    private VcUser;
    private VcDatacenter;
    private VcCluster;
    constructor(private validationService: ValidationService,
                private apiClient: APIClient,
                private dataService: VsphereTkgsService) {
        super();
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl('vcenterAddress', new FormControl('', [Validators.required,
            this.validationService.isValidIpOrFqdn(),
            this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('username', new FormControl('', [Validators.required,
            this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('password',
            new FormControl('', [
                Validators.required]
            ));
        this.formGroup.addControl('datacenter', new FormControl('', [Validators.required]));
        this.formGroup.addControl('cluster', new FormControl('', [Validators.required]));
        // Fetched from backend, not asked on UI
        this.formGroup.addControl('thumbprint', new FormControl('', []));
        this.disableFormFields();

        /** If vSphere FQDN, username or password changes, following will be reset
         * Datacenter
         * Cluster
         * Datastore
         * Content Library
         * AVI OVA image
         */
        SupervisedField.forEach(field => {
            this.formGroup.get(field).valueChanges.pipe(
                debounceTime(500),
                distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr)),
                takeUntil(this.unsubscribe))
                .subscribe(() => {
                    this.connected = false;
                    this.loadingState = ClrLoadingState.DEFAULT;
                    this.formGroup.get('datacenter').setValue('');
                    this.datacenters = [];
                    this.formGroup.get('datacenter').disable();
                    this.formGroup.get('cluster').setValue('');
                    this.clusters = [];
                    this.formGroup.get('cluster').disable();

                });
        });
        this.formGroup['canMoveToNext'] = () => {
            this.apiClient.vcAddress = this.formGroup.get('vcenterAddress').value;
            this.apiClient.vcUser = this.formGroup.get('username').value;
            this.apiClient.vcPass = this.formGroup.get('password').value;
            this.apiClient.fetchNamespaceStorageSpec = true;
            return this.formGroup.valid && this.fetchResources && this.fetchCluster;
        };
        this.formGroup.get('cluster').valueChanges.subscribe(() => this.clusterError = false);
        this.formGroup.get('datacenter').valueChanges.subscribe(() => this.datacenterError = false);

        this.subscription = this.dataService.currentInputFileStatus.subscribe(
            (uploadStatus) => this.uploadStatus = uploadStatus);
        // Updating values from uploaded JSON
        if (this.uploadStatus) {
            this.subscription = this.dataService.currentVcAddress.subscribe(
                (VcFqdn) => this.VcFqdn = VcFqdn);
            this.formGroup.get('vcenterAddress').setValue(this.VcFqdn);
            this.subscription = this.dataService.currentVcUser.subscribe(
                (VcUser) => this.VcUser = VcUser);
            this.formGroup.get('username').setValue(this.VcUser);
            this.subscription = this.dataService.currentDatacenter.subscribe(
                (datacenter) => this.VcDatacenter = datacenter);
            this.subscription = this.dataService.currentCluster.subscribe(
                (cluster) => this.VcCluster = cluster);

        }
    }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
        // don't fill password field with ****
        if (!this.uploadStatus) {
            this.formGroup.get('password').setValue('');
        } else {
            this.formGroup.get('password').setValue('');
        }
    }

    /**
     * @method connectVC
     * helper method to make connection to VC environment, call retrieveDatacenters
     * method if VC connection successful
     */
    connectVC() {
        this.loadingState = ClrLoadingState.LOADING;
        this.vsphereHost = this.formGroup.controls['vcenterAddress'].value;
        this.getSSLThumbprint(this.vsphereHost);
    }

    validateResourceGroupData() {
        this.errorNotification = null;
        if (!this.uploadStatus) {
            return true;
        } else {
            if (this.datacenters.indexOf(this.VcDatacenter) === -1) {
                this.datacenterError = true;
            } else {
                this.datacenterError = false;
                this.formGroup.get('datacenter').setValue(this.VcDatacenter);
            }
        }
    }

    getSSLThumbprint(vsphereHost) {
        const payload = {
            'envSpec': {
                'vcenterDetails': {
                    'vcenterAddress': vsphereHost
                }
            }
        };
        this.connected = false;
        this.apiClient.getSSLThumbprint('vsphere', payload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.thumbprint = data.SHA1;
                    this.formGroup.controls['thumbprint'].setValue(this.thumbprint);
                    FormMetaDataStore.saveMetaDataEntry(this.formName, 'thumbprint', {
                        label: 'SSL THUMBPRINT',
                        displayValue: this.thumbprint,
                    });
                    this.sslThumbprintModal.open();
                    this.getVsphereData();
                } else if (data.responseType === 'ERROR') {
                    this.connected = false;
                    this.loadingState = ClrLoadingState.DEFAULT;
                    this.errorNotification = data.msg;
                }
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'Some Error Occurred while Retrieving SSL Thumbprint';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'vCenter: ' + err.msg;
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'vCenter: Please verify vCenter FQDN.';
            }
        });
    }

    getVcenterVersion() {
        let vCenterData = {
            "vcenterAddress": "",
            "ssoUser": "",
            "ssoPassword": ""
        };

        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['ssoUser'] = this.formGroup.get('username').value;
        vCenterData['ssoPassword'] = this.formGroup.get('password').value;
        this.apiClient.getVcenterVersion(vCenterData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    if(data.VCENTER_8 === "true") this.apiClient.vcenterVersion = "8";
                    else this.apiClient.vcenterVersion = "7";
                } else if (data.responseType === 'ERROR') {
                    this.connected = false;
                    this.errorNotification = data.msg;
                    this.loadingState = ClrLoadingState.DEFAULT;
                }
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'Some Error Occurred while checking vcenter version';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'vCenter: ' + err.msg;
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'vCenter: Please verify vCenter FQDN.';
            }
        })
    }

    thumbprintModalResponse(validThumbprint: boolean) {
        if (validThumbprint) {
            this.login();
        } else {
            this.errorNotification = 'Connection failed. Certificate thumbprint was not validated.';
        }
    }

    login() {
        this.loadingState = ClrLoadingState.LOADING;
        this.errorNotification = null;
        this.loadingState = ClrLoadingState.DEFAULT;
    }

    /**
     * @method getDisabled
     * helper method to get if connect btn should be disabled
     */
    getDisabled(): boolean {
        return !(this.formGroup.get('vcenterAddress').valid && this.formGroup.get('username').valid && this.formGroup.get('password').valid);
    }

    disableFormFields() {
        this.formGroup.get('datacenter').disable();
        this.formGroup.get('cluster').disable();
    }

    enableAllFormFields() {
        this.formGroup.get('datacenter').enable();
    }
    dumyFormFields() {
        this.datacenters = ['Datacenter-1', 'Datacenter-2'];
        this.clusters = ['Cluster-1', 'Cluster-2'];
        this.apiClient.contentLibs = ['Content-lib-1', 'Content-lib-2'];
        this.apiClient.networks = ['Network-1', 'Network-2', 'Network-3', 'Network-4'];
        this.apiClient.storagePolicies = ['Policy-1', 'Policy-2', 'Policy-3'];
        this.apiClient.namespaceVmClass = ['best-effort-2xlarge', 'best-effort-4xlarge', 'best-effort-8xlarge'];
        this.apiClient.clusterVersionsBeta = ['121', '321'];
        this.apiClient.clusterVersionsAlpha = ['121', '321'];
        this.apiClient.tkgsWorkloadNetwork = ['CREATE NEW', 'pri-nw-1', 'pri-nw-2'];
        this.apiClient.allNamespaces = ['CREATE NEW', 'ns-1', 'ns-2'];
        this.apiClient.tmcMgmtCluster = ['mgmt-1', 'mgmt-2'];
        this.fetchResources = true;
        this.fetchOvaImage = true;
    }

    getVsphereData() {
        let vCenterData = {
            "vcenterAddress": "",
            "ssoUser": "",
            "ssoPassword": ""
        };

        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['ssoUser'] = this.formGroup.get('username').value;
        vCenterData['ssoPassword'] = this.formGroup.get('password').value;

        this.apiClient.getVsphereData(vCenterData, 'vsphere', 'tkgs-ns').subscribe((data: any) => {
              if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.datacenters = data.DATACENTERS;
                    this.contentLibs = data.CONTENTLIBRARY_NAMES;
                    this.apiClient.contentLibs = data.CONTENTLIBRARY_NAMES;
                    if (this.uploadStatus){
                        if (this.datacenters.indexOf(this.VcDatacenter) === -1) {
                            this.datacenterError = true;
                        } else {
                            this.datacenterError = false;
                            this.formGroup.get('datacenter').setValue(this.VcDatacenter);
                        }
                    }
                    this.apiClient.networks = data.NETWORKS;
                    this.getVcenterVersion();
                    this.getStoragePolicy();
                } else if (data.responseType === 'ERROR') {
                    this.fetchResources = false;
                    this.connected = false;
                    this.errorNotification = 'vCenter: ' + data.msg;
                }
              } else {
                this.fetchResources = false;
                this.connected = false;
                this.errorNotification = 'vCenter: Some Error Occurred while Fetching Resources. Please verify vCenter credentials.';
              }
            }, (error: any) => {
              if (error.responseType === 'ERROR') {
                this.fetchResources = false;
                this.connected = false;
                this.errorNotification = 'vCenter: ' + error.msg;
              } else {
                this.fetchResources = false;
                this.connected = false;
                this.errorNotification = 'vCenter: Some Error Occurred while Fetching Resources. Please verify vCenter credentials.';
              }
            });
    }

    getStoragePolicy() {
        let vCenterData = {
            "vcenterAddress": "",
            "ssoUser": "",
            "ssoPassword": ""
        };
        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['ssoUser'] = this.formGroup.get('username').value;
        vCenterData['ssoPassword'] = this.formGroup.get('password').value;
        this.apiClient.getStoragePolicy(vCenterData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.apiClient.storagePolicies = data.STORAGE_POLICIES;
                    this.getVmClasses();
                } else if (data.responseType === 'ERROR') {
                    this.fetchResources = false;
                    this.connected = false;
                    this.dataLoadingState = ClrLoadingState.DEFAULT;
                    this.errorNotification = 'Storage Policy: ' + data.msg;
                }
            } else {
                this.fetchResources = false;
                this.connected = false;
                this.dataLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'Storage Policy: Error in listing Storage Policies';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.fetchResources = false;
                this.connected = false;
                this.dataLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'Storage Policy: ' + error.msg;
            } else {
                this.fetchResources = false;
                this.connected = false;
                this.dataLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'Storage Policy: Error in listing Storage Policies';
            }
        });
    }

    getVmClasses() {
        let vCenterData = {
            "vcenterAddress": "",
            "ssoUser": "",
            "ssoPassword": ""
        };
        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['ssoUser'] = this.formGroup.get('username').value;
        vCenterData['ssoPassword'] = this.formGroup.get('password').value;
        this.apiClient.getVmClasses(vCenterData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.apiClient.namespaceVmClass = data.VM_CLASSES;
                    this.fetchResources = true;
                    this.connected = true;
                    this.dataLoadingState = ClrLoadingState.DEFAULT;
                    this.enableAllFormFields();
                } else if(data.responseType === 'ERROR') {
                    this.fetchResources = false;
                    this.connected = false;
                    this.errorNotification = 'VM Classes: ' + data.msg;
                    this.dataLoadingState = ClrLoadingState.DEFAULT;
                }
            } else {
                this.fetchResources = false;
                this.connected = false;
                this.errorNotification = 'VM Classes: Error in listing VM Classes';
                this.dataLoadingState = ClrLoadingState.DEFAULT;
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.fetchResources = false;
                this.connected = false;
                this.errorNotification = 'VM Classes: ' + error.msg;
                this.dataLoadingState = ClrLoadingState.DEFAULT;
            } else {
                this.fetchResources = false;
                this.connected = false;
                this.errorNotification = 'VM Classes: Error in listing VM Classes';
                this.dataLoadingState = ClrLoadingState.DEFAULT;
            }
        });
    }

    reloadVsphereData() {
        let vCenterData = {
            "vcenterAddress": "",
            "ssoUser": "",
            "ssoPassword": ""
        };

        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['ssoUser'] = this.formGroup.get('username').value;
        vCenterData['ssoPassword'] = this.formGroup.get('password').value;
        this.dataLoadingState = ClrLoadingState.LOADING;
        this.errorNotification = null;
        this.apiClient.getVsphereData(vCenterData, 'vsphere', 'tkgs-ns').subscribe((data: any) => {
              if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.datacenters = data.DATACENTERS;
                    this.apiClient.networks = data.NETWORKS;
                    this.contentLibs = data.CONTENTLIBRARY_NAMES;
                    this.apiClient.contentLibs = data.CONTENTLIBRARY_NAMES;
                    this.getStoragePolicy();
                } else if (data.responseType === 'ERROR') {
                    this.fetchResources = false;
                    this.loadData = false;
                    this.dataLoadingState = ClrLoadingState.DEFAULT;
                    this.errorNotification = 'vCenter: ' + data.msg;
                }
              } else {
                this.fetchResources = false;
                this.loadData = false;
                this.dataLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'vCenter: Some Error Occurred while Fetching Resources. Please verify vCenter credentials';
              }
            }, (error: any) => {
              if (error.responseType === 'ERROR') {
                this.fetchResources = false;
                this.loadData = false;
                this.dataLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'vCenter: ' + error.msg;
              } else {
                this.fetchResources = false;
                this.loadData = false;
                this.dataLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'vCenter: Some Error Occurred while Fetching Resources. Please verify vCenter credentials';
              }
            });
    }

    getWcpCluster(datacenter) {
        let vCenterData = {
            "vcenterAddress": "",
            "ssoUser": "",
            "ssoPassword": "",
            "datacenter": datacenter,
        };
        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['ssoUser'] = this.formGroup.get('username').value;
        vCenterData['ssoPassword'] = this.formGroup.get('password').value;
        this.apiClient.getWcpCluster(vCenterData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.apiClient.wcpClusterName = data.WCP_CLUSTER_LIST;
                    this.clusters = data.WCP_CLUSTER_LIST;
                    if(this.uploadStatus) {
                        if (this.clusters.indexOf(this.VcCluster) === -1) {
                            this.clusterError = true;
                        } else {
                            this.clusterError = false;
                            this.formGroup.get('cluster').setValue(this.VcCluster);
                        }
                    }
                    this.fetchCluster = true;
                    this.formGroup.get('cluster').enable();
                } else if(data.responseType === 'ERROR') {
                    this.fetchCluster = false;
                    this.errorNotification = 'WCP Enabled Clusters: ' + data.msg;
                }
            } else {
                this.fetchCluster = false;
                this.errorNotification = 'WCP Enabled Clusters: Error in listing clusters';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.fetchCluster = false;
                this.errorNotification = 'WCP Enabled Clusters: ' + error.msg;
            } else {
                this.fetchCluster = false;
                this.errorNotification = 'WCP Enabled Clusters: Error in listing clusters';
            }
        });
    }

    onClusterChange() {
        if (this.formGroup.get('cluster').value !== '') {
            // 1st call to fetch Supervisor List for TMC
            // 2nd call to fetch Workload Networks
            // 3rd call to fetch Namespace list
            // 4th call to get cluster version
            this.getWorkloadNetwork(this.formGroup.get('cluster').value);
        }
    }

    getClusterVersion(clusterName) {
        let vCenterData = {
            "vcenterAddress": "",
            "ssoUser": "",
            "ssoPassword": "",
            "cluster": clusterName,
            "datacenter": "",
        };
        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['ssoUser'] = this.formGroup.get('username').value;
        vCenterData['ssoPassword'] = this.formGroup.get('password').value;
        vCenterData['datacenter'] = this.formGroup.get('datacenter').value;
        this.apiClient.getClusterVersion(vCenterData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.apiClient.clusterVersionsBeta = data.CLUSTER_VERSIONS_BETA;
                    this.apiClient.clusterVersionsAlpha = data.CLUSTER_VERSIONS_ALPHA;
                } else if (data.responseType === 'ERROR') {
                    this.clusterChangeErrorNotification = 'Cluster Version: ' + data.msg;
                }
            } else {
                this.clusterChangeErrorNotification = 'Cluster Version: Error in listing Cluster Versions';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.clusterChangeErrorNotification = 'Cluster Version: ' + error.msg;
            } else {
                this.clusterChangeErrorNotification = 'Cluster Version: Error in listing Cluster Versions';
            }
        });
    }

    getAllNamespaces(clusterName) {
        let vCenterData = {
            "vcenterAddress": "",
            "ssoUser": "",
            "ssoPassword": "",
            "cluster": clusterName,
            "datacenter": "",
        };
        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['ssoUser'] = this.formGroup.get('username').value;
        vCenterData['ssoPassword'] = this.formGroup.get('password').value;
        vCenterData['datacenter'] = this.formGroup.get('datacenter').value;

        this.apiClient.getNamespaces(vCenterData).subscribe((data: any) => {
            if (data && data !== null) {
                let namespace_list = [];
                if (data.responseType === 'SUCCESS') {
                    for(let item of data.NAMESPACES_LIST){
                        if(this.apiClient.allNamespaces.indexOf(item)===-1) namespace_list.push(item);
                    }
                    this.apiClient.allNamespaces.push(...namespace_list);
                    this.getClusterVersion(clusterName);
                } else if (data.responseType === 'ERROR') {
                    this.clusterChangeErrorNotification = 'Fetch Namespaces: ' + data.msg;
                    this.getClusterVersion(clusterName);
                }
            } else {
                this.clusterChangeErrorNotification = 'Fetch Namespaces: Error in listing Namespaces';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.clusterChangeErrorNotification = 'Fetch Namespaces: ' + error.msg;
            } else {
                this.clusterChangeErrorNotification = 'Fetch Namespaces: Error in listing Namespaces';
            }
        });
    }

    getWorkloadNetwork(clusterName) {
        let vCenterData = {
            "vcenterAddress": "",
            "ssoUser": "",
            "ssoPassword": "",
            "datacenter": "",
            "cluster": clusterName
        };
        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['ssoUser'] = this.formGroup.get('username').value;
        vCenterData['ssoPassword'] = this.formGroup.get('password').value;
        vCenterData['datacenter'] = this.formGroup.get('datacenter').value;

        this.apiClient.getWorkloadNetwork(vCenterData).subscribe((data: any) => {
            if (data && data !== null) {
                let wrk_nw_list = [];
                if (data.responseType === 'SUCCESS') {
                    for(let item of data.WORKLOAD_NETWORKS){
                        if(this.apiClient.tkgsWorkloadNetwork.indexOf(item)===-1) wrk_nw_list.push(item);
                    }
                    this.apiClient.tkgsWorkloadNetwork.push(...wrk_nw_list);
                    this.getAllNamespaces(clusterName);
                } else if (data.responseType === 'ERROR') {
                    this.clusterChangeErrorNotification = 'Workload Networks: ' + data.msg;
                }
            } else {
                this.clusterChangeErrorNotification = 'Workload Networks: Error in listing Workload Networks';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.clusterChangeErrorNotification = 'Workload Networks: ' + error.msg;
            } else {
                this.clusterChangeErrorNotification = 'Workload Networks:: Error in listing Workload Networks';
            }
        });
    }


    onDatacenterChange() {
        if (this.formGroup.get('datacenter').value !== '') {
            this.formGroup.get('cluster').disable();
            this.getWcpCluster(this.formGroup.get('datacenter').value);
        }
    }
}
