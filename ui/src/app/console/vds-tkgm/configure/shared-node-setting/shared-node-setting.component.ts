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
import { debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';

/**
 * App imports
 */
import { PROVIDERS, Providers } from 'src/app/shared/constants/app.constants';
import { NodeType, vSphereNodeTypes } from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import { StepFormDirective } from 'src/app/views/landing/wizard/shared/step-form/step-form';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import Broker from 'src/app/shared/service/broker';
import { WizardBaseDirective } from 'src/app/views/landing/wizard/shared/wizard-base/wizard-base';
import { AppEdition } from 'src/app/shared/constants/branding.constants';
import { APIClient } from 'src/app/swagger/api-client.service';
import { Subscription } from 'rxjs';
import { DataService } from 'src/app/shared/service/data.service';
import { ClrLoadingState } from '@clr/angular';

const SupervisedField = ['veleroCredential', 'veleroTargetLocation', 'clusterGroupName'];

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
    sharedServiceNodeTypes: Array<NodeType> = vSphereNodeTypes;
    nodeType: string;
    additionalNoProxyInfo: string;
    fullNoProxy: string;
    enableNetworkName = true;
    networks = [];
    mgmtSegmentName: string;
    wizardBase: WizardBaseDirective;

    subscription: Subscription;
    private uploadStatus = false;
    private enableL7 = false;
    private isSameAsHttp;
    private httpProxyUrl;
    private httpProxyUsername;
    private httpProxyPassword;
    private httpsProxyUrl;
    private httpsProxyUsername;
    private httpsProxyPassword;
    private noProxy;
    private proxyCert;
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
    private tkgCustomCert;
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

    public clusterAdminUserSet = new Set();
    public adminUserSet = new Set();
    public editUserSet = new Set();
    public viewUserSet = new Set();
    private clusterAdminUsers;
    private adminUsers;
    private editUsers;
    private viewUsers;
    public rbacErrorClusterAdmin = false;
    public errorRBACClusterAdmin = "";
    public rbacErrorAdmin = false;
    public errorRBACAdmin = "";
    public rbacErrorEdit = false;
    public errorRBACEdit = "";
    public rbacErrorView = false;
    public errorRBACView = "";

    // VELERO via TMC
    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    public fetchCredential = false;
    public fetchBackupLocation = false;
    public validateCredential = false;
    public validateBackupLocation = false;
    public validatedDataProtection = false;
    public credentialValidationError = "";
    public targetLocationValidationError = "";

    // Offline VELERO
    private enableVelero = false;
    private veleroBucket;
    private veleroUsername;
    private veleroPassword;
    private veleroRegion;
    private veleroS3Url;
    private veleroPublicUrl;

    constructor(private validationService: ValidationService,
                public apiClient: APIClient,
                private  dataService: DataService) {

        super();
        this.nodeTypes = [...vSphereNodeTypes];
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl(
            'sharedServicesClusterSettings',
            new FormControl(false)
        );
        this.formGroup.addControl(
            'controlPlaneSetting',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'devInstanceType',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'prodInstanceType',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'clusterName',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'segmentName',
            new FormControl({value: '', disabled:true}, [])
        );
        this.formGroup.addControl(
            'gatewayAddress',
            new FormControl({value: '', disabled:true}, [])
        );
        this.formGroup.addControl(
            'enableL7',
            new FormControl(false, [])
        );

        this.formGroup.addControl(
            'clusterCidr',
            new FormControl('100.96.0.0/11', []))
        ;
        this.formGroup.addControl('serviceCidr',
            new FormControl('100.64.0.0/13', [])
        );
        this.formGroup.addControl(
            'baseImage',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'baseImageVersion',
            new FormControl('', [])
        );
        // Custom Storage Settings
        this.formGroup.addControl(
            'sharedCpu',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'sharedMemory',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'sharedStorage',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'clusterGroupName',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'enableDataProtection',
            new FormControl(false)
        );
        this.formGroup.addControl(
            'veleroCredential',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'veleroTargetLocation',
            new FormControl('', [])
        );
        const fieldsMapping = [
            ['httpProxyUrl', ''],
            ['httpProxyUsername', ''],
            ['httpProxyPassword', ''],
            ['httpsProxyUrl', ''],
            ['httpsProxyUsername', ''],
            ['httpsProxyPassword', ''],
            ['noProxy', ''],
            ['proxyCert', ''],
        ];
        fieldsMapping.forEach(field => {
            this.formGroup.addControl(field[0], new FormControl(field[1], []));
        });
        this.formGroup.addControl(
            'proxySettings',
            new FormControl(false)
        );
        this.formGroup.addControl(
            'isSameAsHttp',
            new FormControl(true)
        );
        this.formGroup.addControl(
            'workerNodeCount',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'tkgCustomCert',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'harborFqdn',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'harborPassword',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'harborCertPath',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'harborCertKeyPath',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'clusterAdminUsers',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'adminUsers',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'editUsers',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'viewUsers',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'enableVelero',
            new FormControl(false)
        );
        this.formGroup.addControl(
            'veleroBucket',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'veleroUsername',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'veleroPassword',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'veleroRegion',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'veleroS3Url',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'veleroPublicUrl',
            new FormControl('', [])
        );

        SupervisedField.forEach(field => {
            this.formGroup.get(field).valueChanges.pipe(
                debounceTime(500),
                distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr)),
                takeUntil(this.unsubscribe))
                .subscribe(() => {
                    if (this.apiClient.sharedDataProtectonEnabled && this.validatedDataProtection){
                        this.validatedDataProtection = false;
                        this.loadingState = ClrLoadingState.DEFAULT;
                    }
                });
        });
        this.formGroup['canMoveToNext'] = () => {
            this.toggleSharedServicesClusterSettings();
            this.findInvalidControls();
            if(!this.apiClient.sharedServicesClusterSettings) return this.formGroup.valid;
            else {
                this.setMinWorker();
                // return true;
                if (this.apiClient.sharedDataProtectonEnabled) {
                    if (this.uploadStatus){
                        return (this.formGroup.valid && this.apiClient.TkgSharedNwValidated &&
                            !this.rbacErrorClusterAdmin && !this.rbacErrorAdmin &&
                            !this.rbacErrorEdit && !this.rbacErrorView &&
                            this.validatedDataProtection);
                    }
                    return (this.formGroup.valid && this.apiClient.TkgSharedNwValidated &&
                            !this.rbacErrorClusterAdmin && !this.rbacErrorAdmin &&
                            !this.rbacErrorEdit && !this.rbacErrorView &&
                            this.fetchCredential && this.fetchBackupLocation &&
                            this.validatedDataProtection);
                } else {
                    return (this.formGroup.valid && this.apiClient.TkgSharedNwValidated &&
                        !this.rbacErrorClusterAdmin && !this.rbacErrorAdmin &&
                        !this.rbacErrorEdit && !this.rbacErrorView);
                }
            }
        };

        setTimeout(_ => {
            if(this.apiClient.sharedServicesClusterSettings) {
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
                    if (this.apiClient.sharedServicesClusterSettings){
                        if(this.apiClient.tmcEnabled && this.nodeType === 'prod'){
                            this.formGroup.get('workerNodeCount').setValidators([
                                Validators.required, Validators.min(3)]);
                        } else{
                            this.formGroup.get('workerNodeCount').setValidators([
                                Validators.required, Validators.min(1)]);
                        }
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
                    this.subscription = this.dataService.currentArcasProxyCertificate.subscribe(
                        (proxyCert) => this.proxyCert = proxyCert);
                    this.formGroup.get('proxyCert').setValue(this.proxyCert);
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

                    this.subscription = this.dataService.currentAviL7Shared.subscribe(
                        (enableL7) => this.enableL7 = enableL7);
                    this.formGroup.get('enableL7').setValue(this.enableL7);

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
                    }
                    if (this.apiClient.baseImageVersion.indexOf(this.sharedBaseImageVersion) !== -1) {
                        this.formGroup.get('baseImageVersion').setValue(this.sharedBaseImageVersion);
                    }
                    this.subscription = this.dataService.currentTkgCustomCert.subscribe(
                        (certs) => this.tkgCustomCert = certs);
                    this.formGroup.get('tkgCustomCert').setValue(this.tkgCustomCert);
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
                    this.subscription = this.dataService.currentSharedProxyCert.subscribe(
                        (proxyCert) => this.proxyCert = proxyCert);
                    this.formGroup.get('proxyCert').setValue(this.proxyCert);
                    this.subscription = this.dataService.currentSharedHttpsProxyUrl.subscribe(
                        (httpsProxyUrl) => this.httpsProxyUrl = httpsProxyUrl);
                    this.formGroup.get('httpsProxyUrl').setValue(this.httpsProxyUrl);
                    this.subscription = this.dataService.currentSharedHttpsProxyUsername.subscribe(
                        (httpsProxyUsername) => this.httpsProxyUsername = httpsProxyUsername);
                    this.formGroup.get('httpsProxyUsername').setValue(this.httpsProxyUsername);
                    this.subscription = this.dataService.currenSharedHttpsProxyPassword.subscribe(
                        (httpsProxyPassword) => this.httpsProxyPassword = httpsProxyPassword);
                    this.formGroup.get('httpsProxyPassword').setValue(this.httpsProxyPassword);
                    if (this.apiClient.enableIdentityManagement){
                        this.subscription = this.dataService.currentSharedClusterAdminUsers.subscribe(
                            (clusterAdminUsers) => this.clusterAdminUsers = clusterAdminUsers);
                        this.formGroup.get('clusterAdminUsers').setValue(this.clusterAdminUsers);
                        this.subscription = this.dataService.currentSharedAdminUsers.subscribe(
                            (adminUsers) => this.adminUsers = adminUsers);
                        this.formGroup.get('adminUsers').setValue(this.adminUsers);
                        this.subscription = this.dataService.currentSharedEditUsers.subscribe(
                            (editUsers) => this.editUsers = editUsers);
                        this.formGroup.get('editUsers').setValue(this.editUsers);
                        this.subscription = this.dataService.currentSharedViewUsers.subscribe(
                            (viewUsers) => this.viewUsers = viewUsers);
                        this.formGroup.get('viewUsers').setValue(this.viewUsers);
                    }
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

                    if(!this.apiClient.tmcEnabled) {
                        this.subscription = this.dataService.currentSharedEnableVelero.subscribe(
                            (enable) => this.enableVelero = enable);
                        this.formGroup.get('enableVelero').setValue(this.enableVelero);
                        if(this.enableVelero) {
                            this.subscription = this.dataService.currentSharedVeleroUsername.subscribe(
                                (username) => this.veleroUsername = username);
                            this.formGroup.get('veleroUsername').setValue(this.veleroUsername);
                            this.subscription = this.dataService.currentSharedVeleroPassword.subscribe(
                                (password) => this.veleroPassword = password);
                            this.formGroup.get('veleroPassword').setValue(this.veleroPassword);
                            this.subscription = this.dataService.currentSharedVeleroBucketName.subscribe(
                                (bucket) => this.veleroBucket = bucket);
                            this.formGroup.get('veleroBucket').setValue(this.veleroBucket);
                            this.subscription = this.dataService.currentSharedVeleroRegion.subscribe(
                                (region) => this.veleroRegion = region);
                            this.formGroup.get('veleroRegion').setValue(this.veleroRegion);
                            this.subscription = this.dataService.currentSharedVeleroS3Url.subscribe(
                                (s3Url) => this.veleroS3Url = s3Url);
                            this.formGroup.get('veleroS3Url').setValue(this.veleroS3Url);
                            this.subscription = this.dataService.currentSharedVeleroPublicUrl.subscribe(
                                (publicUrl) => this.veleroPublicUrl = publicUrl);
                            this.formGroup.get('veleroPublicUrl').setValue(this.veleroPublicUrl);
                        }
                    }
                    this.apiClient.TkgSharedNwValidated = true;
                }
                this.apiClient.TkgSharedNwValidated = true;
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
                this.formGroup.get('proxyCert').setValue(this.proxyCert);
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
        if (this.formGroup.controls['controlPlaneSetting'].value === 'prod' && this.apiClient.tmcEnabled) {
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

    toggleProxySetting() {
        const proxySettingFields = [
            'httpProxyUrl',
            'httpProxyUsername',
            'httpProxyPassword',
            'isSameAsHttp',
            'httpsProxyUrl',
            'httpsProxyUsername',
            'httpsProxyPassword',
            'noProxy',
            'proxyCert',
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
            this.resurrectField('proxyCert', [
            ], this.formGroup.value['proxyCert']);
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

    toggleEnableL7() {
        const aviL7Fields = [];
        if(this.formGroup.value['enableL7']) {

        } else {
            aviL7Fields.forEach((field) => {
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
                    Validators.min(4)],
                    this.formGroup.value['sharedMemory']);
                this.resurrectField('sharedStorage', [
                    Validators.required,
                    Validators.min(20)],
                    this.formGroup.value['sharedStorage']);
            } else {
                storageFields.forEach((field) => {
                    this.disarmField(field, true);
                });
            }
        }
    }


    onClusterAdminFieldChange() {
        if (this.formGroup.get('clusterAdminUsers').valid &&
            this.formGroup.get('clusterAdminUsers').value !== "" &&
            this.formGroup.get('clusterAdminUsers').value !== null) {
            let clusterAdminUsers = this.formGroup.get('clusterAdminUsers').value.split(',');
            this.clusterAdminUserSet.clear();
            for (let item of clusterAdminUsers) {
                item = item.trim();
                if (item === "") continue;
                if (this.clusterAdminUserSet.has(item)) {
                    this.rbacErrorClusterAdmin = true;
                    this.errorRBACClusterAdmin = item + " user is already present in CLUSTER ADMIN ROLE list";
                    return;
                } else if(this.adminUserSet.has(item)) {
                    this.rbacErrorClusterAdmin = true;
                    this.errorRBACClusterAdmin = item + " user is already present in ADMIN ROLE list";
                    return;
                } else if (this.editUserSet.has(item)) {
                    this.rbacErrorClusterAdmin = true;
                    this.errorRBACClusterAdmin = item + " user is already present in EDIT ROLE list";
                    return;
                } else if (this.viewUserSet.has(item)) {
                    this.rbacErrorClusterAdmin = true;
                    this.errorRBACClusterAdmin = item + " user is already present in VIEW ROLE list";
                    return;
                } else {
                    this.clusterAdminUserSet.add(item);
                }
            }
            this.rbacErrorClusterAdmin = false;
        }
    }


    onAdminFieldChange() {
        if (this.formGroup.get('adminUsers').valid &&
            this.formGroup.get('adminUsers').value !== "" &&
            this.formGroup.get('adminUsers').value !== null) {
            let adminUsers = this.formGroup.get('adminUsers').value.split(',');
            this.adminUserSet.clear();
            for (let item of adminUsers) {
                item = item.trim();
                if (item === "") continue;
                if (this.clusterAdminUserSet.has(item)) {
                    this.rbacErrorAdmin = true;
                    this.errorRBACAdmin = item + " user is already present in CLUSTER ADMIN ROLE list";
                    return;
                } else if(this.adminUserSet.has(item)) {
                    this.rbacErrorAdmin = true;
                    this.errorRBACAdmin = item + " user is already present in ADMIN ROLE list";
                    return;
                } else if (this.editUserSet.has(item)) {
                    this.rbacErrorAdmin = true;
                    this.errorRBACAdmin = item + " user is already present in EDIT ROLE list";
                    return;
                } else if (this.viewUserSet.has(item)) {
                    this.rbacErrorAdmin = true;
                    this.errorRBACAdmin = item + " user is already present in VIEW ROLE list";
                    return;
                } else {
                    this.adminUserSet.add(item);
                }
            }
            this.rbacErrorAdmin = false;
        }
    }


    onEditFieldChange() {
        if (this.formGroup.get('editUsers').valid &&
            this.formGroup.get('editUsers').value !== "" &&
            this.formGroup.get('editUsers').value !== null) {
            let editUsers = this.formGroup.get('editUsers').value.split(',');
            this.editUserSet.clear();
            for (let item of editUsers) {
                item = item.trim();
                if (item === "") continue;
                if (this.clusterAdminUserSet.has(item)) {
                    this.rbacErrorEdit = true;
                    this.errorRBACEdit = item + " user is already present in CLUSTER ADMIN ROLE list";
                    return;
                } else if(this.adminUserSet.has(item)) {
                    this.rbacErrorEdit = true;
                    this.errorRBACEdit = item + " user is already present in ADMIN ROLE list";
                    return;
                } else if (this.editUserSet.has(item)) {
                    this.rbacErrorEdit = true;
                    this.errorRBACEdit = item + " user is already present in EDIT ROLE list";
                    return;
                } else if (this.viewUserSet.has(item)) {
                    this.rbacErrorEdit = true;
                    this.errorRBACEdit = item + " user is already present in VIEW ROLE list";
                    return;
                } else {
                    this.editUserSet.add(item);
                }
            }
            this.rbacErrorEdit = false;
        }
    }


    onViewFieldChange() {
        if (this.formGroup.get('viewUsers').valid &&
            this.formGroup.get('viewUsers').value !== "" &&
            this.formGroup.get('viewUsers').value !== null) {
            let viewUsers = this.formGroup.get('viewUsers').value.split(',');
            this.viewUserSet.clear();
            for (let item of viewUsers) {
                item = item.trim();
                if (item === "") continue;
                if (this.clusterAdminUserSet.has(item)) {
                    this.rbacErrorView = true;
                    this.errorRBACView = item + " user is already present in CLUSTER ADMIN ROLE list";
                    return;
                } else if(this.adminUserSet.has(item)) {
                    this.rbacErrorView = true;
                    this.errorRBACView = item + " user is already present in ADMIN ROLE list";
                    return;
                } else if (this.editUserSet.has(item)) {
                    this.rbacErrorView = true;
                    this.errorRBACView = item + " user is already present in EDIT ROLE list";
                    return;
                } else if (this.viewUserSet.has(item)) {
                    this.rbacErrorView = true;
                    this.errorRBACView = item + " user is already present in VIEW ROLE list";
                    return;
                } else {
                    this.viewUserSet.add(item);
                }
            }
            this.rbacErrorView = false;
        }
    }

    fetchVeleroCredentials() {
        let tmcData = {
            "refreshToken": "",
            "instanceUrl": ""
        };
        let refreshToken;
        let instanceUrl;
        this.dataService.currentApiToken.subscribe((token) => refreshToken = token);
        tmcData["refreshToken"] = refreshToken;
        this.dataService.currentInstanceUrl.subscribe((url) => instanceUrl = url);
        tmcData["instanceUrl"] = instanceUrl;
        this.apiClient.fetchCredentials(tmcData, 'vsphere').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.apiClient.dataProtectionCredentials = data.CREDENTIALS;
                    this.fetchCredential = true;
                    this.credentialValidationError = "";
                    if (this.uploadStatus) {
                        let credential;
                        this.dataService.currentSharedDataProtectionCreds.subscribe((cred) => credential = cred);
                        if (this.apiClient.dataProtectionCredentials.indexOf(credential) !== -1){
                            this.formGroup.get('veleroCredential').setValue(credential);
                        }
                    }
                } else if (data.responseType === 'ERROR') {
                    this.fetchCredential = false;
                    this.credentialValidationError = data.msg;
                }
            } else {
                this.fetchCredential = false;
                this.credentialValidationError = "Failed to fetch available credentials";
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.fetchCredential = false;
                this.credentialValidationError = error.msg;
            } else {
                this.fetchCredential = false;
                this.credentialValidationError = "Failed to fetch available credentials";
            }
        });
    }

    fetchVeleroBackupLocations() {
        let tmcData = {
            "refreshToken": "",
            "instanceUrl": ""
        };
        let refreshToken;
        let instanceUrl;
        this.dataService.currentApiToken.subscribe((token) => refreshToken = token);
        tmcData["refreshToken"] = refreshToken;
        this.dataService.currentInstanceUrl.subscribe((url) => instanceUrl = url);
        tmcData["instanceUrl"] = instanceUrl;
        this.apiClient.fetchTargetLocations(tmcData, 'vsphere').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.apiClient.dataProtectionTargetLocations = data.TARGET_LOCATIONS;
                    this.fetchBackupLocation = true;
                    this.targetLocationValidationError = "";
                    if (this.uploadStatus) {
                        let backupLocation;
                        this.dataService.currentSharedDataProtectionTargetLocation.subscribe((loc) => backupLocation = loc);
                        if (this.apiClient.dataProtectionTargetLocations.indexOf(backupLocation) !== -1){
                            this.formGroup.get('veleroTargetLocation').setValue(backupLocation);
                        }
                    }
                } else if (data.responseType === 'ERROR') {
                    this.fetchBackupLocation = false;
                    this.targetLocationValidationError = data.msg;
                }
            } else {
                this.fetchBackupLocation = false;
                this.targetLocationValidationError = "Failed to fetch available backup locations";
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.fetchBackupLocation = false;
                this.targetLocationValidationError = error.msg;
            } else {
                this.fetchBackupLocation = false;
                this.targetLocationValidationError = "Failed to fetch available backup locations";
            }
        });
    }

    validateVeleroCredential(credential, targetLocation, clusterGroup) {
        let tmcData = {
            "refreshToken": "",
            "instanceUrl": "",
            "credential": credential,
            "targetLocation": targetLocation,
            "clusterGroupName": clusterGroup
        };
        let refreshToken;
        let instanceUrl;
        this.dataService.currentApiToken.subscribe((token) => refreshToken = token);
        tmcData["refreshToken"] = refreshToken;
        this.dataService.currentInstanceUrl.subscribe((url) => instanceUrl = url);
        tmcData["instanceUrl"] = instanceUrl;
        this.apiClient.validateCredentials(tmcData, 'vsphere', 'shared').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.credentialValidationError = "";
                    this.validateVeleroBackupLocation(credential, targetLocation, clusterGroup);
                } else if (data.responseType === 'ERROR') {
                    this.validatedDataProtection = false;
                    this.credentialValidationError = data.msg;
                    this.loadingState = ClrLoadingState.DEFAULT;
                }
            } else {
                this.validatedDataProtection = false;
                this.credentialValidationError = "Failed to fetch available credentials";
                this.loadingState = ClrLoadingState.DEFAULT;
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.validatedDataProtection = false;
                this.credentialValidationError = error.msg;
                this.loadingState = ClrLoadingState.DEFAULT;
            } else {
                this.validatedDataProtection = false;
                this.credentialValidationError = "Failed to fetch available credentials";
                this.loadingState = ClrLoadingState.DEFAULT;
            }
        });
    }

    onValidateDataProtection() {
        if (this.formGroup.get('veleroCredential').value !== '' &&
            this.formGroup.get('veleroTargetLocation').value !== '' &&
            this.formGroup.get('clusterGroupName').value !== ''){
            this.loadingState = ClrLoadingState.LOADING;
            this.validateVeleroCredential(this.formGroup.get('veleroCredential').value,
                this.formGroup.get('veleroTargetLocation').value, this.formGroup.get('clusterGroupName').value);
        }
    }

    onVeleroCredentialChange() {
        this.validateCredential = false;
        if(this.formGroup.get('veleroCredential').value !== ''){
        }
    }

    onVeleroBackupLocationChange() {
        this.validateCredential = false;
        if(this.formGroup.get('veleroTargetLocation').value !== ''){
        }
    }

    validateVeleroBackupLocation(credential, backupLocation, clusterGroupName) {
        let tmcData = {
            "refreshToken": "",
            "instanceUrl": "",
            "credential": credential,
            "backupLocation": backupLocation,
            "clusterGroupName": clusterGroupName
        };
        let refreshToken;
        let instanceUrl;
        this.dataService.currentApiToken.subscribe((token) => refreshToken = token);
        tmcData["refreshToken"] = refreshToken;
        this.dataService.currentInstanceUrl.subscribe((url) => instanceUrl = url);
        tmcData["instanceUrl"] = instanceUrl;
        this.apiClient.validateTargetLocations(tmcData, 'vsphere', 'shared').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.validatedDataProtection = true;
                    this.targetLocationValidationError = "";
                    this.loadingState = ClrLoadingState.DEFAULT;
                } else if (data.responseType === 'ERROR') {
                    this.validatedDataProtection = false;
                    this.targetLocationValidationError = data.msg;
                    this.loadingState = ClrLoadingState.DEFAULT;
                }
            } else {
                this.validatedDataProtection = false;
                this.targetLocationValidationError = "Failed to fetch available backup locations";
                this.loadingState = ClrLoadingState.DEFAULT;
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.validatedDataProtection = false;
                this.targetLocationValidationError = error.msg;
                this.loadingState = ClrLoadingState.DEFAULT;
            } else {
                this.validatedDataProtection = false;
                this.targetLocationValidationError = "Failed to fetch available backup locations";
                this.loadingState = ClrLoadingState.DEFAULT;
            }
        });
    }

    toggleEnableDataProtection() {
        const dataProtectionFields = [
            'veleroCredential',
            'veleroTargetLocation',
        ];
        if (this.formGroup.value['enableDataProtection']) {
            this.apiClient.sharedDataProtectonEnabled = true;
            this.resurrectField('veleroCredential', [
                Validators.required
            ], this.formGroup.value['veleroCredential']);
            this.resurrectField('veleroTargetLocation', [
                Validators.required
            ], this.formGroup.value['veleroTargetLocation']);
            this.resurrectField('clusterGroupName', [
                Validators.required
            ], this.formGroup.value['clusterGroupName']);
            this.fetchVeleroCredentials();
            this.fetchVeleroBackupLocations();
        } else {
            this.apiClient.sharedDataProtectonEnabled = false;
            dataProtectionFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    toggleEnableVelero() {
        const veleroFields = [
            'veleroUsername',
            'veleroPassword',
            'veleroBucket',
            'veleroRegion',
            'veleroS3Url',
            'veleroPublicUrl'
        ];
        if (!this.apiClient.tmcEnabled && this.formGroup.value['enableVelero']) {
            this.resurrectField('veleroUsername', [
                Validators.required
            ], this.formGroup.value['veleroUsername']);
            this.resurrectField('veleroPassword', [
                Validators.required
            ], this.formGroup.value['veleroPassword']);
            this.resurrectField('veleroBucket', [
                Validators.required
            ], this.formGroup.value['veleroBucket']);

            this.resurrectField('veleroRegion', [
                Validators.required
            ], this.formGroup.value['veleroRegion']);
            this.resurrectField('veleroS3Url', [
                Validators.required, this.validationService.isHttpOrHttps()
            ], this.formGroup.value['veleroS3Url']);
            this.resurrectField('veleroPublicUrl', [
                Validators.required, this.validationService.isHttpOrHttps()
            ], this.formGroup.value['veleroPublicUrl']);
        } else {
            this.apiClient.sharedDataProtectonEnabled = false;
            veleroFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    getDisabled(): boolean {
        return !(this.formGroup.get('veleroCredential').valid && this.formGroup.get('veleroTargetLocation').valid);
    }

    toggleSharedServicesClusterSettings() {
        const mandatorySharedServicesFields = [
            'controlPlaneSetting',
            'devInstanceType',
            'prodInstanceType',
            'clusterName',
            'segmentName',
            'gatewayAddress',
            'clusterCidr',
            'serviceCidr',
            'baseImage',
            'baseImageVersion',
            'sharedCpu',
            'sharedMemory',
            'sharedStorage',
            'workerNodeCount',
            'harborFqdn',
            'harborPassword',
            'clusterAdminUsers',
            'adminUsers',
            'editUsers',
            'viewUsers',
            'clusterGroupName',
            'enableDataProtection',
            'veleroCredential',
            'veleroTargetLocation',
            'httpProxyUrl',
            'httpProxyUsername',
            'httpProxyPassword',
            'httpsProxyUrl',
            'httpsProxyUsername',
            'httpsProxyPassword',
            'noProxy',
            'proxyCert',
            'proxySettings',
            'isSameAsHttp',
            'harborCertPath',
            'harborCertKeyPath',
            'enableVelero',
            'veleroUsername',
            'veleroPassword',
            'veleroBucket',
            'veleroRegion',
            'veleroS3Url',
            'veleroPublicUrl',
            'tkgCustomCert'
        ];

        if (this.formGroup.value['sharedServicesClusterSettings']) {
            this.apiClient.sharedServicesClusterSettings = true;
            this.resurrectField('controlPlaneSetting', [Validators.required], this.formGroup.value['controlPlaneSetting']);
            this.resurrectField('devInstanceType', [], this.formGroup.value['devInstanceType']);
            this.resurrectField('prodInstanceType', [], this.formGroup.value['prodInstanceType']);
            this.resurrectField('clusterName', [Validators.required, this.validationService.isValidClusterName(), this.validationService.noWhitespaceOnEnds()], this.formGroup.value['clusterName']);
            this.resurrectField('segmentName', [Validators.required], this.formGroup.value['segmentName']);
            this.resurrectField('gatewayAddress', [Validators.required, this.validationService.isValidIpNetworkSegment(), this.validationService.noWhitespaceOnEnds()], this.formGroup.value['gatewayAddress']);
            this.resurrectField('clusterCidr', [Validators.required, this.validationService.noWhitespaceOnEnds(), this.validationService.isValidIpNetworkSegment()], this.formGroup.value['clusterCidr']);
            this.resurrectField('serviceCidr', [Validators.required, this.validationService.isValidIpNetworkSegment(), this.validationService.noWhitespaceOnEnds()], this.formGroup.value['serviceCidr']);
            this.resurrectField('baseImage', [Validators.required], this.formGroup.value['baseImage']);
            this.resurrectField('baseImageVersion', [Validators.required], this.formGroup.value['baseImageVersion']);
            this.resurrectField('sharedCpu', [Validators.min(2)], this.formGroup.value['sharedCpu']);
            this.resurrectField('sharedMemory', [Validators.min(4)], this.formGroup.value['sharedMemory']);
            this.resurrectField('sharedStorage', [Validators.min(20)], this.formGroup.value['sharedStorage']);
            this.resurrectField('workerNodeCount', [Validators.required], this.formGroup.value['workerNodeCount']);
            this.resurrectField('harborFqdn', [Validators.required, this.validationService.noWhitespaceOnEnds()], this.formGroup.value['harborFqdn']);
            this.resurrectField('harborPassword', [Validators.required], this.formGroup.value['harborPassword']);
            this.resurrectField('harborCertPath', [this.validationService.noWhitespaceOnEnds()], this.formGroup.value['harborCertPath']);
            this.resurrectField('harborCertKeyPath', [this.validationService.noWhitespaceOnEnds()], this.formGroup.value['harborCertKeyPath']);
            this.resurrectField('clusterAdminUsers', [this.validationService.noWhitespaceOnEnds()], this.formGroup.value['clusterAdminUsers']);
            this.resurrectField('adminUsers', [this.validationService.noWhitespaceOnEnds()], this.formGroup.value['adminUsers']);
            this.resurrectField('editUsers', [this.validationService.noWhitespaceOnEnds()], this.formGroup.value['editUsers']);
            this.resurrectField('viewUsers', [this.validationService.noWhitespaceOnEnds()], this.formGroup.value['viewUsers']);
        } else {
            this.apiClient.sharedServicesClusterSettings = false;
            mandatorySharedServicesFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    public findInvalidControls() {
        const controls = this.formGroup.controls;
        for (const name in controls) {
            if (controls[name].invalid) {
                console.log(name);
                console.log(controls[name].errors);
            }
        }
    }

}
