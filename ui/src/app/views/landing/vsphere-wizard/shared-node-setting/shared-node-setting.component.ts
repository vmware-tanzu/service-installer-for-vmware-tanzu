/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { TkgEventType } from 'src/app/shared/service/Messenger';
/**
 * Angular Modules
 */
import { Component, OnInit, Input } from '@angular/core';
import {
    Validators,
    FormControl
} from '@angular/forms';
import { Netmask } from 'netmask';
import { distinctUntilChanged, takeUntil } from 'rxjs/operators';
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';

/**
 * App imports
 */
import { PROVIDERS, Providers } from '../../../../shared/constants/app.constants';
import { NodeType, sharedServiceNodeTypes } from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
// import { KUBE_VIP, NSX_ADVANCED_LOAD_BALANCER } from '../../wizard/shared/components/steps/load-balancer/load-balancer-step.component';
import Broker from 'src/app/shared/service/broker';
import { WizardBaseDirective } from 'src/app/views/landing/wizard/shared/wizard-base/wizard-base';
import { AppEdition } from 'src/app/shared/constants/branding.constants';
import {APIClient} from 'src/app/swagger/api-client.service';
import {Subscription} from 'rxjs';
import {DataService} from '../../../../shared/service/data.service';

@Component({
    selector: 'app-shared-node-setting-step',
    templateUrl: './shared-node-setting.component.html',
    styleUrls: ['./shared-node-setting.component.scss']
})
export class SharedNodeSettingComponent extends StepFormDirective implements OnInit {
    @Input() providerType: string;
    @Input() errorNotification: string;

    nodeTypes: Array<NodeType> = [];
    PROVIDERS: Providers = PROVIDERS;
    sharedServiceNodeTypes: Array<NodeType> = sharedServiceNodeTypes;
    nodeType: string;
    additionalNoProxyInfo: string;
    fullNoProxy: string;
    enableNetworkName = true;
    networks = [];
    mgmtSegmentName: string;
    wizardBase: WizardBaseDirective;

    subscription: Subscription;
    private uploadStatus = false;
    private isSameAsHttp;
    private httpProxyUrl;
    private httpProxyUsername;
    private httpProxyPassword;
    private httpsProxyUrl;
    private httpsProxyUsername;
    private httpsProxyPassword;
    private noProxy;
    private enableProxy;

