
/**
 * Angular Modules
 */
import { Component, OnInit } from '@angular/core';
import { FormControl, Validators } from '@angular/forms';
import { debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';
import {ClrLoadingState} from '@clr/angular';
/**
 * App imports
 */
import { TkgEventType } from 'src/app/shared/service/Messenger';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { StepFormDirective } from 'src/app/views/landing/wizard/shared/step-form/step-form';
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';
import Broker from 'src/app/shared/service/broker';
import {Subscription} from "rxjs";
import {APIClient} from 'src/app/swagger/api-client.service';
import {VsphereTkgsService} from '../../../../shared/service/vsphere-tkgs-data.service';


@Component({
    selector: 'app-tanzuSaas-step',
    templateUrl: './tanzu-saas-setting-step.component.html',
    styleUrls: ['./tanzu-saas-setting-step.component.scss']
})
export class TanzuSaasStepComponent extends StepFormDirective implements OnInit {
    
    SupervisedField = ['refreshToken', 'tmcInstanceURL'];

    enableNetworkName = true;
    subscription: Subscription;
    uploadStatus: boolean;
    private enableTmc: boolean;
    private refreshToken: string;
    private tmcInstanceURL;
    private supervisorClusterName: string;
    private supervisorClusterGroupName: string;
    private enableTo: boolean;
    private toRefreshToken: string;
    private toUrl: string;
    connected: boolean = false;
    arcasHttpUsername: string;
    arcasHttpsUsername: string;
    arcasHttpUrl: string;
    arcasHttpsUrl: string
    arcasSameAsHttp: boolean;
    arcasHttpPassword: string;
    arcasHttpsPassword: string;
    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    validateRefreshToken = false;
    tmcClusterValid = true;

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                private dataService: VsphereTkgsService,
                private apiClient: APIClient) {

        super();
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl('tmcSettings', new FormControl(false));
        this.formGroup.addControl('refreshToken', new FormControl('', []));
        this.formGroup.addControl('tmcInstanceURL', new FormControl('', []));
        this.formGroup.addControl('clusterName', new FormControl('', []));
        this.formGroup.addControl('clusterGroupName', new FormControl('', []));
        this.formGroup.addControl('toSettings', new FormControl(false));
        this.formGroup.addControl('toUrl', new FormControl('', []));
        this.formGroup.addControl('toRefreshToken', new FormControl('', []));

        this.SupervisedField.forEach(field => {
            this.formGroup.get(field).valueChanges.pipe(
                debounceTime(500),
                distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr)),
                takeUntil(this.unsubscribe))
                .subscribe(() => {
                    this.connected = false;
                    this.loadingState = ClrLoadingState.DEFAULT;
                });
        });
        this.formGroup['canMoveToNext'] = () => {
            if (this.formGroup.get('tmcSettings').value) {
                return this.formGroup.valid && this.connected && this.tmcClusterValid;
            } else {
                return this.formGroup.valid;
            }
        };
        setTimeout(_ => {
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentEnableTMC.subscribe(
                    (enableTmc) => this.enableTmc = enableTmc);
                this.formGroup.get('tmcSettings').setValue(this.enableTmc);
                if (this.enableTmc) {
                    this.apiClient.tmcEnabled = true;
                    this.subscription = this.dataService.currentApiToken.subscribe(
                        (refreshToken) => this.refreshToken = refreshToken);
                    this.formGroup.get('refreshToken').setValue(this.refreshToken);
                    if(this.apiClient.tkgsStage === 'namespace'){
                        this.getSupervisorClustersForTMC(this.refreshToken);
                    }
                    this.subscription = this.dataService.currentInstanceUrl.subscribe(
                        (url) => this.tmcInstanceURL = url);
                    this.formGroup.get('tmcInstanceURL').setValue(this.tmcInstanceURL);
                    if(this.apiClient.tkgsStage === 'wcp'){
                        this.subscription = this.dataService.currentSupervisorClusterName.subscribe(
                            (clusterName) => this.supervisorClusterName = clusterName);
                        this.formGroup.get('clusterName').setValue(this.supervisorClusterName);
                        this.subscription = this.dataService.currentSupervisorClusterGroupName.subscribe(
                            (clusterGroupName) => this.supervisorClusterGroupName = clusterGroupName);
                        this.formGroup.get('clusterGroupName').setValue(this.supervisorClusterGroupName);
                    }
//                     if (this.apiClient.tkgStage === 'wcp') {
//                         this.formGroup.get('clusterName').setValue(this.supervisorClusterName);
//                     } else if (this.apiClient.tkgStage === 'namespace') {
//                         if(this.apiClient.tmcMgmtCluster.indexOf(this.supervisorClusterName) === -1)
//                     }
                    this.subscription = this.dataService.currentEnableTO.subscribe(
                        (enableTo) => this.enableTo = enableTo);
                    this.formGroup.get('toSettings').setValue(this.enableTo);
                    if (this.enableTo) {
                        this.apiClient.toEnabled = true;
                        this.subscription = this.dataService.currentTOApiToken.subscribe(
                            (toRefreshToken) => this.toRefreshToken = toRefreshToken);
                        this.formGroup.get('toRefreshToken').setValue(this.toRefreshToken);
                        this.subscription = this.dataService.currentTOUrl.subscribe(
                            (toUrl) => this.toUrl = toUrl);
                        this.formGroup.get('toUrl').setValue(this.toUrl);
                    } else {
                        this.apiClient.toEnabled = false;
                    }
                } else {
                    this.apiClient.tmcEnabled = false;
                    this.apiClient.toEnabled = false;
                }
            }
        });
    }

    getSupervisorClustersForTMC(refreshToken) {
        this.apiClient.getSupervisorClustersForTMC(refreshToken).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.apiClient.tmcMgmtCluster = data.NAMESPACES_LIST;
                    this.errorNotification = '';
                    if(this.uploadStatus){
                        this.subscription = this.dataService.currentSupervisorClusterName.subscribe(
                            (clusterName) => this.supervisorClusterName = clusterName);
                        if(this.apiClient.tmcMgmtCluster.indexOf(this.supervisorClusterName) !== -1){
                            this.formGroup.get('clusterName').setValue(this.supervisorClusterName);
                        }
                    }
                } else if(data.responseType === 'ERROR') {
                    this.errorNotification = 'TMC Supervisor Clusters: ' + data.msg;
                }
            } else {
                this.errorNotification = 'TMC Supervisor Clusters: Error in listing TMC Supervisor Clusters';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.errorNotification = 'TMC Supervisor Clusters: ' + error.msg;
            } else {
                this.errorNotification = 'TMC Supervisor Clusters: Error in listing TMC Supervisor Clusters';
            }
        });
    }

    onTMCRefreshTokenChange(){
        if(this.apiClient.tkgsStage === 'namespace'){
            if (this.formGroup.get('refreshToken').value !== '') {
                this.getSupervisorClustersForTMC(this.formGroup.get('refreshToken').value);
            }
        }
        // if(this.apiClient.tkgsStage === 'wcp'){
        //     if(this.formGroup.get('refreshToken').value !== '' &&
        //         this.formGroup.get('tmcInstanceURL').value !== '') {
        //         this.fetchClusterGroups(this.formGroup.get('refreshToken').value, 
        //             this.formGroup.get('tmcInstanceURL').value);
        //     }
        // }
    }

    toggleTMCSetting() {
        const tmcSettingsFields = [
            'refreshToken',
            'tmcInstanceURL',
            'clusterName',
            'clusterGroupName',
            'toSettings',
            'toUrl',
            'toRefreshToken',
        ];
        if (this.formGroup.value['tmcSettings']) {
            this.apiClient.tmcEnabled = true;
            this.resurrectField('refreshToken', [
                Validators.required,
                this.validationService.noWhitespaceOnEnds()
            ], this.formGroup.value['refreshToken']);
            this.resurrectField('clusterName', [
                Validators.required,
                this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidClusterName()
                ], this.formGroup.value['clusterName']);
            this.resurrectField('clusterGroupName', [
                ], this.formGroup.value['clusterGroupName']);

            this.resurrectField('tmcInstanceURL', [
                Validators.required,
                this.validationService.noWhitespaceOnEnds(),
                this.validationService.isHttpOrHttps()
            ], this.formGroup.value['tmcInstanceURL']);
        } else {
            this.apiClient.tmcEnabled = false;
            this.apiClient.toEnabled = false;
            tmcSettingsFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    toggleTOSetting() {
        const toSettingsFields = [
            'toUrl',
            'toRefreshToken',
        ];
        if (this.formGroup.value['toSettings']) {
            this.apiClient.toEnabled = true;
            this.resurrectField('toUrl', [
                Validators.required, this.validationService.isHttpOrHttps(),
                this.validationService.noWhitespaceOnEnds()
            ], this.formGroup.value['toUrl']);
            this.resurrectField('toRefreshToken',
                [Validators.required, this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['toRefreshToken']);
        } else {
            this.apiClient.toEnabled = false;
            toSettingsFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    getDisabled(): boolean {
        return !(this.formGroup.get('refreshToken').valid);
    }

//     getArcasHttpProxyParam() {
//         this.dataService.currentArcasHttpProxyUsername.subscribe((httpUsername) => this.arcasHttpUsername = httpUsername);
//         if (this.arcasHttpUsername !== '') {
//             this.dataService.currentArcasHttpProxyUrl.subscribe((httpUrl) => this.arcasHttpUrl = httpUrl);
//             this.dataService.currentArcasHttpProxyPassword.subscribe((httpPassword) => this.arcasHttpPassword = httpPassword);
//             let httpProxyVal = 'http://' + this.arcasHttpUsername + ':' + this.arcasHttpPassword +'@'+ this.arcasHttpUrl.substr(7);
//             return httpProxyVal;
//         } else {
//             this.dataService.currentArcasHttpProxyUrl.subscribe((httpUrl) => this.arcasHttpUrl = httpUrl);
//             return this.arcasHttpUrl
//         }
//     }

//     getArcasHttpsProxyParam() {
//         this.dataService.currentArcasHttpsProxyUsername.subscribe((httpsUsername) => this.arcasHttpsUsername = httpsUsername);
//         if (this.arcasHttpsUsername !== '') {
//             this.dataService.currentArcasHttpsProxyUrl.subscribe((httpsUrl) => this.arcasHttpsUrl = httpsUrl);
//             this.dataService.currentArcasHttpsProxyPassword.subscribe((httpsPassword) => this.arcasHttpsPassword = httpsPassword);
//             let httpsProxyVal = 'https://' + this.arcasHttpsUsername + ':' + this.arcasHttpsPassword + '@' + this.arcasHttpsUrl.substr(8);
//             return httpsProxyVal;
//         } else {
//             this.dataService.currentArcasHttpsProxyUrl.subscribe((httpsUrl) => this.arcasHttpsUrl = httpsUrl);
//             return this.arcasHttpsUrl;
//         }
//     }

//     public getArcasHttpsProxy() {
//         let httpsProxyVal = '';
//         this.dataService.currentArcasIsSameAsHttp.subscribe((sameAsHttp) => this.arcasSameAsHttp = sameAsHttp);
//         if (this.arcasSameAsHttp) {
//             httpsProxyVal = this.getArcasHttpProxyParam();
//         } else {
//             httpsProxyVal = this.getArcasHttpsProxyParam();
//         }
//         return httpsProxyVal
//     }

    fetchClusterGroups(refreshToken, instanceUrl) {
        this.loadingState  = ClrLoadingState.LOADING;
        this.apiClient.fetchClusterGroups(refreshToken, instanceUrl, 'vsphere').subscribe((data:any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.apiClient.clusterGroups = data.CLUSTER_GROUPS;
                    if (this.uploadStatus){
                        this.subscription = this.dataService.currentSupervisorClusterGroupName.subscribe(
                            (clusterGroupName) => this.supervisorClusterGroupName = clusterGroupName);
                        if(this.apiClient.clusterGroups.indexOf(this.supervisorClusterGroupName) !== -1){
                            this.formGroup.get('clusterGroupName').setValue(this.supervisorClusterGroupName);
                        }
                    }
                    if (this.apiClient.wrkDataProtectionEnabled) {
                        this.fetchVeleroCredentials(refreshToken, instanceUrl);
                    } else {
                        this.connected = true;
                        this.loadingState = ClrLoadingState.DEFAULT;
                    }
                } else if (data.responseType === 'ERROR') {
                    this.connected = false;
                    this.loadingState = ClrLoadingState.DEFAULT;
                    this.errorNotification = data.msg;
                }
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = data.msg;
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = err.msg;
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = "Error while fetching Cluster Groups";
            }
        });
    }

    verifyTmcRefreshToken() {
        let refreshToken = this.formGroup.controls['refreshToken'].value;
        let tmcInstanceURL = this.formGroup.controls['tmcInstanceURL'].value;
        this.loadingState = ClrLoadingState.LOADING;
        this.apiClient.verifyTmcRefreshToken(refreshToken).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.fetchClusterGroups(refreshToken, tmcInstanceURL);
                } else if (data.responseType === 'ERROR') {
                    this.connected = false;
                    this.loadingState = ClrLoadingState.DEFAULT;
                    if (data.hasOwnProperty('msg')) {
                        this.errorNotification = data.msg;
                    } else {
                        this.errorNotification = 'Validation of TMC API Token has failed.';
                    }
                }
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'Validation of TMC API Token has failed. Please ensure the env has connectivity to external networks.';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                // tslint:disable-next-line:max-line-length
                this.errorNotification = 'Failed to connect to the TMC Account. ' + err.msg;
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'Failed to connect to the TMC Account. Please ensure the env has connectivity to external networks.';
            }
        });
    }

    dumyConnect() {
        this.connected = true;
        this.loadingState = ClrLoadingState.DEFAULT;
    }

    validateSupervisorCluster(clusterName) {
        this.apiClient.validateSupervisorCluster(clusterName).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.errorNotification = '';
                    this.tmcClusterValid = true;
                } else if (data.responseType === 'ERROR') {
                    this.errorNotification = 'TMC Supervisor Cluster: ' + data.msg;
                    this.tmcClusterValid = false;
                }
            } else {
                this.errorNotification = 'TMC Supervisor Cluster: Cluster is not HEALTHY';
                this.tmcClusterValid = false;
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.errorNotification = 'TMC Supervisor Cluster: ' + error.msg;
                this.tmcClusterValid = false;
            } else {
                this.errorNotification = 'TMC Supervisor Cluster: Cluster is not HEALTHY';
                this.tmcClusterValid = false;
            }
        });
    }

    onSupervisorClusterChange() {
        this.tmcClusterValid = false;
        if(this.formGroup.get('clusterName').value !== ''){
            this.validateSupervisorCluster(this.formGroup.get('clusterName').value);
        }
    }

    onSupervisorClusterGroupChange() {
        if(this.formGroup.get('refreshToken').value !== "" &&
            this.formGroup.get('tmcInstanceURL').value !== ""){
            this.fetchClusterGroups(this.formGroup.get('refreshToken').value, this.formGroup.get('tmcInstanceURL').value);
        }
    }

    fetchVeleroCredentials(refreshToken, instanceUrl) {
        let tmcData = {
            'refreshToken' : refreshToken,
            'instanceUrl': instanceUrl,
        };
        this.apiClient.fetchCredentials(tmcData, 'tkgs').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.apiClient.dataProtectionCredentials = data.CREDENTIALS;
                    this.fetchVeleroBackupLocations(refreshToken, instanceUrl);
                } else if (data.responseType === 'ERROR') {
                    this.connected = false;
                    this.loadingState = ClrLoadingState.DEFAULT;
                    this.errorNotification = data.msg;
                }
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = "Failed to fetch available credentials";
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = error.msg;
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = "Failed to fetch available credentials";
            }
        });
    }

    fetchVeleroBackupLocations(refreshToken, instanceUrl) {
        let tmcData = {
            "refreshToken": refreshToken,
            "instanceUrl": instanceUrl
        };
        this.apiClient.fetchTargetLocations(tmcData, 'tkgs').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.apiClient.dataProtectionTargetLocations = data.TARGET_LOCATIONS;
                    this.connected = true;
                    this.loadingState = ClrLoadingState.DEFAULT;
                } else if (data.responseType === 'ERROR') {
                    this.connected = false;
                    this.loadingState = ClrLoadingState.DEFAULT;
                    this.errorNotification = data.msg;
                }
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = "Failed to fetch available backup locations";
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = error.msg;
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = "Failed to fetch available backup locations";
            }
        });
    }

