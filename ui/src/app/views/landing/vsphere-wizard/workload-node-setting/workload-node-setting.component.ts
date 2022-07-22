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
import { debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';
import { ClrLoadingState } from '@clr/angular';
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';
/**
 * App imports
 */
import { PROVIDERS, Providers } from '../../../../shared/constants/app.constants';
import { NodeType, vSphereNodeTypes, toNodeTypes } from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
// import { KUBE_VIP, NSX_ADVANCED_LOAD_BALANCER } from '../../wizard/shared/components/steps/load-balancer/load-balancer-step.component';
import Broker from 'src/app/shared/service/broker';
import { AppEdition } from 'src/app/shared/constants/branding.constants';
import {APIClient} from 'src/app/swagger/api-client.service';
import {Subscription} from 'rxjs';
import {DataService} from '../../../../shared/service/data.service';

const SupervisedField = ['veleroCredential', 'veleroTargetLocation', 'clusterGroupName'];

@Component({
    selector: 'app-workload-node-setting-step',
    templateUrl: './workload-node-setting.component.html',
    styleUrls: ['./workload-node-setting.component.scss']
})
export class WorkloadNodeSettingComponent extends StepFormDirective implements OnInit {
    @Input() providerType: string;
    @Input() errorNotification: string;
    nodeTypes: Array<NodeType> = [];
    toNodeTypes: Array<NodeType> = [];
    PROVIDERS: Providers = PROVIDERS;
    vSphereNodeTypes: Array<NodeType> = vSphereNodeTypes;
    toClusterNodeTypes: Array<NodeType> = vSphereNodeTypes;
    nodeType: string;
    additionalNoProxyInfo: string;
    fullNoProxy: string;
    enableNetworkName = true;
    networks = [];

    segmentErrorMsg = 'Workload Segment not found, please update the segment value from the drop-down list';
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
    private proxyCert;
    private enableProxy;
    private controlPlaneSetting;
    private devInstanceType;
    private prodInstanceType;
    private wrkCluster;
    private wrkSegment;
    private wrkGateway;
    private workerNodeCount;
    private wrkClusterCidr;
    private wrkServiceCidr;
    enableTsm = false;

    private exactName;
    private startsWithName;
    private wrkBaseImage;
    private wrkBaseImageVersion;
    // Storage Setting Fields
    private wrkCpu;
    private wrkMemory;
    private wrkStorage;
//     private wrkControlPlaneEndpoint;

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

    // VELERO
    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    public fetchCredential = false;
    public fetchBackupLocation = false;
    public validateCredential = false;
    public validateBackupLocation = false;
    public validatedDataProtection = false;
    public credentialValidationError = "";
    public targetLocationValidationError = "";
    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                public apiClient: APIClient,
                private  dataService: DataService) {

        super();
        this.toClusterNodeTypes = [...vSphereNodeTypes];
        this.nodeTypes = [...vSphereNodeTypes];
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl('workloadClusterSettings',
            new FormControl(false));

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
            new FormControl('', [Validators.required])
        );
        this.formGroup.addControl('workerNodeCount', new FormControl('',
            [Validators.required]));
//         this.formGroup.addControl(
//             'controlPlaneEndpointIP',
//             new FormControl('', [
//                 Validators.required,
//                 this.validationService.isValidIpOrFqdn()
//             ])
//         );
        this.formGroup.addControl(
            'gatewayAddress',
            new FormControl('', [
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
        this.formGroup.addControl('tsmSettings', new FormControl(false));
        this.formGroup.addControl('exactName', new FormControl('', []));
        this.formGroup.addControl('startsWithName', new FormControl('', []));
        // Custom Storage Settings
        this.formGroup.addControl('wrkCpu',
            new FormControl('', [Validators.min(2)]));
        this.formGroup.addControl('wrkMemory',
            new FormControl('', [Validators.min(4)]));
        this.formGroup.addControl('wrkStorage',
            new FormControl('', [Validators.min(20)]));
        this.formGroup.addControl('clusterGroupName', 
            new FormControl('', []));
        this.formGroup.addControl('enableDataProtection',
            new FormControl(false));
        this.formGroup.addControl('veleroCredential', 
            new FormControl('', []));
        this.formGroup.addControl('veleroTargetLocation', 
            new FormControl('', []));
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
        this.formGroup.addControl('proxySettings', new FormControl(false));
        this.formGroup.addControl('isSameAsHttp', new FormControl(true));

        this.formGroup.addControl('clusterAdminUsers',
            new FormControl('',
                [this.validationService.noWhitespaceOnEnds()]
        ));
        this.formGroup.addControl('adminUsers',
            new FormControl('',
                [this.validationService.noWhitespaceOnEnds()]
        ));
        this.formGroup.addControl('editUsers',
            new FormControl('',
                [this.validationService.noWhitespaceOnEnds()]
        ));
        this.formGroup.addControl('viewUsers',
            new FormControl('',
                [this.validationService.noWhitespaceOnEnds()]
        ));

        SupervisedField.forEach(field => {
            this.formGroup.get(field).valueChanges.pipe(
                debounceTime(500),
                distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr)),
                takeUntil(this.unsubscribe))
                .subscribe(() => {
                    if (this.apiClient.wrkDataProtectionEnabled && this.validatedDataProtection){
                        this.validatedDataProtection = false;
                        this.loadingState = ClrLoadingState.DEFAULT;
                    }
                });
        });
        this.formGroup['canMoveToNext'] = () => {
            this.toggleWorkloadClusterSettings();
            if(!this.apiClient.workloadClusterSettings){
                return this.formGroup.valid;
            } else {
                this.setMinWorker();
                //    return true;
                if (this.apiClient.wrkDataProtectionEnabled) {
                    if (this.uploadStatus) {
                        return (this.formGroup.valid && this.apiClient.TkgWrkNwValidated &&
                            !this.rbacErrorClusterAdmin && !this.rbacErrorAdmin &&
                            !this.rbacErrorEdit && !this.rbacErrorView &&
                            this.validatedDataProtection);
                    }
                    return (this.formGroup.valid && this.apiClient.TkgWrkNwValidated &&
                        !this.rbacErrorClusterAdmin && !this.rbacErrorAdmin &&
                        !this.rbacErrorEdit && !this.rbacErrorView &&
                        this.fetchCredential && this.fetchBackupLocation &&
                        this.validatedDataProtection);
                }
                return (this.formGroup.valid && this.apiClient.TkgWrkNwValidated &&
                        !this.rbacErrorClusterAdmin && !this.rbacErrorAdmin &&
                        !this.rbacErrorEdit && !this.rbacErrorView);
            }
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
                if (this.apiClient.workloadClusterSettings){
                    if(this.apiClient.tmcEnabled && this.nodeType === 'prod'){
                        this.formGroup.get('workerNodeCount').setValidators([
                            Validators.required, Validators.min(3)]);
                    }else{
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
            this.formGroup.get('segmentName').valueChanges.subscribe(
                () => this.apiClient.wrkSegmentError = false);
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
                this.formGroup.get('segmentName').setValue('');
            }
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentWrkDeploymentType.subscribe(
                (controlPlaneSetting) => this.controlPlaneSetting = controlPlaneSetting);
                this.formGroup.get('controlPlaneSetting').setValue(this.controlPlaneSetting);
                if (this.controlPlaneSetting === 'dev') {
                    this.subscription = this.dataService.currentWrkDeploymentSize.subscribe(
                        (devInstanceType) => this.devInstanceType = devInstanceType);
                    if (this.apiClient.toEnabled) {
                        if (['large', 'extra-large', 'custom'].indexOf(this.devInstanceType) !== -1) {
                            this.formGroup.get('devInstanceType').setValue(this.devInstanceType);
                        }
                    } else {
                        if (['medium', 'large', 'extra-large', 'custom'].indexOf(this.devInstanceType) !== -1) {
                            this.formGroup.get('devInstanceType').setValue(this.devInstanceType);
                        }
                    }
                } else if (this.controlPlaneSetting === 'prod') {
                    this.subscription = this.dataService.currentWrkDeploymentSize.subscribe(
                        (prodInstanceType) => this.prodInstanceType = prodInstanceType);
                    if (this.apiClient.toEnabled) {
                        if (['large', 'extra-large', 'custom'].indexOf(this.prodInstanceType) !== -1) {
                            this.formGroup.get('prodInstanceType').setValue(this.prodInstanceType);
                        }
                    } else {
                        if (['medium', 'large', 'extra-large', 'custom'].indexOf(this.prodInstanceType) !== -1) {
                            this.formGroup.get('prodInstanceType').setValue(this.prodInstanceType);
                        }
                    }
                }
                if (this.devInstanceType === 'custom' || this.prodInstanceType === 'custom'){
                    this.subscription = this.dataService.currentWrkCpu.subscribe(
                        (cpu) => this.wrkCpu = cpu);
                    this.formGroup.get('wrkCpu').setValue(this.wrkCpu);
                    this.subscription = this.dataService.currentWrkStorage.subscribe(
                        (storage) => this.wrkStorage = storage);
                    this.formGroup.get('wrkStorage').setValue(this.wrkStorage);
                    this.subscription = this.dataService.currentWrkMemory.subscribe(
                        (memory) => this.wrkMemory = memory);
                    this.formGroup.get('wrkMemory').setValue(this.wrkMemory);
                }
                this.subscription = this.dataService.currentWrkClusterName.subscribe(
                    (wrkCluster) => this.wrkCluster = wrkCluster);
                this.formGroup.get('clusterName').setValue(this.wrkCluster);
                this.subscription = this.dataService.currentWrkSegment.subscribe(
                    (wrkSegment) => this.wrkSegment = wrkSegment);
                if (this.apiClient.networks.indexOf(this.wrkSegment) === -1) {
                    this.apiClient.wrkSegmentError = true;
                } else {
                    this.formGroup.get('segmentName').setValue(this.wrkSegment);
                    this.apiClient.wrkSegmentError = false;
                }
                this.subscription = this.dataService.currentWrkGateway.subscribe(
                    (wrkGateway) => this.wrkGateway = wrkGateway);
                this.formGroup.get('gatewayAddress').setValue(this.wrkGateway);
                this.subscription = this.dataService.currentWrkClusterCidr.subscribe(
                    (wrkClusterCidr) => this.wrkClusterCidr = wrkClusterCidr);
                this.formGroup.get('clusterCidr').setValue(this.wrkClusterCidr);
                this.subscription = this.dataService.currentWrkServiceCidr.subscribe(
                    (wrkServiceCidr) => this.wrkServiceCidr = wrkServiceCidr);
                this.formGroup.get('serviceCidr').setValue(this.wrkServiceCidr);

                this.subscription = this.dataService.currentWrkBaseImage.subscribe(
                    (wrkBaseImage) => this.wrkBaseImage = wrkBaseImage);
                this.subscription = this.dataService.currentWrkBaseImageVersion.subscribe(
                    (wrkBaseImageVersion) => this.wrkBaseImageVersion = wrkBaseImageVersion);
                if (this.apiClient.baseImage.indexOf(this.wrkBaseImage) !== -1) {
                    this.formGroup.get('baseImage').setValue(this.wrkBaseImage);
                    // this.getBaseOsVersion();
                }
                if (this.apiClient.baseImageVersion.indexOf(this.wrkBaseImageVersion) !== -1) {
                    this.formGroup.get('baseImageVersion').setValue(this.wrkBaseImageVersion);
                }

                if (this.apiClient.tmcEnabled) {
                    this.subscription = this.dataService.currentEnableTSM.subscribe(
                        (tsmEnable) => this.enableTsm = tsmEnable);
                    this.formGroup.get('tsmSettings').setValue(this.enableTsm);
                    this.toggleTSMSetting();
                    if (this.enableTsm) {
                        this.subscription = this.dataService.currentExactNamespaceExclusion.subscribe(
                            (tsmExactName) => this.exactName = tsmExactName);
                        this.formGroup.get('exactName').setValue(this.exactName);
                        this.subscription = this.dataService.currentStartsWithNamespaceExclusion.subscribe(
                            (tsmStartsWith) => this.startsWithName = tsmStartsWith);
                        this.formGroup.get('startsWithName').setValue(this.startsWithName);
                    }
                } else {
                    this.formGroup.get('tsmSettings').setValue(false);
                    this.formGroup.get('exactName').setValue('');
                    this.formGroup.get('startsWithName').setValue('');
                }
                this.subscription = this.dataService.currentWrkWorkerNodeCount.subscribe(
                    (worker) => this.workerNodeCount = worker);
                if (this.apiClient.tmcEnabled && this.nodeType === 'prod') {
                    if (this.workerNodeCount >= 3) {
                        this.formGroup.get('workerNodeCount').setValue(this.workerNodeCount);
                    }
                } else {
                    if (this.workerNodeCount >= 1) {
                        this.formGroup.get('workerNodeCount').setValue(this.workerNodeCount);
                    }
                }
                this.subscription = this.dataService.currentWrkEnableProxy.subscribe(
                    (enableProxy) => this.enableProxy = enableProxy);
                this.formGroup.get('proxySettings').setValue(this.enableProxy);
                if (this.enableProxy) {
                    this.toggleProxySetting();
                }
                this.subscription = this.dataService.currentWrkHttpProxyUrl.subscribe(
                    (httpProxyUrl) => this.httpProxyUrl = httpProxyUrl);
                this.formGroup.get('httpProxyUrl').setValue(this.httpProxyUrl);
                this.subscription = this.dataService.currentWrkHttpProxyUsername.subscribe(
                    (httpProxyUsername) => this.httpProxyUsername = httpProxyUsername);
                this.formGroup.get('httpProxyUsername').setValue(this.httpProxyUsername);
                this.subscription = this.dataService.currentWrkHttpProxyPassword.subscribe(
                    (httpProxyPassword) => this.httpProxyPassword = httpProxyPassword);
                this.formGroup.get('httpProxyPassword').setValue(this.httpProxyPassword);
                this.subscription = this.dataService.currentWrkIsSameAsHttp.subscribe(
                    (isSameAsHttp) => this.isSameAsHttp = isSameAsHttp);
                this.formGroup.get('isSameAsHttp').setValue(this.isSameAsHttp);
                this.subscription = this.dataService.currentWrkNoProxy.subscribe(
                    (noProxy) => this.noProxy = noProxy);
                this.formGroup.get('noProxy').setValue(this.noProxy);
                this.subscription = this.dataService.currentWrkProxyCert.subscribe(
                    (proxyCert) => this.proxyCert = proxyCert);
                this.formGroup.get('proxyCert').setValue(this.proxyCert);
                this.subscription = this.dataService.currentWrkHttpsProxyUrl.subscribe(
                    (httpsProxyUrl) => this.httpsProxyUrl = httpsProxyUrl);
                this.formGroup.get('httpsProxyUrl').setValue(this.httpsProxyUrl);
                this.subscription = this.dataService.currentWrkHttpsProxyUsername.subscribe(
                    (httpsProxyUsername) => this.httpsProxyUsername = httpsProxyUsername);
                this.formGroup.get('httpsProxyUsername').setValue(this.httpsProxyUsername);
                this.subscription = this.dataService.currentWrkHttpsProxyPassword.subscribe(
                    (httpsProxyPassword) => this.httpsProxyPassword = httpsProxyPassword);
                this.formGroup.get('httpsProxyPassword').setValue(this.httpsProxyPassword);
                this.apiClient.TkgWrkNwValidated = true;
                if (this.apiClient.enableIdentityManagement){
                    this.subscription = this.dataService.currentWrkClusterAdminUsers.subscribe(
                        (clusterAdminUsers) => this.clusterAdminUsers = clusterAdminUsers);
                    this.formGroup.get('clusterAdminUsers').setValue(this.clusterAdminUsers);
                    this.subscription = this.dataService.currentWrkAdminUsers.subscribe(
                        (adminUsers) => this.adminUsers = adminUsers);
                    this.formGroup.get('adminUsers').setValue(this.adminUsers);
                    this.subscription = this.dataService.currentWrkEditUsers.subscribe(
                        (editUsers) => this.editUsers = editUsers);
                    this.formGroup.get('editUsers').setValue(this.editUsers);
                    this.subscription = this.dataService.currentWrkViewUsers.subscribe(
                        (viewUsers) => this.viewUsers = viewUsers);
                    this.formGroup.get('viewUsers').setValue(this.viewUsers);
                }
//                 let gatewayIp;
//                 this.dataService.currentAviClusterVipGatewayIp.subscribe((gatewayVipIp) => gatewayIp = gatewayVipIp);
//                 const block = new Netmask(gatewayIp);
//                 if (block.contains(this.wrkControlPlaneEndpoint)) {
//                     this.apiClient.TkgWrkNwValidated = true;
//                     this.errorNotification = '';
//                 } else {
//                     this.errorNotification = 'Control Plane Endpoint IP in not in AVI Cluster VIP Network';
//                     this.apiClient.TkgWrkNwValidated = false;
//                 }
            }
            this.toggleTSMSetting();
            this.apiClient.TkgWrkNwValidated = true;
            });
        this.networks = this.apiClient.networks;
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
                this.formGroup.get('segmentName').setValue('');
            } else {
                this.formGroup.get('httpProxyPassword').setValue('');
                this.formGroup.get('httpsProxyPassword').setValue('');
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

    toggleTSMSetting() {
        const tsmSettingsFields = [
            'exactName',
            'startsWithName',
        ];
        if (this.apiClient.tmcEnabled && this.formGroup.value['tsmSettings']) {
            this.resurrectField('exactName', [this.validationService.noWhitespaceOnEnds()], this.formGroup.value['exactName']);
            this.resurrectField('startsWithName', [this.validationService.noWhitespaceOnEnds()], this.formGroup.value['startsWithName']);
        } else {
            tsmSettingsFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    // getBaseOsVersion() {
    //     this.apiClient.getKubeVersions('vsphere').subscribe((data: any) => {
    //         if (data && data !== null) {
    //             if (data.responseType === 'SUCCESS') {
    //                 this.apiClient.wrkBaseImageVersion = data.KUBE_VERSION_LIST;
    //                 this.formGroup.get('baseImageVersion').enable();
    //                 if (this.uploadStatus) {
    //                     if (this.wrkBaseImageVersion !== '') {
    //                         if (this.apiClient.wrkBaseImageVersion.indexOf(this.wrkBaseImageVersion) !== -1) {
    //                             this.formGroup.get('baseImageVersion').setValue(this.wrkBaseImageVersion);
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

//     public onTkgWrkValidateClick() {
//         let gatewayIp;
//         this.dataService.currentAviClusterVipGatewayIp.subscribe((gatewayVipIp) => gatewayIp = gatewayVipIp);
//         if ((gatewayIp !== '') && this.formGroup.get('controlPlaneEndpointIP').valid) {
//             const controlPlaneIp = this.formGroup.get('controlPlaneEndpointIP').value;
//             const block = new Netmask(gatewayIp);
//             if (block.contains(controlPlaneIp)) {
//                 this.apiClient.TkgWrkNwValidated = true;
//                 this.errorNotification = '';
//             } else {
//                 this.errorNotification = 'Control Plane Endpoint IP in not in AVI Cluster VIP Network';
//                 this.apiClient.TkgWrkNwValidated = false;
//             }
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
                this.resurrectField('httpsProxyUrl', [
                    Validators.required,
                    this.validationService.isHttpOrHttps(),
                    this.validationService.noWhitespaceOnEnds()
                ], this.formGroup.value['httpsProxyUrl']);
                this.resurrectField('httpsProxyUsername', [
                    this.validationService.noWhitespaceOnEnds()
                ], this.formGroup.value['httpsProxyUsername']);
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
            'wrkCpu',
            'wrkMemory',
            'wrkStorage',
        ];
        if (this.formGroup.get('devInstanceType').valid ||
            this.formGroup.get('prodInstanceType').valid) {
            if (this.formGroup.get('devInstanceType').value === 'custom' ||
                this.formGroup.get('prodInstanceType').value === 'custom') {
                this.resurrectField('wrkCpu', [
                    Validators.required,
                    Validators.min(2)],
                    this.formGroup.value['wrkCpu']);
                this.resurrectField('wrkMemory', [
                    Validators.required,
                    Validators.min(4)],
                    this.formGroup.value['wrkMemory']);
                this.resurrectField('wrkStorage', [
                    Validators.required,
                    Validators.min(20)],
                    this.formGroup.value['wrkStorage']);
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
                        this.dataService.currentWrkDataProtectionCreds.subscribe((cred) => credential = cred);
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
                        this.dataService.currentWrkDataProtectionCreds.subscribe((loc) => backupLocation = loc);
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
        this.apiClient.validateCredentials(tmcData, 'vsphere', 'workload').subscribe((data: any) => {
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
//             this.validateVeleroCredential(this.formGroup.get('veleroCredential').value);
        }
    }

    onVeleroBackupLocationChange() {
        this.validateCredential = false;
        if(this.formGroup.get('veleroTargetLocation').value !== ''){
//             this.validateVeleroBackupLocation(this.formGroup.get('veleroTargetLocation').value);
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
        this.apiClient.validateTargetLocations(tmcData, 'vsphere', 'workload').subscribe((data: any) => {
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
            this.apiClient.wrkDataProtectionEnabled = true;
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
            this.apiClient.wrkDataProtectionEnabled = false;
            dataProtectionFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    getDisabled(): boolean {
        return !(this.formGroup.get('veleroCredential').valid && this.formGroup.get('veleroTargetLocation').valid);
    }

    toggleWorkloadClusterSettings() {
        const mandatoryWorkloadFields = [
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
            'wrkCpu',
            'wrkMemory',
            'wrkStorage',
            'workerNodeCount',
            'clusterAdminUsers',
            'adminUsers',
            'editUsers',
            'viewUsers',
            'tsmSettings',
            'exactName',
            'startsWithName',
            'clusterGroupName',
            'enableDataProtection',
            'veleroCredential',
            'veleroTargetLocation',
            'proxySettings',
            'isSameAsHttp',
            'httpProxyUrl',
            'httpProxyUsername',
            'httpProxyPassword',
            'httpsProxyUrl',
            'httpsProxyUsername',
            'httpsProxyPassword',
            'noProxy',
            'proxyCert',
        ];

        if (this.formGroup.value['workloadClusterSettings']) {
            this.apiClient.workloadClusterSettings = true;
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
            this.resurrectField('wrkCpu', [Validators.min(2)], this.formGroup.value['wrkCpu']);
            this.resurrectField('wrkMemory', [Validators.min(4)], this.formGroup.value['wrkMemory']);
            this.resurrectField('wrkStorage', [Validators.min(20)], this.formGroup.value['wrkStorage']);
            this.resurrectField('workerNodeCount', [Validators.required], this.formGroup.value['workerNodeCount']);
            this.resurrectField('clusterAdminUsers', [this.validationService.noWhitespaceOnEnds()], this.formGroup.value['clusterAdminUsers']);
            this.resurrectField('adminUsers', [this.validationService.noWhitespaceOnEnds()], this.formGroup.value['adminUsers']);
            this.resurrectField('editUsers', [this.validationService.noWhitespaceOnEnds()], this.formGroup.value['editUsers']);
            this.resurrectField('viewUsers', [this.validationService.noWhitespaceOnEnds()], this.formGroup.value['viewUsers']);
        } else {
            this.apiClient.workloadClusterSettings = false;
            mandatoryWorkloadFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

}