    private controlPlaneSetting;
    private devInstanceType;
    private prodInstanceType;
    private sharedCluster;
    private workerNodeCount;
    private sharedSegment;
    private sharedGateway;
    private sharedClusterCidr;
    private sharedServiceCidr;
    private sharedControlPlaneEndpoint;
    private enableHarbor;
    private harborFqdn;
    private harborPassword;
    private harborCertPath;
    private harborCertKeyPath;
    private sharedBaseImage;
    private sharedBaseImageVersion;
    // Storage Setting Fields
    private sharedCpu;
    private sharedMemory;
    private sharedStorage;
//     controlPlaneEndpointProviders = [KUBE_VIP, NSX_ADVANCED_LOAD_BALANCER];
//     currentControlPlaneEndpoingProvider = KUBE_VIP;
//     controlPlaneEndpointOptional = "";

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                public apiClient: APIClient,
                private  dataService: DataService) {

        super();
        this.nodeTypes = [...sharedServiceNodeTypes];
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl(
            'controlPlaneSetting',
            new FormControl('', [
                Validators.required
            ])
        );
        this.formGroup.addControl(
            'devInstanceType',
            new FormControl('', [
                Validators.required
            ])
        );
        this.formGroup.addControl(
            'prodInstanceType',
            new FormControl('', [
                Validators.required
            ])
        );
        this.formGroup.addControl(
            'clusterName',
            new FormControl('', [
                this.validationService.isValidClusterName(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl(
            'segmentName',
            new FormControl({value: '', disabled:true}, [
                Validators.required])
        );
        this.formGroup.addControl(
            'gatewayAddress',
            new FormControl({value: '', disabled:true}, [
                Validators.required,
                this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('clusterCidr',
            new FormControl('100.96.0.0/11', [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('serviceCidr',
            new FormControl('100.64.0.0/13', [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('baseImage', new FormControl('', [Validators.required]));
        this.formGroup.addControl('baseImageVersion', new FormControl('', [Validators.required]));
        // Custom Storage Settings
        this.formGroup.addControl('sharedCpu',
            new FormControl('', [Validators.min(2)]));
        this.formGroup.addControl('sharedMemory',
            new FormControl('', [Validators.min(8)]));
        this.formGroup.addControl('sharedStorage',
            new FormControl('', [Validators.min(40)]));
        const fieldsMapping = [
            ['httpProxyUrl', ''],
            ['httpProxyUsername', ''],
            ['httpProxyPassword', ''],
            ['httpsProxyUrl', ''],
            ['httpsProxyUsername', ''],
            ['httpsProxyPassword', ''],
            ['noProxy', '']
        ];
        fieldsMapping.forEach(field => {
            this.formGroup.addControl(field[0], new FormControl(field[1], []));
        });
        this.formGroup.addControl('proxySettings', new FormControl(false));
        this.formGroup.addControl('isSameAsHttp', new FormControl(true));

        this.formGroup.addControl('workerNodeCount', new FormControl('',
            [Validators.required]));
        this.formGroup.addControl('harborFqdn', new FormControl('',
            [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('harborPassword', new FormControl('',
            [Validators.required]));
        this.formGroup.addControl('harborCertPath', new FormControl('', [this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('harborCertKeyPath', new FormControl('', [this.validationService.noWhitespaceOnEnds()]));
        this.formGroup['canMoveToNext'] = () => {
            this.setMinWorker();
            return (this.formGroup.valid && this.apiClient.TkgSharedNwValidated);
        };
        setTimeout(_ => {
            this.formGroup.get('controlPlaneSetting').valueChanges.subscribe(data => {
                if (data === 'dev') {
                    this.nodeType = 'dev';
                    this.formGroup.get('devInstanceType').setValidators([
                        Validators.required
                    ]);
                    this.formGroup.controls['prodInstanceType'].clearValidators();
                    this.formGroup.controls['prodInstanceType'].setValue('');
                } else if (data === 'prod') {
                    this.nodeType = 'prod';
                    this.formGroup.controls['prodInstanceType'].setValidators([
                        Validators.required
                    ]);
                    this.formGroup.get('devInstanceType').clearValidators();
                    this.formGroup.controls['devInstanceType'].setValue('');
                }
                this.formGroup.get('devInstanceType').updateValueAndValidity();
                this.formGroup.controls['prodInstanceType'].updateValueAndValidity();
            });
            this.formGroup.get('workerNodeCount').valueChanges.subscribe(data => {
                if(this.apiClient.tmcEnabled){
                    this.formGroup.get('workerNodeCount').setValidators([
                        Validators.required, Validators.min(3)]);
                } else{
                    this.formGroup.get('workerNodeCount').setValidators([
                        Validators.required, Validators.min(1)]);
                }
            });
            if (this.edition !== AppEdition.TKG) {
                this.resurrectField('clusterName',
                    [Validators.required, this.validationService.isValidClusterName(),
                    this.validationService.noWhitespaceOnEnds()],
                    this.formGroup.get('clusterName').value);
                this.resurrectField('segmentName',
                    [Validators.required],
                    this.formGroup.get('segmentName').value);
                }
            this.resurrectField('gatewayAddress',
                [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('gatewayAddress').value);
            this.resurrectField('workerNodeCount',
                [Validators.required],
                this.formGroup.get('workerNodeCount').value);
            this.resurrectField('clusterCidr',
                [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('clusterCidr').value);
            this.resurrectField('serviceCidr',
                [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('serviceCidr').value);
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (!this.uploadStatus) {
                this.subscription = this.dataService.currentArcasEnableProxy.subscribe(
                    (arcasEnableProxy) => this.enableProxy = arcasEnableProxy);
                this.formGroup.get('proxySettings').setValue(this.enableProxy);
                this.subscription = this.dataService.currentArcasHttpProxyUrl.subscribe(
                    (httpProxyUrl) => this.httpProxyUrl = httpProxyUrl);
                this.formGroup.get('httpProxyUrl').setValue(this.httpProxyUrl);
                this.subscription = this.dataService.currentArcasHttpProxyUsername.subscribe(
                    (httpProxyUsername) => this.httpProxyUsername = httpProxyUsername);
                this.formGroup.get('httpProxyUsername').setValue(this.httpProxyUsername);
                this.subscription = this.dataService.currentArcasHttpProxyPassword.subscribe(
                    (httpProxyPassword) => this.httpProxyPassword = httpProxyPassword);
                this.formGroup.get('httpProxyPassword').setValue(this.httpProxyPassword);

                this.subscription = this.dataService.currentArcasIsSameAsHttp.subscribe(
                    (isSameAsHttp) => this.isSameAsHttp = isSameAsHttp);
                this.formGroup.get('isSameAsHttp').setValue(this.isSameAsHttp);
                this.subscription = this.dataService.currentArcasNoProxy.subscribe(
                    (noProxy) => this.noProxy = noProxy);
                this.formGroup.get('noProxy').setValue(this.noProxy);

                this.subscription = this.dataService.currentArcasHttpsProxyUrl.subscribe(
                    (httpsProxyUrl) => this.httpsProxyUrl = httpsProxyUrl);
                this.formGroup.get('httpsProxyUrl').setValue(this.httpsProxyUrl);
                this.subscription = this.dataService.currentArcasHttpsProxyUsername.subscribe(
                    (httpsProxyUsername) => this.httpsProxyUsername = httpsProxyUsername);
                this.formGroup.get('httpsProxyUsername').setValue(this.httpsProxyUsername);
                this.subscription = this.dataService.currentArcasHttpsProxyPassword.subscribe(
                    (httpsProxyPassword) => this.httpsProxyPassword = httpsProxyPassword);
                this.formGroup.get('httpsProxyPassword').setValue(this.httpsProxyPassword);

                this.subscription = this.dataService.currentMgmtSegment.subscribe(
                    (segmentName) => this.sharedSegment = segmentName);
                this.formGroup.get('segmentName').setValue(this.sharedSegment);
                this.subscription = this.dataService.currentMgmtGateway.subscribe(
                    (gatewayIp) => this.sharedGateway = gatewayIp);
                this.formGroup.get('gatewayAddress').setValue(this.sharedGateway);
            }
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentSharedDeploymentType.subscribe(
                    (controlPlaneSetting) => this.controlPlaneSetting = controlPlaneSetting);
                this.formGroup.get('controlPlaneSetting').setValue(this.controlPlaneSetting);

                if (this.controlPlaneSetting === 'dev') {
                    this.subscription = this.dataService.currentSharedDeploymentSize.subscribe(
                        (devInstanceType) => this.devInstanceType = devInstanceType);
                    this.formGroup.get('devInstanceType').setValue(this.devInstanceType);
                } else if (this.controlPlaneSetting === 'prod') {
                    this.subscription = this.dataService.currentSharedDeploymentSize.subscribe(
                        (prodInstanceType) => this.prodInstanceType = prodInstanceType);
                    this.formGroup.get('prodInstanceType').setValue(this.prodInstanceType);
                }
                if (this.devInstanceType === 'custom' || this.prodInstanceType === 'custom'){
                    this.subscription = this.dataService.currentSharedCpu.subscribe(
                        (cpu) => this.sharedCpu = cpu);
                    this.formGroup.get('sharedCpu').setValue(this.sharedCpu);
                    this.subscription = this.dataService.currentSharedStorage.subscribe(
                        (storage) => this.sharedStorage = storage);
                    this.formGroup.get('sharedStorage').setValue(this.sharedStorage);
                    this.subscription = this.dataService.currentSharedMemory.subscribe(
                        (memory) => this.sharedMemory = memory);
                    this.formGroup.get('sharedMemory').setValue(this.sharedMemory);
                }
                this.subscription = this.dataService.currentSharedClusterName.subscribe(
                    (sharedCluster) => this.sharedCluster = sharedCluster);
                this.formGroup.get('clusterName').setValue(this.sharedCluster);
                this.subscription = this.dataService.currentSharedWorkerNodeCount.subscribe(
                    (workerNodeCount) => this.workerNodeCount = workerNodeCount);
                if (this.workerNodeCount >= 1) {
                    this.formGroup.get('workerNodeCount').setValue(this.workerNodeCount);
                }

                this.subscription = this.dataService.currentMgmtSegment.subscribe(
                    (mgmtSegment) => this.sharedSegment = mgmtSegment);
                this.formGroup.get('segmentName').setValue(this.sharedSegment);
                this.subscription = this.dataService.currentMgmtGateway.subscribe(
                    (mgmtGateway) => this.sharedGateway = mgmtGateway);
                this.formGroup.get('gatewayAddress').setValue(this.sharedGateway);
                this.subscription = this.dataService.currentSharedClusterCidr.subscribe(
                    (sharedClusterCidr) => this.sharedClusterCidr = sharedClusterCidr);
                this.formGroup.get('clusterCidr').setValue(this.sharedClusterCidr);
                this.subscription = this.dataService.currentSharedServiceCidr.subscribe(
                    (sharedServiceCidr) => this.sharedServiceCidr = sharedServiceCidr);
                this.formGroup.get('serviceCidr').setValue(this.sharedServiceCidr);
                this.subscription = this.dataService.currentSharedBaseImage.subscribe(
                    (sharedBaseImage) => this.sharedBaseImage = sharedBaseImage);
                this.subscription = this.dataService.currentSharedBaseImageVersion.subscribe(
                    (sharedBaseImageVersion) => this.sharedBaseImageVersion = sharedBaseImageVersion);
                if (this.apiClient.baseImage.indexOf(this.sharedBaseImage) !== -1) {
                    this.formGroup.get('baseImage').setValue(this.sharedBaseImage);
                    // this.getBaseOsVersion();
                }
                if (this.apiClient.baseImageVersion.indexOf(this.sharedBaseImageVersion) !== -1) {
                    this.formGroup.get('baseImageVersion').setValue(this.sharedBaseImageVersion);
                }
                this.subscription = this.dataService.currentSharedEnableProxy.subscribe(
                    (sharedEnableProxy) => this.enableProxy = sharedEnableProxy);
                this.formGroup.get('proxySettings').setValue(this.enableProxy);
                if (this.enableProxy) {
                    this.toggleProxySetting();
                }
                this.subscription = this.dataService.currentSharedHttpProxyUrl.subscribe(
                    (httpProxyUrl) => this.httpProxyUrl = httpProxyUrl);
                this.formGroup.get('httpProxyUrl').setValue(this.httpProxyUrl);
                this.subscription = this.dataService.currentSharedHttpProxyUsername.subscribe(
                    (httpProxyUsername) => this.httpProxyUsername = httpProxyUsername);
                this.formGroup.get('httpProxyUsername').setValue(this.httpProxyUsername);
                this.subscription = this.dataService.currentSharedHttpProxyPassword.subscribe(
                    (httpProxyPassword) => this.httpProxyPassword = httpProxyPassword);
                this.formGroup.get('httpProxyPassword').setValue(this.httpProxyPassword);

                this.subscription = this.dataService.currentSharedIsSameAsHttp.subscribe(
                    (isSameAsHttp) => this.isSameAsHttp = isSameAsHttp);
                this.formGroup.get('isSameAsHttp').setValue(this.isSameAsHttp);
                this.subscription = this.dataService.currentSharedNoProxy.subscribe(
                    (noProxy) => this.noProxy = noProxy);
                this.formGroup.get('noProxy').setValue(this.noProxy);

                this.subscription = this.dataService.currentSharedHttpsProxyUrl.subscribe(
                    (httpsProxyUrl) => this.httpsProxyUrl = httpsProxyUrl);
                this.formGroup.get('httpsProxyUrl').setValue(this.httpsProxyUrl);
                this.subscription = this.dataService.currentSharedHttpsProxyUsername.subscribe(
                    (httpsProxyUsername) => this.httpsProxyUsername = httpsProxyUsername);
                this.formGroup.get('httpsProxyUsername').setValue(this.httpsProxyUsername);
                this.subscription = this.dataService.currenSharedHttpsProxyPassword.subscribe(
                    (httpsProxyPassword) => this.httpsProxyPassword = httpsProxyPassword);
                this.formGroup.get('httpsProxyPassword').setValue(this.httpsProxyPassword);

                this.subscription = this.dataService.currentHarborFqdn.subscribe(
                    (harborFqdn) => this.harborFqdn = harborFqdn);
                this.formGroup.get('harborFqdn').setValue(this.harborFqdn);
                this.subscription = this.dataService.currentHarborPassword.subscribe(
                    (harborPassword) => this.harborPassword = harborPassword);
                this.formGroup.get('harborPassword').setValue(this.harborPassword);
                this.subscription = this.dataService.currentHarborCertPath.subscribe(
                    (harborCertPath) => this.harborCertPath = harborCertPath);
                this.formGroup.get('harborCertPath').setValue(this.harborCertPath);
                this.subscription = this.dataService.currentHarborCertKey.subscribe(
                    (harborCertKeyPath) => this.harborCertKeyPath = harborCertKeyPath);
                this.formGroup.get('harborCertKeyPath').setValue(this.harborCertKeyPath);

//                 let gatewayIp;
//                 this.dataService.currentAviClusterVipGatewayIp.subscribe((gatewayVipIp) => gatewayIp = gatewayVipIp);
//                 const block = new Netmask(gatewayIp);
//                 if (block.contains(this.sharedControlPlaneEndpoint)) {
                this.apiClient.TkgSharedNwValidated = true;
//                     this.errorNotification = '';
//                 } else {
//                     this.apiClient.TkgSharedNwValidated = false;
//                     this.errorNotification = 'Control Plane Endpoint IP in not in AVI Cluster VIP Network';
//                 }
            }
            this.apiClient.TkgSharedNwValidated = true;
        });
        this.networks = this.apiClient.networks;
        }

    buildForm() {
        }

    setSavedDataAfterLoad() {
        if (this.hasSavedData()) {
            this.cardClick(this.getSavedValue('devInstanceType', '') === '' ? 'prod' : 'dev');
            super.setSavedDataAfterLoad();
            // set the node type ID by finding it by the node type name
            let savedNodeType = this.nodeTypes.find(n => n.name === this.getSavedValue('devInstanceType', ''));
            if (savedNodeType) {
                this.formGroup.get('devInstanceType').setValue(savedNodeType.id);
            }
            savedNodeType = this.nodeTypes.find(n => n.name === this.getSavedValue('prodInstanceType', ''));
            if (savedNodeType) {
                this.formGroup.get('prodInstanceType').setValue(savedNodeType.id);
            }
            if (!this.uploadStatus) {
                this.formGroup.get('proxySettings').setValue(this.enableProxy);
                this.formGroup.get('httpProxyUrl').setValue(this.httpProxyUrl);
                this.formGroup.get('httpProxyUsername').setValue(this.httpProxyUsername);
                this.formGroup.get('httpProxyPassword').setValue(this.httpProxyPassword);
                this.formGroup.get('isSameAsHttp').setValue(this.isSameAsHttp);
                this.formGroup.get('httpsProxyUrl').setValue(this.httpsProxyUrl);
                this.formGroup.get('httpsProxyUsername').setValue(this.httpsProxyUsername);
                this.formGroup.get('httpsProxyPassword').setValue(this.httpsProxyPassword);
                this.formGroup.get('noProxy').setValue(this.noProxy);
                this.formGroup.get('harborPassword').setValue('');
            } else {
                this.formGroup.get('httpProxyPassword').setValue('');
                this.formGroup.get('httpsProxyPassword').setValue('');
                this.formGroup.get('harborPassword').setValue('');
            }
        }
    }

    cardClick(envType: string) {
        this.formGroup.controls['controlPlaneSetting'].setValue(envType);
    }

    getEnvType(): string {
        return this.formGroup.controls['controlPlaneSetting'].value;
    }

    setMinWorker() {
        if (this.apiClient.tmcEnabled) {
            this.formGroup.get('workerNodeCount').setValidators([Validators.min(3), Validators.required]);
        } else {
            this.formGroup.get('workerNodeCount').setValidators([Validators.min(1), Validators.required]);
        }
    }

    listenToEvents() {
        const noProxyFieldChangeMap = ['noProxy'];

        noProxyFieldChangeMap.forEach((field) => {
            this.formGroup.get(field).valueChanges.pipe(
                distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr)),
                takeUntil(this.unsubscribe)
                ).subscribe(() => {
                    this.generateFullNoProxy();
                });
        });

        Broker.messenger.getSubject(TkgEventType.AWS_GET_NO_PROXY_INFO)
            .pipe(takeUntil(this.unsubscribe))
            .subscribe(event => {
                this.additionalNoProxyInfo = event.payload.info;
                this.generateFullNoProxy();
        });
    }

    // getBaseOsVersion() {
    //     this.apiClient.getKubeVersions('vsphere').subscribe((data: any) => {
    //         if (data && data !== null) {
    //             if (data.responseType === 'SUCCESS') {
    //                 this.apiClient.sharedBaseImageVersion = data.KUBE_VERSION_LIST;
    //                 this.formGroup.get('baseImageVersion').enable();
    //                 if (this.uploadStatus) {
    //                     if (this.sharedBaseImageVersion !== '') {
    //                         if (this.apiClient.sharedBaseImageVersion.indexOf(this.sharedBaseImageVersion) !== -1) {
    //                             this.formGroup.get('baseImageVersion').setValue(this.sharedBaseImageVersion);
    //                         }
    //                     }
    //                 }
    //             } else if (data.responseType === 'ERROR') {
    //                 this.errorNotification = 'Base OS Version: ' + data.msg;
    //             }
    //         } else {
    //             this.errorNotification = 'Base OS Version: Some Error occurred while fetching Kube Versions';
    //         }
    //     }, (error: any) => {
    //         if (error.responseType === 'ERROR') {
    //             this.errorNotification = 'Base OS Version: ' + error.msg;
    //         } else {
    //             this.errorNotification = 'Base OS Version: Some Error occurred while fetching Kube Versions';
    //         }
    //     });
    // }
    //
    // onBaseOsChange() {
    //     if (this.formGroup.get('baseImage').valid) {
    //         if (this.formGroup.get('baseImage').value !== '') {
    //             this.getBaseOsVersion();
    //         }
    //     }
    // }

    generateFullNoProxy() {
        const noProxy = this.formGroup.get('noProxy');
        if (noProxy && !noProxy.value) {
            this.fullNoProxy = '';
            return;
        }
        const noProxyList = [
            ...noProxy.value.split(','),
            this.additionalNoProxyInfo,
            'localhost',
            '127.0.0.1',
            '.svc',
            '.svc.cluster.local'
        ];
        this.fullNoProxy = noProxyList.filter(elem => elem).join(',');
    }

//     public onTkgSharedValidateClick() {
//         let gatewayIp;
//         this.dataService.currentAviClusterVipGatewayIp.subscribe((gatewayVipIp) => gatewayIp = gatewayVipIp);
//         console.log(gatewayIp);
//         if ((gatewayIp !== '') && this.formGroup.get('controlPlaneEndpointIP').valid) {
//             const controlPlaneIp = this.formGroup.get('controlPlaneEndpointIP').value;
//             const block = new Netmask(gatewayIp);
//             if (block.contains(controlPlaneIp)) {
//                 this.apiClient.TkgSharedNwValidated = true;
//                 this.errorNotification = '';
//             } else {
//                 this.errorNotification = 'Control Plane Endpoint IP in not in AVI Cluster VIP Network';
//                 this.apiClient.TkgSharedNwValidated = false;
//             }
//         }
//     }

//     toggleProxySetting() {
//         const proxySettingFields = [
//             'httpProxyUrl',
//             'httpProxyUsername',
//             'httpProxyPassword',
//             'isSameAsHttp',
//             'httpsProxyUrl',
//             'httpsProxyUsername',
//             'httpsProxyPassword',
//             'noProxy'
//         ];
//         if (this.formGroup.value['proxySettings']) {
//             this.resurrectField('httpProxyUrl', [
//                 Validators.required,
//                 this.validationService.isHttpOrHttps()
//             ], this.formGroup.value['httpProxyUrl']);
//             if (!this.formGroup.value['isSameAsHttp']) {
//                 this.resurrectField('httpsProxyUrl', [
//                     Validators.required,
//                     this.validationService.isHttpOrHttps()
//                 ], this.formGroup.value['httpsProxyUrl']);
//             } else {
//                 const httpsFields = [
//                     'httpsProxyUrl',
//                     'httpsProxyUsername',
//                     'httpsProxyPassword',
//                 ];
//                 httpsFields.forEach((field) => {
//                     this.disarmField(field, true);
//                 });
//             }
//         } else {
//             proxySettingFields.forEach((field) => {
//                 this.disarmField(field, true);
//             });
//         }
//     }

            toggleProxySetting() {
                        const proxySettingFields = [
                            'httpProxyUrl',
                            'httpProxyUsername',
                            'httpProxyPassword',
                            'isSameAsHttp',
                            'httpsProxyUrl',
                            'httpsProxyUsername',
                            'httpsProxyPassword',
                            'noProxy'
                        ];
                        if (this.formGroup.value['proxySettings']) {
                            this.resurrectField('httpProxyUrl', [
                                Validators.required,
                                this.validationService.noWhitespaceOnEnds(),
                                this.validationService.isHttpOrHttps()
                            ], this.formGroup.value['httpProxyUrl']);
                            this.resurrectField('httpProxyUsername', [
                                this.validationService.noWhitespaceOnEnds()
                            ], this.formGroup.value['httpProxyUsername']);
                            this.resurrectField('noProxy', [
                                this.validationService.noWhitespaceOnEnds()
                            ], this.formGroup.value['noProxy']);
                            if (!this.formGroup.value['isSameAsHttp']) {
                                this.resurrectField('httpsProxyUsername', [
                                    this.validationService.noWhitespaceOnEnds()
                                ], this.formGroup.value['httpsProxyUsername']);
                                this.resurrectField('httpsProxyUrl', [
                                    Validators.required,
                                    this.validationService.isHttpOrHttps(),
                                    this.validationService.noWhitespaceOnEnds()
                                ], this.formGroup.value['httpsProxyUrl']);
                            } else {
                                const httpsFields = [
                                    'httpsProxyUrl',
                                    'httpsProxyUsername',
                                    'httpsProxyPassword',
                                ];
                                httpsFields.forEach((field) => {
                                    this.disarmField(field, true);
                                });
                            }
                        } else {
                            proxySettingFields.forEach((field) => {
                                this.disarmField(field, true);
                            });
                        }
                    }

    checkCustom() {
        const storageFields = [
            'sharedCpu',
            'sharedMemory',
            'sharedStorage',
        ];
        if (this.formGroup.get('devInstanceType').valid ||
            this.formGroup.get('prodInstanceType').valid) {
            if (this.formGroup.get('devInstanceType').value === 'custom' ||
                this.formGroup.get('prodInstanceType').value === 'custom') {
                this.resurrectField('sharedCpu', [
                    Validators.required,
                    Validators.min(2)],
                    this.formGroup.value['sharedCpu']);
                this.resurrectField('sharedMemory', [
                    Validators.required,
                    Validators.min(8)],
                    this.formGroup.value['sharedMemory']);
                this.resurrectField('sharedStorage', [
                    Validators.required,
                    Validators.min(40)],
                    this.formGroup.value['sharedStorage']);
            } else {
                storageFields.forEach((field) => {
                    this.disarmField(field, true);
                });
            }
        }
    }
}