//     connectTMC() {
//         this.loadingState = ClrLoadingState.LOADING;
//         let arcasEnableProxy;
//         this.dataService.currentArcasEnableProxy.subscribe((enableProxy) => arcasEnableProxy = enableProxy);
//         this.dataService.currentArcasNoProxy.subscribe((noProxy) => this.arcasNoProxy = noProxy);
//         if (arcasEnableProxy) {
//             let httpProxy = this.getArcasHttpProxyParam();
//             let httpsProxy = this.getArcasHttpsProxy();
//             let noProxy = this.arcasNoProxy;
//             this.apiClient.enableArcasProxy(httpProxy, httpsProxy, noProxy).subscribe((data: any) => {
//                 if (data && data !== null) {
//                     if (data.responseType === 'SUCCESS') {
//                         this.verifyTmcRefreshToken();
//                     } else if (data.responseType === 'ERROR') {
//                         this.connected = false;
//                         this.loadingState = ClrLoadingState.DEFAULT;
//                         if (data.hasOwnProperty('msg')) {
//                             this.errorNotification = data.msg;
//                         } else {
//                             this.errorNotification = 'Validation of TMC API Token has failed. Failed to configure Proxy on Arcas VM.';
//                         }
//                     }
//                 } else {
//                     this.connected = false;
//                     this.loadingState = ClrLoadingState.DEFAULT;
//                     this.errorNotification = 'Validation of TMC API Token has failed. Failed to configure Proxy on Arcas VM.';
//                 }
//             }, (err: any) => {
//                 this.connected = false;
//                 this.loadingState = ClrLoadingState.DEFAULT;
//                 const error = err.error.msg || err.msg || JSON.stringify(err);
//                 this.errorNotification = 'Failed to connect to the TMC Account. Failed to configure Proxy on Arcas VM. ${error}';
//             });
//         } else {
//             this.verifyTmcRefreshToken();
//         }
//     }

}
