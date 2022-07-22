
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
import {VMCDataService} from "../../../../shared/service/vmc-data.service";


const SupervisedField = ['refreshToken', 'tmcInstanceURL'];

@Component({
    selector: 'app-tanzuSaas-step',
    templateUrl: './tanzu-saas-setting-step.component.html',
    styleUrls: ['./tanzu-saas-setting-step.component.scss']
})
export class TanzuSaasStepComponent extends StepFormDirective implements OnInit {

    enableNetworkName = true;
    subscription: Subscription;
    uploadStatus: boolean;
    private enableTmc: boolean;
    private refreshToken: string;
    private tmcInstanceURL;
    private enableTo: boolean;
    private toRefreshToken: string;
    private toUrl: string;
    connected: boolean = false;

    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    validateRefreshToken = false;

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                private dataService: VMCDataService,
                private apiClient: APIClient) {

        super();
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl('tmcSettings', new FormControl(false));
        this.formGroup.addControl('refreshToken', new FormControl('', []));
        this.formGroup.addControl('tmcInstanceURL', new FormControl('', []));
        this.formGroup.addControl('toSettings', new FormControl(false));
        this.formGroup.addControl('toUrl', new FormControl('', []));
        this.formGroup.addControl('toRefreshToken', new FormControl('', []));

        SupervisedField.forEach(field => {
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
                return this.formGroup.valid && this.connected;
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
                    this.subscription = this.dataService.currentInstanceUrl.subscribe(
                        (url) => this.tmcInstanceURL = url);
                    this.formGroup.get('tmcInstanceURL').setValue(this.tmcInstanceURL);
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

    toggleTMCSetting() {
        const tmcSettingsFields = [
            'refreshToken',
            'tmcInstanceURL',
            'toSettings',
            'toUrl',
            'toRefreshToken',
        ];
        if (this.formGroup.value['tmcSettings']) {
            this.apiClient.tmcEnabled = true;
            this.apiClient.baseImage = ['photon'];
            this.resurrectField('refreshToken', [
                Validators.required, this.validationService.noWhitespaceOnEnds()
            ], this.formGroup.value['refreshToken']);
            this.resurrectField('tmcInstanceURL', [
                Validators.required,
                this.validationService.noWhitespaceOnEnds(),
                this.validationService.isHttpOrHttps()
            ], this.formGroup.value['tmcInstanceURL']);
        } else {
            this.apiClient.tmcEnabled = false;
            this.apiClient.toEnabled = false;
            this.apiClient.baseImage = ['photon', 'ubuntu'];
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
                Validators.required,
                this.validationService.isHttpOrHttps(),
                this.validationService.noWhitespaceOnEnds()
            ], this.formGroup.value['toUrl']);
            this.resurrectField('toRefreshToken',
                [Validators.required,
                this.validationService.noWhitespaceOnEnds()],
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

    dumyConnect() {
        this.connected = true;
        this.loadingState = ClrLoadingState.DEFAULT;
    }

    fetchClusterGroups(refreshToken, instanceUrl) {
        this.loadingState  = ClrLoadingState.LOADING;
        this.apiClient.fetchClusterGroups(refreshToken, instanceUrl, 'vmc').subscribe((data:any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.apiClient.clusterGroups = data.CLUSTER_GROUPS;
                    if (this.uploadStatus &&  (this.apiClient.wrkDataProtectionEnabled || this.apiClient.sharedDataProtectonEnabled)) {
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

    connectTMC() {
        this.loadingState = ClrLoadingState.LOADING;
        let refreshToken = this.formGroup.controls['refreshToken'].value;
        let tmcInstanceURL = this.formGroup.controls['tmcInstanceURL'].value;
        this.apiClient.verifyTmcRefreshToken(refreshToken).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.fetchClusterGroups(refreshToken, tmcInstanceURL);
                    // this.connected = true;
                    // this.loadingState = ClrLoadingState.DEFAULT;
                } else if (data.responseType === 'ERROR') {
                    this.connected = false;
                    this.loadingState = ClrLoadingState.DEFAULT;
                    if (data.hasOwnProperty('msg')) {
                        this.errorNotification = data.msg;
                    } else {
                        this.errorNotification = 'Validation of TMC API Token has failed. Please ensure the env has connectivity to external networks.';
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
                this.errorNotification = 'Failed to connect to the TMC Account. Please ensure the env has connectivity to external networks. ' + err.msg;
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'Failed to connect to the TMC Account. Please ensure the env has connectivity to external networks.';
            }
        });
    }

    fetchVeleroCredentials(refreshToken, instanceUrl) {
        let tmcData = {
            'refreshToken' : refreshToken,
            'instanceUrl': instanceUrl,
        };
        this.apiClient.fetchCredentials(tmcData, 'vcf').subscribe((data: any) => {
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
        this.apiClient.fetchTargetLocations(tmcData, 'vcf').subscribe((data: any) => {
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
}
