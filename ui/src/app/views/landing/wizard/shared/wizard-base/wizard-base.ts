/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular imports
import { AfterViewInit, Directive, ElementRef, OnInit, ViewChild } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { Router } from '@angular/router';
import {
    Validators,
} from '@angular/forms';
// Third party imports
import { ClrStepper } from '@clr/angular';
import {Observable, Subscription} from 'rxjs';
import { debounceTime } from 'rxjs/operators';
import { BasicSubscriber } from 'src/app/shared/abstracts/basic-subscriber';
import { Providers, PROVIDERS } from 'src/app/shared/constants/app.constants';
import { APP_ROUTES, Routes } from 'src/app/shared/constants/routes.constants';
import {APIClient} from 'src/app/swagger/api-client.service';
import { FormMetaDataService } from 'src/app/shared/service/form-meta-data.service';
import { FormMetaDataStore } from '../FormMetaDataStore';
import { DataService } from '../../../../../shared/service/data.service';
import { VMCDataService } from '../../../../../shared/service/vmc-data.service';
import { VsphereNsxtDataService } from '../../../../../shared/service/vsphere-nsxt-data.service';
import { VsphereTkgsService } from '../../../../../shared/service/vsphere-tkgs-data.service';

@Directive()
export abstract class WizardBaseDirective extends BasicSubscriber implements AfterViewInit, OnInit {

    APP_ROUTES: Routes = APP_ROUTES;
    PROVIDERS: Providers = PROVIDERS;

    @ViewChild('wizard', { read: ClrStepper, static: true })
    wizard: ClrStepper;

    form: FormGroup;
    errorNotification: string;
    provider: Observable<string>;
    providerType: string;
    infraType: string;
    deploymentPending = false;
    disableDeployButton = false;
    apiClient: APIClient;

    title: string;
    edition: string;
    clusterType: string;
    steps;
//     vsphereSteps = [true, false, false, false, false, false, false, false, false, false, false, false, false];
    vsphereSteps = [true, false, false, false, false, false, false, false, false, false, false, false];
    vmcSteps = [true, false, false, false, false, false, false, false, false, false, false];
//     nsxtSteps = [true, false, false, false, false, false, false, false, false, false, false, false, false];
    nsxtSteps = [true, false, false, false, false, false, false, false, false, false, false, false];
    vsphereTkgsSteps = [true, false, false, false, false, false, false, false, false, false, false, false];
    vsphereTkgsWcpSteps = [true, false, false, false, false, false, false, false, false, false];
    vsphereTkgsNamespaceSteps = [true, false, false, false, false, false, false];
    review = false;
    uploadStatus: boolean;
    subscription: Subscription;

    constructor(
        protected router: Router,
        protected el: ElementRef,
        protected formMetaDataService: FormMetaDataService,
        protected titleService: Title,
        private dataService: DataService,
        private vmcDataService: VMCDataService,
        private nsxtDataService: VsphereNsxtDataService,
        private vsphereTkgsDataService: VsphereTkgsService,
    ) {
        super();
    }

    ngOnInit() {
        if (this.providerType === 'vsphere') {
            if (this.infraType === 'tkgm') {
                this.steps = this.vsphereSteps;
                this.subscription = this.dataService.currentInputFileStatus.subscribe(
                    (uploadStatus) => this.uploadStatus = uploadStatus);
            } else if (this.infraType === 'tkgs') {
                if (this.apiClient.tkgsStage === 'wcp') {
                    this.steps = this.vsphereTkgsWcpSteps;
                } else if (this.apiClient.tkgsStage === 'namespace') {
                    this.steps = this.vsphereTkgsNamespaceSteps;
                }
                this.subscription = this.vsphereTkgsDataService.currentInputFileStatus.subscribe(
                    (uploadStatus) => this.uploadStatus = uploadStatus);
            }
        } else if (this.providerType === 'vsphere-nsxt') {
            this.steps = this.nsxtSteps;
            this.subscription = this.nsxtDataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
        } else {
            this.steps = this.vmcSteps;
            this.subscription = this.vmcDataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
        }
        this.clusterType = 'management';
        // work around an issue within StepperModel
        this.wizard['stepperService']['accordion']['openFirstPanel'] = function() {
            const firstPanel = this.getFirstPanel();
            if (firstPanel) {
                this._panels[firstPanel.id].open = true;
                this._panels[firstPanel.id].disabled = true;
            }
        };
        this.watchFieldsChange();

        FormMetaDataStore.resetStepList();
        FormMetaDataStore.resetFormList();
    }

    ngAfterViewInit(): void {
        this.getStepMetadata();
    }

    watchFieldsChange() {
        const formNames = Object.keys(this.form.controls);
        formNames.forEach((formName) => {
            this.form.controls[formName].valueChanges.pipe(debounceTime(200)).subscribe(() => {
                if (this.form.controls[formName].status === 'VALID') {
                    this.formMetaDataService.saveFormMetadata(formName,
                        this.el.nativeElement.querySelector(`clr-stepper-panel[formgroupname=${formName}]`));
                }
            });
        });
    }
    /**
     * Collect step meta data (title, description etc.) for all steps
     */
    getStepMetadata() {
        let wizard = this.el.nativeElement;
        wizard = wizard.querySelector('form[clrstepper]');
        const panels: any[] = Array.from(wizard.querySelectorAll('clr-stepper-panel'));
        const stepMetadataList = [];
        panels.forEach((panel => {
            const stepMetadata = {};
            const title = panel.querySelector('clr-step-title');
            if (title) {
                stepMetadata['title'] = title.innerText;
            }
            const description = panel.querySelector('clr-step-description');
            if (description) {
                stepMetadata['description'] = description.innerText;
            }
            stepMetadataList.push(stepMetadata);
        }));
        FormMetaDataStore.setStepList(stepMetadataList);
    }

    getWizardValidity(): boolean {
        if (!FormMetaDataStore.getStepList()) {
            return false;
        }
        const totalSteps = FormMetaDataStore.getStepList().length;
        const stepsVisited = this.steps.filter(step => step).length;
        return stepsVisited > totalSteps && this.form.status === 'VALID';
    }

    /**
     * @method navigate
     * @desc helper method to trigger router navigation to specified route
     * @param route - the route to navigate to
     */
    navigate(route: string): void {
        this.router.navigate([route]);
    }

    /**
     * Set the next step to be rendered. In initial wizard walkthrouh,
     * each step content is rendered sequentially, but in subsequent walkthrough,
     * a.k.a. "Edit Configuration" mode, each step widget is no longer re-created,
     * and therefore it reuses its previous component and form states.
     */

    onNextStep() {
        for (let i = 0; i < this.steps.length; i++) {
            if (!this.steps[i]) {
                this.steps[i] = true;
                break;
            }
        }
        this.getStepMetadata();
    }

    uploadNextStep() {
        for (let i = 0; i < this.steps.length; i++ )
        {
            if (!this.steps[i]) {
                this.steps[i] = true;
                this.getStepMetadata();
            }
        }
    }

    vmcUploadNextStep() {
        for (let i = 0; i < (this.steps.length); i++ )
        {
            if (!this.steps[i]) {
                this.steps[i] = true;
                this.getStepMetadata();
            }
        }
    }

    onInfraNextStep() {
        for (let i = 0; i < this.steps.length; i++) {
            if (!this.steps[i]) {
                this.steps[i] = true;
                break;
            }
        }
        this.getStepMetadata();
        this.dataService.changeArcasEnableProxy(
            this.getBooleanFieldValue('vsphereInfraDetailsForm', 'proxySettings'));
        this.apiClient.arcasProxyEnabled = this.getBooleanFieldValue('vsphereInfraDetailsForm', 'proxySettings');
//         if (this.apiClient.arcasProxyEnabled && this.apiClient.providerVisited) {
//             this.form.get('vsphereProviderForm').get('kubernetesOva').clearValidators();
//             this.form.get('vsphereProviderForm').get('kubernetesOva').setValue('');
//             this.form.get('vsphereProviderForm').get('kubernetesOva').updateValueAndValidity();
//         }
//         if (!this.apiClient.arcasProxyEnabled && this.apiClient.providerVisited){
//             this.form.get('vsphereProviderForm').get('kubernetesOva').setValidators([Validators.required]);
//             this.form.get('vsphereProviderForm').get('kubernetesOva').updateValueAndValidity();
//             this.form.get('vsphereProviderForm').get('kubernetesOva').setValue('' || null);
//         }
        this.dataService.changeArcasHttpProxyUrl(
            this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyUrl'));
        this.dataService.changeArcasHttpProxyUsername(
            this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyUsername'));
        this.dataService.changeArcasHttpProxyPassword(
            this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyPassword'));
        this.dataService.changeArcasIsSameAsHttp(
            this.getFieldValue('vsphereInfraDetailsForm', 'isSameAsHttp'));
        this.dataService.changeArcasHttpsProxyUrl(
            this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyUrl'));
        this.dataService.changeArcasHttpsProxyUsername(
            this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyUsername'));
        this.dataService.changeArcasHttpsProxyPassword(
            this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyPassword'));
        this.dataService.changeArcasNoProxy(
            this.getFieldValue('vsphereInfraDetailsForm', 'noProxy'));
    }

    onInfraNextStepVCF() {
        for (let i = 0; i < this.steps.length; i++) {
            if (!this.steps[i]) {
                this.steps[i] = true;
                break;
            }
        }
        this.getStepMetadata();
        this.nsxtDataService.changeArcasEnableProxy(
            this.getBooleanFieldValue('vsphereInfraDetailsForm', 'proxySettings'));
        this.apiClient.arcasProxyEnabled = this.getBooleanFieldValue('vsphereInfraDetailsForm', 'proxySettings');
//         if (this.apiClient.arcasProxyEnabled && this.apiClient.providerVisited) {
//             this.form.get('vsphereProviderForm').get('kubernetesOva').clearValidators();
//             this.form.get('vsphereProviderForm').get('kubernetesOva').setValue('');
//             this.form.get('vsphereProviderForm').get('kubernetesOva').updateValueAndValidity();
//         }
//         if (!this.apiClient.arcasProxyEnabled && this.apiClient.providerVisited){
//             this.form.get('vsphereProviderForm').get('kubernetesOva').setValidators([Validators.required]);
//             this.form.get('vsphereProviderForm').get('kubernetesOva').updateValueAndValidity();
//             this.form.get('vsphereProviderForm').get('kubernetesOva').setValue('' || null);
//         }
        this.nsxtDataService.changeArcasHttpProxyUrl(
            this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyUrl'));
        this.nsxtDataService.changeArcasHttpProxyUsername(
            this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyUsername'));
        this.nsxtDataService.changeArcasHttpProxyPassword(
            this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyPassword'));
        this.nsxtDataService.changeArcasIsSameAsHttp(
            this.getFieldValue('vsphereInfraDetailsForm', 'isSameAsHttp'));
        this.nsxtDataService.changeArcasHttpsProxyUrl(
            this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyUrl'));
        this.nsxtDataService.changeArcasHttpsProxyUsername(
            this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyUsername'));
        this.nsxtDataService.changeArcasHttpsProxyPassword(
            this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyPassword'));
        this.nsxtDataService.changeArcasNoProxy(
            this.getFieldValue('vsphereInfraDetailsForm', 'noProxy'));
    }

    vSphereProviderNextStep() {
//         this.dataService.changeIsAirgapped(this.getBooleanFieldValue('vsphereProviderForm', 'airgapped'));
        this.onNextStep();
    }

    onCustomRepoNextClick() {
        if (this.uploadStatus) {
            let aviSegmentName;
            let aviClusterSegmentName;
            this.dataService.currentAviSegment.subscribe((aviSegment) => aviSegmentName = aviSegment);
            this.dataService.currentAviClusterVipNetworkName.subscribe((aviClusterSegment) => aviClusterSegmentName = aviClusterSegment);
            if (this.apiClient.networks.indexOf(aviSegmentName) === -1) {
                this.apiClient.aviSegmentError = true;
            } else {
                this.apiClient.aviSegmentError = false;
                this.form.get('vsphereAVINetworkSettingForm').get('aviMgmtNetworkName').setValue(aviSegmentName);
            }
            if (this.apiClient.networks.indexOf(aviClusterSegmentName) === -1) {
                this.apiClient.aviClusterSegmentError = true;
            } else {
                this.apiClient.aviClusterSegmentError = false;
                this.form.get('vsphereAVINetworkSettingForm').get('aviClusterVipNetworkName').setValue(aviClusterSegmentName);
            }
        }
        this.onNextStep();
    }

    onVmcTanzuSaasNextClick() {
//         if (this.uploadStatus) {
//             let aviClusterSegmentName;
//             this.vmcDataService.currentAviClusterVipNetworkName.subscribe((aviSegment) => aviClusterSegmentName = aviSegment);
//             if (this.apiClient.networks.indexOf(aviClusterSegmentName) === -1) {
//                 this.apiClient.aviClusterSegmentError = true;
//             } else {
//                 this.apiClient.aviClusterSegmentError = false;
//                 this.form.get('vmcAVINetworkSettingForm').get('aviClusterVipNetworkName').setValue(aviClusterSegmentName);
//             }
//         }
        this.onNextStep();
    }

    onVmcTkgMgmtDataNextClick() {
        if (this.uploadStatus) {
            let mgmtSegment;
            this.vmcDataService.currentMgmtSegment.subscribe((segmentName) => mgmtSegment = segmentName);
            if (this.apiClient.networks.indexOf(mgmtSegment) === -1) {
                this.apiClient.mgmtSegmentError = true;
            } else {
                this.apiClient.mgmtSegmentError = false;
                this.form.get('vmcMgmtNodeSettingForm').get('segmentName').setValue(mgmtSegment);
            }
        }
        this.onNextStep();
    }

    onVmcWrkNextClick() {
        const sharedCluster = this.getFieldValue('vmcSharedServiceNodeSettingForm', 'clusterName');
        this.vmcDataService.changeSharedClusterName(sharedCluster);
        const wrkCluster = this.getFieldValue('vmcWorkloadNodeSettingForm', 'clusterName');
        this.vmcDataService.changeWrkClusterName(wrkCluster);
        this.apiClient.allClusters = [sharedCluster, wrkCluster];
        let enableTanzuExtension;
        this.vmcDataService.currentEnableTanzuExtension.subscribe((enableExtension) => enableTanzuExtension = enableExtension);
        let tkgCluster;
        if (this.uploadStatus && !this.apiClient.toEnabled) {
            if (enableTanzuExtension) {
                this.vmcDataService.currentTkgClusters.subscribe(
                (clusterName) => tkgCluster = clusterName);
                if (this.apiClient.allClusters.indexOf(tkgCluster) === -1) {
                    this.apiClient.tkgClusterError = true;
                } else {
                    this.apiClient.tkgClusterError = false;
                    this.form.get('vmcExtensionSettingForm').get('tanzuExtensionClusters').setValue(tkgCluster);
                }
            }
        } else if (this.uploadStatus && this.apiClient.toEnabled) {
            this.apiClient.tkgClusterError = false;
        }
        this.onNextStep();
    }

    onAVINextClick() {
        if (this.uploadStatus) {
            let tkgMgmtDataSegment;
            this.dataService.currentTkgMgmtDataSegment.subscribe((segmentName) => tkgMgmtDataSegment = segmentName);
            if (this.apiClient.networks.indexOf(tkgMgmtDataSegment) === -1) {
                this.apiClient.tkgMgmtDataSegmentError = true;
            } else {
                this.apiClient.tkgMgmtDataSegmentError = false;
                this.form.get('TKGMgmtDataNWForm').get('TKGMgmtSegmentName').setValue(tkgMgmtDataSegment);
            }
        }
        for (let i = 0; i < this.steps.length; i++) {
            if (!this.steps[i]) {
                this.steps[i] = true;
                break;
            }
        }
        this.getStepMetadata();
        this.dataService.changeAviClusterVipGatewayIp(
            this.getFieldValue('vsphereAVINetworkSettingForm', 'aviClusterVipGatewayIp'));
    }

    onTkgMgmtDataNextClick() {
        if (this.uploadStatus) {
            let mgmtSegment;
            this.dataService.currentMgmtSegment.subscribe((segmentName) => mgmtSegment = segmentName);
            if (this.apiClient.networks.indexOf(mgmtSegment) === -1) {
                this.apiClient.mgmtSegmentError = true;
            } else {
                this.apiClient.mgmtSegmentError = false;
                this.form.get('vsphereMgmtNodeSettingForm').get('segmentName').setValue(mgmtSegment);
            }
        }
        this.onNextStep();
    }

    onVcfTkgMgmtDataNextClick() {
        if (this.uploadStatus) {
            let mgmtSegment;
            this.nsxtDataService.currentMgmtSegment.subscribe((segmentName) => mgmtSegment = segmentName);
            if (this.apiClient.networks.indexOf(mgmtSegment) === -1) {
                this.apiClient.mgmtSegmentError = true;
            } else {
                this.apiClient.mgmtSegmentError = false;
                this.form.get('vsphereMgmtNodeSettingForm').get('segmentName').setValue(mgmtSegment);
            }
        }
        this.onNextStep();
    }
    onMgmtNextClick() {
        if (this.uploadStatus) {
            let tkgWrkDataSegment;
            this.dataService.currentTkgWrkDataSegment.subscribe((segmentName) => tkgWrkDataSegment = segmentName);
            if (this.apiClient.networks.indexOf(tkgWrkDataSegment) === -1) {
                this.apiClient.tkgWrkDataSegmentError = true;
            } else {
                this.apiClient.tkgWrkDataSegmentError = false;
                this.form.get('TKGWorkloadDataNWForm').get('TKGDataSegmentName').setValue(tkgWrkDataSegment);
            }
        }
        this.onNextStep();
    }

    onTkgWrkDataNextClick() {
        if (this.uploadStatus) {
            let wrkSegment;
            this.dataService.currentWrkSegment.subscribe((segmentName) => wrkSegment = segmentName);
            if (this.apiClient.networks.indexOf(wrkSegment) === -1) {
                this.apiClient.wrkSegmentError = true;
            } else {
                this.apiClient.wrkSegmentError = false;
                this.form.get('vsphereWorkloadNodeSettingForm').get('segmentName').setValue(wrkSegment);
            }
        }
        this.onNextStep();
    }

    onWrkNextClick() {
        const sharedCluster = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'clusterName');
        this.dataService.changeSharedClusterName(sharedCluster);
        const wrkCluster = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'clusterName');
        this.dataService.changeWrkClusterName(wrkCluster);
        this.apiClient.allClusters = [sharedCluster, wrkCluster];
        let enableTanzuExtension;
        this.dataService.currentEnableTanzuExtension.subscribe((enableExtension) => enableTanzuExtension = enableExtension);
        let tkgCluster;
        if (this.uploadStatus && !this.apiClient.toEnabled) {
            if (enableTanzuExtension) {
                this.dataService.currentTkgClusters.subscribe(
                    (clusterName) => tkgCluster = clusterName);
                if (this.apiClient.allClusters.indexOf(tkgCluster) === -1) {
                    this.apiClient.tkgClusterError = true;
                } else {
                    this.apiClient.tkgClusterError = false;
                    this.form.get('extensionSettingForm').get('tanzuExtensionClusters').setValue(tkgCluster);
                }
            }
        } else if (this.uploadStatus && this.apiClient.toEnabled) {
            this.apiClient.tkgClusterError = false;
        }
        for (let i = 0; i < this.steps.length; i++) {
            if (!this.steps[i]) {
                this.steps[i] = true;
                break;
            }
        }
        this.getStepMetadata();
    }

    // TKGS Next Methods
    onDnsNext() {
        const dns = this.getFieldValue('dumyForm', 'dnsServer');
        this.vsphereTkgsDataService.changeDnsServer(dns);
        const ntp = this.getFieldValue('dumyForm', 'ntpServer');
        this.vsphereTkgsDataService.changeNtpServer(ntp);
        const searchDomain = this.getFieldValue('dumyForm', 'searchDomain');
        this.vsphereTkgsDataService.changeSearchDomain(searchDomain);
        this.onNextStep();
    }

    onTanzuNext() {
        if (this.uploadStatus) {
            let aviMgmtSegment;
            this.vsphereTkgsDataService.currentAviSegment.subscribe((segmentName) => aviMgmtSegment = segmentName);
            if (this.apiClient.networks.indexOf(aviMgmtSegment) === -1) {
                this.apiClient.aviSegmentError = true;
            } else {
                this.apiClient.aviSegmentError = false;
                this.form.get('vsphereAVINetworkSettingForm').get('aviMgmtNetworkName').setValue(aviMgmtSegment);
            }
            let tkgsVipSegment;
            this.vsphereTkgsDataService.currentAviClusterVipNetworkName.subscribe((segmentName) => tkgsVipSegment = segmentName);
            if (this.apiClient.networks.indexOf(tkgsVipSegment) === -1) {
                this.apiClient.aviClusterSegmentError = true;
            } else {
                this.apiClient.aviClusterSegmentError = false;
                this.form.get('vsphereAVINetworkSettingForm').get('aviClusterVipNetworkName').setValue(tkgsVipSegment);
            }
        }
        this.onNextStep();
    }

    onControlPlaneNext() {
        if (this.uploadStatus) {
            let masterPolicy;
            this.vsphereTkgsDataService.currentMasterStoragePolicy.subscribe(
                (masterStoragePolicy) => masterPolicy = masterStoragePolicy);
            if (this.apiClient.storagePolicies.indexOf(masterPolicy) === -1) {
                this.apiClient.masterPolicyError = true;
            } else {
                this.apiClient.masterPolicyError = false;
                this.form.get('storagePolicyForm').get('masterStoragePolicy').setValue(masterPolicy);
            }
            let ephemeralPolicy;
            this.vsphereTkgsDataService.currentEphemeralStoragePolicy.subscribe(
                (ephemeralStoragePolicy) => ephemeralPolicy = ephemeralStoragePolicy);
            if (this.apiClient.storagePolicies.indexOf(ephemeralPolicy) === -1) {
                this.apiClient.ephemeralPolicyError = true;
            } else {
                this.apiClient.ephemeralPolicyError = false;
                this.form.get('storagePolicyForm').get('ephemeralStoragePolicy').setValue(ephemeralPolicy);
            }
            let imagePolicy;
            this.vsphereTkgsDataService.currentImageStoragePolicy.subscribe(
                (imageStoragePolicy) => imagePolicy = imageStoragePolicy);
            if (this.apiClient.storagePolicies.indexOf(imagePolicy) === -1) {
                this.apiClient.imagePolicyError = true;
            } else {
                this.apiClient.imagePolicyError = false;
                this.form.get('storagePolicyForm').get('imageStoragePolicy').setValue(imagePolicy);
            }
        }
        this.onNextStep();
    }

    onStoragePolicyNext() {
        if (this.uploadStatus) {
            let mgmtSegment;
            this.vsphereTkgsDataService.currentMgmtSegment.subscribe(
                (segmentName) => mgmtSegment = segmentName);
            if (this.apiClient.networks.indexOf(mgmtSegment) === -1) {
                this.apiClient.mgmtSegmentError = true;
            } else {
                this.apiClient.mgmtSegmentError = false;
                this.form.get('mgmtNwForm').get('segmentName').setValue(mgmtSegment);
            }
        }
        this.onNextStep();
    }

    onMgmtNetworkNext() {
        if (this.uploadStatus) {
            let wrkSegment;
            this.vsphereTkgsDataService.currentWrkSegment.subscribe(
                (segmentName) => wrkSegment = segmentName);
            if (this.apiClient.networks.indexOf(wrkSegment) === -1) {
                this.apiClient.wrkSegmentError = true;
            } else {
                this.apiClient.wrkSegmentError = false;
                this.form.get('wrkNwForm').get('segmentName').setValue(wrkSegment);
            }
        }
        this.onNextStep();
    }

    onWrkNWNext() {
//         this.apiClient.wrkNetworks = [this.form.get('wrkNwForm').get('segmentName').value];
        if (this.uploadStatus) {
            let namespaceName;
            this.vsphereTkgsDataService.currentNamespaceName.subscribe(
                (name) => namespaceName = name);
            if(this.apiClient.allNamespaces.indexOf(namespaceName) !== -1) {
                this.form.get('namespaceForm').get('namespaceName').setValue(namespaceName);
            } else {
                this.form.get('namespaceForm').get('namespaceName').setValue('CREATE NEW');
                this.form.get('namespaceForm').get('newNamespaceName').setValue(namespaceName);

                let namespaceContentLib;
                this.vsphereTkgsDataService.currentNamespaceContentLib.subscribe(
                    (contentLib) => namespaceContentLib = contentLib);
                if (this.apiClient.contentLibs.indexOf(namespaceContentLib) !== -1) {
                    this.form.get('namespaceForm').get('contentLib').setValue(namespaceContentLib);
                }

                let vmClassUpload;
                const selectedVmClass = [];
                this.vsphereTkgsDataService.currentNamespaceVmClass.subscribe(
                    (vmClass) => vmClassUpload = vmClass);
                for (let i = 0; i < vmClassUpload.length; i++){
                    if (this.apiClient.namespaceVmClass.indexOf(vmClassUpload[i]) !== -1) {
                        selectedVmClass.push(vmClassUpload[i]);
                    }
                }
                this.form.get('namespaceForm').get('vmClass').setValue(selectedVmClass);

                let storageSpecUpload;
                this.vsphereTkgsDataService.currentStorageSpec.subscribe(
                    (storagePolicy) => storageSpecUpload = storagePolicy);
                this.apiClient.storagePolicy = storageSpecUpload;
                const storagePolicyUpload = [...this.apiClient.storagePolicy.keys()];
                const storageLimitUpload = [...this.apiClient.storagePolicy.values()];
                for (let i = 0; i < storagePolicyUpload.length; i++) {
                    if (this.apiClient.storagePolicies.indexOf(storagePolicyUpload[i]) === -1) {
                        this.apiClient.storagePolicy.delete(storagePolicyUpload[i]);
                    }
                }
                this.form.get('namespaceForm').get('storageSpec').setValue(this.apiClient.storagePolicy);
            }
        }
        this.onNextStep();
    }

    onNamespaceNext() {
        if(this.form.get('namespaceForm').get('namespaceName').value === 'CREATE NEW'){
            this.apiClient.allowedStoragePolicy = [...this.getFieldValue('namespaceForm', 'storageSpec').keys()];
            this.apiClient.selectedVmClass = this.form.get('namespaceForm').get('vmClass').value;
        }
        if (this.uploadStatus) {
            let allowedStorageClass = [];
            const setAllowedStorageClass = [];
            this.vsphereTkgsDataService.currentAllowedStorageClass.subscribe(
                (allowedStorage) => allowedStorageClass = allowedStorage);
            for (let i = 0; i < allowedStorageClass.length; i++) {
                if (this.apiClient.allowedStoragePolicy.indexOf(allowedStorageClass[i]) !== -1) {
                    setAllowedStorageClass.push(allowedStorageClass[i]);
                }
            }
            this.form.get('workloadClusterForm').get('allowedStorageClass').setValue(setAllowedStorageClass);
            let defaultStorageClass;
            this.vsphereTkgsDataService.currentDefaultStorageClass.subscribe(
                (defaultStorage) => defaultStorageClass = defaultStorage);
            if (this.apiClient.allowedStoragePolicy.indexOf(defaultStorageClass) !== -1) {
                this.form.get('workloadClusterForm').get('defaultStorageClass').setValue(defaultStorageClass);
            }
            let nodeStorageClass;
            this.vsphereTkgsDataService.currentNodeStorageClass.subscribe(
                (nodeStorage) => nodeStorageClass = nodeStorage);
            if (this.apiClient.allowedStoragePolicy.indexOf(nodeStorageClass) !== -1) {
                this.form.get('workloadClusterForm').get('nodeStorageClass').setValue(nodeStorageClass);
            }
            let controlPlaneVmClass;
            this.vsphereTkgsDataService.currentControlPlaneVmClass.subscribe(
                (CPVMClass) => controlPlaneVmClass = CPVMClass);
            if (this.apiClient.selectedVmClass.indexOf(controlPlaneVmClass) !== -1) {
                this.form.get('workloadClusterForm').get('controlPlaneVmClass').setValue(controlPlaneVmClass);
            }
            let workerVmClass;
            this.vsphereTkgsDataService.currentWorkerVmClass.subscribe(
                (workerVMClass) => workerVmClass = workerVMClass);
            if (this.apiClient.selectedVmClass.indexOf(workerVmClass) !== -1) {
                this.form.get('workloadClusterForm').get('workerVmClass').setValue(workerVmClass);
            }
            let clusterVersion;
            this.vsphereTkgsDataService.currentClusterVersion.subscribe(
                (version) => clusterVersion = version);
            if (this.apiClient.clusterVersions.indexOf(clusterVersion) !== -1) {
                this.form.get('workloadClusterForm').get('clusterVersion').setValue(clusterVersion);
            }
            if(["v1.20.7+vmware.1-tkg.1.7fb9067", "v1.20.9+vmware.1-tkg.1.a4cee5b", "v1.21.2+vmware.1-tkg.1.ee25d55", "v1.21.6+vmware.1-tkg.1.b3d708a", "v1.21.6+vmware.1-tkg.1"].indexOf(clusterVersion) === -1){
                this.apiClient.clusterVersionMismatch = true;
//                 this.form.get('workloadClusterForm').get('harborSettings').setValue(false);
//                 this.form.get('workloadClusterForm').get('harborSettings').disable();
            }else{
                this.apiClient.clusterVersionMismatch = false;
//                 this.form.get('workloadClusterForm').get('harborSettings').enable();
            }
        }
        this.onNextStep();
    }

    onTkgsWrkNextClick() {
        const wrkCluster = this.getFieldValue('workloadClusterForm', 'clusterName');
        this.vsphereTkgsDataService.changeWrkClusterName(wrkCluster);
        this.apiClient.allClusters = [wrkCluster];
        let enableTanzuExtension;
        this.vsphereTkgsDataService.currentEnableTanzuExtension.subscribe((enableExtension) => enableTanzuExtension = enableExtension);
        let tkgCluster;
        let clusterVersion = this.form.get('workloadClusterForm').get('clusterVersion').value;
        if(["v1.20.7+vmware.1-tkg.1.7fb9067", "v1.20.9+vmware.1-tkg.1.a4cee5b", "v1.21.2+vmware.1-tkg.1.ee25d55", "v1.21.6+vmware.1-tkg.1.b3d708a", "v1.21.6+vmware.1-tkg.1"].indexOf(clusterVersion) === -1){
//             this.form.get('extensionSettingForm').get('tanzuExtensions').setValue(false);
//             enableTanzuExtension = false;
            this.apiClient.clusterVersionMismatch = true;
//             this.form.get('extensionSettingForm').get('tanzuExtensions').disable();
        } else {
            this.apiClient.clusterVersionMismatch = false;
//             this.form.get('extensionSettingForm').get('tanzuExtensions').enable();
        }
        if (this.uploadStatus && !this.apiClient.toEnabled) {
            if (enableTanzuExtension) {
                this.vsphereTkgsDataService.currentTkgClusters.subscribe(
                    (clusterName) => tkgCluster = clusterName);
                if (this.apiClient.allClusters.indexOf(tkgCluster) === -1) {
                    this.apiClient.tkgClusterError = true;
                } else {
                    this.apiClient.tkgClusterError = false;
                    this.form.get('extensionSettingForm').get('tanzuExtensionClusters').setValue(tkgCluster);
                }
            }
        } else if (this.uploadStatus && this.apiClient.toEnabled) {
            this.apiClient.tkgClusterError = false;
        }
        for (let i = 0; i < this.steps.length; i++) {
            if (!this.steps[i]) {
                this.steps[i] = true;
                break;
            }
        }
        this.getStepMetadata();
    }

    onVCDetailsNext() {
        if(this.uploadStatus && this.apiClient.tkgsStage==='namespace') {
            let supervisorClusterName;
            this.subscription = this.vsphereTkgsDataService.currentSupervisorClusterName.subscribe(
                (clusterName) => supervisorClusterName = clusterName);
            if(this.apiClient.tmcMgmtCluster.indexOf(supervisorClusterName) !== -1) {
                this.form.get('tanzuSaasSettingForm').get('clusterName').setValue(supervisorClusterName);
            }
        }
        this.onNextStep();
    }

    checkForWorkloadNetwork() {
        if(this.uploadStatus) {
            let networkName;
            this.subscription = this.vsphereTkgsDataService.currentWorkloadSegmentName.subscribe(
                (network) => networkName = network);
            if(this.apiClient.tkgsWorkloadNetwork.indexOf(networkName) !== -1) {
                this.apiClient.wrkSegmentError = false;
                this.form.get('workloadNetworkForm').get('networkName').setValue(networkName);
            } else {
                this.form.get('workloadNetworkForm').get('networkName').setValue('CREATE NEW');
                this.form.get('workloadNetworkForm').get('newNetworkName').setValue(networkName);
                let portGroup;
                this.vsphereTkgsDataService.currentWrkSegment.subscribe(
                    (pGroup) => portGroup = pGroup);
                if(this.apiClient.networks.indexOf(portGroup)!==-1) {
                    this.apiClient.wrkSegmentError = false;
                    this.form.get('workloadNetworkForm').get('portGroup').setValue(portGroup);
                }
//                 let serviceCidr;
//                 this.vsphereTkgsDataService.currentWrkServiceCidr.subscribe(
//                     (cidr) => serviceCidr = cidr);
//                 this.form.get('workloadNetworkForm').get('serviceCidr').setValue(serviceCidr);
//
//                 let gatewayCidr;
//                 this.vsphereTkgsDataService.currentWrkGateway.subscribe(
//                     (cidr) => gatewayCidr = cidr);
//                 this.form.get('workloadNetworkForm').get('gatewayAddress').setValue(gatewayCidr);
//                 let startIp;
//                 this.vsphereTkgsDataService.currentWrkStartAddress.subscribe(
//                     (start) => startIp = start);
//                 this.form.get('workloadNetworkForm').get('startAddress').setValue(startIp);
//                 let endIp;
//                 this.vsphereTkgsDataService.currentWrkEndAddress.subscribe(
//                     (end) => endIp = end);
//                 this.form.get('workloadNetworkForm').get('endAddress').setValue(endIp);
            }
        }
        this.onNextStep();
    }

    /**
     * Return the current value of the specified field
     * @param formName the form to get the field from
     * @param fieldName the name of the field to get
     */
    getFieldValue(formName, fieldName) {
        return this.form.get(formName) && this.form.get(formName).get(fieldName) && this.form.get(formName).get(fieldName).value || '';
    }

    /**
     * Return the field value as a boolean type
     * @param formName the form to get the field from
     * @param fieldName the name of the field to get
     */
    getBooleanFieldValue(formName, fieldName): boolean {
        return this.getFieldValue(formName, fieldName) ? true : false;
    }

    getStringBoolFieldValue(formName, fieldName): string {
        return this.getFieldValue(formName, fieldName) ? 'true' : 'false';
    }

    /**
     * Return CLI based on latest user input
     */
    // abstract getCli(configPath: string): string;

    /**
     * Notify others that the CLI has changed
     */
    // updateCli(configPath: string) {
    //     const cli = this.getCli(configPath);
    //     Broker.messenger.publish({
    //         type: TkgEventType.CLI_CHANGED,
    //         payload: cli
    //     });
    // }

    /**
     * Converts ES6 map to stringifyable object
     * @param strMap ES6 map that will be converted
     */
    // strMapToObj(strMap: Map<string, string>): { [key: string]: string; } {
    //     const obj = Object.create(null);
    //     for (const [k, v] of strMap) {
    //         obj[k] = v;
    //     }
    //     return obj;
    // }

    onWorkloadDataNextNSXT() {
        if(this.uploadStatus) {
            if(!this.apiClient.tmcEnabled){
                this.form.get('vsphereWorkloadNodeSettingForm').get('tsmSettings').setValue(false);
                this.form.get('vsphereWorkloadNodeSettingForm').get('tsmSettings').setValidators(Validators.min(1));
                this.form.get('vsphereWorkloadNodeSettingForm').get('tsmSettings').updateValueAndValidity();
            }
        }
        this.onNextStep();
    }
}
