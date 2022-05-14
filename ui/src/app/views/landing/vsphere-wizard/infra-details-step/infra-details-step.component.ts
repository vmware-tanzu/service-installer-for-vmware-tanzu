/**
 * Angular Modules
 */
import {Component, OnInit} from '@angular/core';
import {FormControl, Validators} from '@angular/forms';
import {ClrLoadingState} from '@clr/angular';
import {Subscription} from 'rxjs';
/**
 * App imports
 */
import {VSphereWizardFormService} from 'src/app/shared/service/vsphere-wizard-form.service';
import {APIClient} from 'src/app/swagger/api-client.service';
import {StepFormDirective} from 'src/app/views/landing/wizard/shared/step-form/step-form';
import {ValidationService} from 'src/app/views/landing/wizard/shared/validation/validation.service';
import {DataService} from '../../../../shared/service/data.service';

@Component({
    selector: 'app-infradata-step',
    templateUrl: './infra-details-step.component.html',
    styleUrls: ['./infra-details-step.component.scss']
})
export class InfraDataStepComponent extends StepFormDirective implements OnInit {

    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    disableLoadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    configured = false;
    disabledProxy = false;

    enableNetworkName = true;
    displayForm = false;
    additionalNoProxyInfo: string;
    fullNoProxy: string;
    subscription: Subscription;
    errorNotification;
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

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                private dataService: DataService,
                private apiClient: APIClient) {

        super();
        // this.buildForm()
    }

    ngOnInit() {
        super.ngOnInit();
        // this.formGroup.addControl('ntpServer', new FormControl('', [
        //     Validators.required,
        //     this.validationService.isCommaSeparatedIpsOrFqdn()]
        // ));
        // this.formGroup.addControl('dnsServer', new FormControl('', [
        //     Validators.required,
        //     this.validationService.isCommaSeparatedIpsOrFqdn()]
        // ));

        const fieldsMapping = [
            ['httpProxyUrl', ''],
            ['httpProxyUsername', ''],
            ['httpProxyPassword', ''],
            ['httpsProxyUrl', ''],
            ['httpsProxyUsername', ''],
            ['httpsProxyPassword', ''],
            ['noProxy', ''],
        ];
        fieldsMapping.forEach(field => {
            this.formGroup.addControl(field[0], new FormControl(field[1], []));
        });
        this.formGroup.addControl('proxySettings', new FormControl(false));
        this.formGroup.addControl('isSameAsHttp', new FormControl(true));
        setTimeout(_ => {
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentArcasEnableProxy.subscribe(
                    (enableProxy) => this.enableProxy = enableProxy);
                this.formGroup.get('proxySettings').setValue(this.enableProxy);
                if (this.enableProxy) {
                    this.apiClient.arcasProxyEnabled = true;
                    this.toggleProxySetting();
                } else {
                    this.apiClient.arcasProxyEnabled = false;
                    this.toggleProxySetting();
                }
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
                this.subscription = this.dataService.currentArcasHttpsProxyUrl.subscribe(
                    (httpsProxyUrl) => this.httpsProxyUrl = httpsProxyUrl);
                this.formGroup.get('httpsProxyUrl').setValue(this.httpsProxyUrl);
                this.subscription = this.dataService.currentArcasHttpsProxyUsername.subscribe(
                    (httpsProxyUsername) => this.httpsProxyUsername = httpsProxyUsername);
                this.formGroup.get('httpsProxyUsername').setValue(this.httpsProxyUsername);
                this.subscription = this.dataService.currentArcasHttpsProxyPassword.subscribe(
                    (httpsProxyPassword) => this.httpsProxyPassword = httpsProxyPassword);
                this.formGroup.get('httpsProxyPassword').setValue(this.httpsProxyPassword);
                this.subscription = this.dataService.currentArcasNoProxy.subscribe(
                    (noProxy) => this.noProxy = noProxy);
                this.formGroup.get('noProxy').setValue(this.noProxy);
            }
        });
        //
        //
        //
        // this.formGroup.addControl('proxySettings', new FormControl(false));
        // this.formGroup.addControl('httpProxyUrl', new FormControl('', []));
    }
    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
        // don't fill password field with ****
        if (!this.uploadStatus) {
            this.formGroup.get('httpProxyPassword').setValue('');
            this.formGroup.get('httpsProxyPassword').setValue('');
        }
    }

    getArcasHttpProxyParam() {
        const arcasHttpUsername = this.formGroup.get('httpProxyUsername').value;
        const arcasHttpProxyUrl = this.formGroup.get('httpProxyUrl').value;
        if (arcasHttpUsername !== '') {
            const arcasHttpPassword = this.formGroup.get('httpProxyPassword').value;
            const httpProxyVal = 'http://' + arcasHttpUsername + ':' + arcasHttpPassword + '@' + arcasHttpProxyUrl.substring(7);
            return httpProxyVal;
        } else {
            return arcasHttpProxyUrl;
        }
    }

    getArcasHttpsProxyParam() {
        const arcasHttpsUsername = this.formGroup.get('httpsProxyUsername').value;
        const arcasHttpsUrl = this.formGroup.get('httpsProxyUrl').value;
        if (arcasHttpsUsername !== '') {
            const arcasHttpsPassword = this.formGroup.get('httpsProxyPassword').value;
            const httpsProxyVal = 'https://' + arcasHttpsUsername + ':' + arcasHttpsPassword + '@' + arcasHttpsUrl.substring(8);
            return httpsProxyVal;
        } else {
            return arcasHttpsUrl;
        }
    }

    public getArcasHttpsProxy() {
        let httpsProxyVal = '';
        const arcasSameAsHttp = this.formGroup.get('isSameAsHttp').value;
        if (arcasSameAsHttp) {
            httpsProxyVal = this.getArcasHttpProxyParam();
        } else {
            httpsProxyVal = this.getArcasHttpsProxyParam();
        }
        return httpsProxyVal;
    }

    configureProxy() {
        const arcasEnableProxy = this.formGroup.get('proxySettings').value;
        const arcasNoProxy = this.formGroup.get('noProxy').value;
        this.loadingState = ClrLoadingState.LOADING;
        if (!(this.apiClient.proxyConfiguredVsphere) && arcasEnableProxy) {
            const httpProxy = this.getArcasHttpProxyParam();
            const httpsProxy = this.getArcasHttpsProxy();
            // this.apiClient.proxyConfiguredVsphere = true;
            // this.loadingState = ClrLoadingState.DEFAULT;
            // this.disabledProxy = false;
            this.apiClient.enableArcasProxy(httpProxy, httpsProxy, arcasNoProxy, 'vsphere').subscribe((data: any) => {
                if (data && data !== null) {
                    if (data.responseType === 'SUCCESS') {
                        this.apiClient.proxyConfiguredVsphere = true;
                        this.loadingState = ClrLoadingState.DEFAULT;
                        this.disabledProxy = false;
                    } else if (data.responseType === 'ERROR') {
                        this.loadingState = ClrLoadingState.DEFAULT;
                        this.apiClient.proxyConfiguredVsphere = false;
                        if (data.hasOwnProperty('msg')) {
                            this.errorNotification = data.msg;
                        } else {
                            this.errorNotification = 'Configuring Proxy on Arcas VM failed.';
                        }
                    }
                } else {
                    this.loadingState = ClrLoadingState.DEFAULT;
                    this.apiClient.proxyConfiguredVsphere = false;
                    this.errorNotification = 'Configuring Proxy on Arcas VM failed.';
                }
            }, (err: any) => {
                this.loadingState = ClrLoadingState.DEFAULT;
                this.apiClient.proxyConfiguredVsphere = false;
                const error = err.error.msg || err.msg || JSON.stringify(err);
                this.errorNotification = 'Configuring Proxy on Arcas VM failed. ' + error;
            });
        }
    }

    disableProxy() {
        if (this.apiClient.proxyConfiguredVsphere) {
            // this.disableLoadingState = ClrLoadingState.DEFAULT;
            // this.apiClient.proxyConfiguredVsphere = false;
            // this.disabledProxy = true;
            this.apiClient.disableArcasProxy('vsphere').subscribe((data: any) => {
                if (data && data !== null) {
                    if (data.responseType === 'SUCCESS') {
                        this.disableLoadingState = ClrLoadingState.DEFAULT;
                        this.apiClient.proxyConfiguredVsphere = false;
                        this.disabledProxy = true;
                    } else if (data.responseType === 'ERROR') {
                        this.disableLoadingState = ClrLoadingState.DEFAULT;
                        this.apiClient.proxyConfiguredVsphere = true;
                        this.disabledProxy = false;
                        if (data.hasOwnProperty('msg')) {
                            this.errorNotification = data.msg;
                        } else {
                            this.errorNotification = 'Disabling Proxy on Arcas VM failed.';
                        }
                    }
                } else {
                    this.disableLoadingState = ClrLoadingState.DEFAULT;
                    this.apiClient.proxyConfiguredVsphere = true;
                    this.disabledProxy = false;
                    this.errorNotification = 'Disabling Proxy on Arcas VM failed.';
                }
            }, (err: any) => {
                this.disableLoadingState = ClrLoadingState.DEFAULT;
                this.apiClient.proxyConfiguredVsphere = true;
                this.disabledProxy = false;
                const error = err.error.msg || err.msg || JSON.stringify(err);
                this.errorNotification = 'Disabling Proxy on Arcas VM failed. ' + error;
            });
        }
    }


    listenToEvents() {
        //     Broker.messenger.getSubject(TkgEventType.DATACENTER_CHANGED)
        //                 .pipe(takeUntil(this.unsubscribe))
        //                 .subscribe(event => {
        //                     this.resetFieldsUponDCChange();
        //                 });

//         const noProxyFieldChangeMap = ['noProxy'];
//
//         noProxyFieldChangeMap.forEach((field) => {
//             this.formGroup.get(field).valueChanges.pipe(
//                 distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr)),
//                 takeUntil(this.unsubscribe)
//             ).subscribe(() => {
//                 this.generateFullNoProxy();
//             });
//         });
//
//         Broker.messenger.getSubject(TkgEventType.AWS_GET_NO_PROXY_INFO)
//             .pipe(takeUntil(this.unsubscribe))
//             .subscribe(event => {
//                 this.additionalNoProxyInfo = event.payload.info;
//                 this.generateFullNoProxy();
//             });
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
        ];
        if (this.formGroup.value['proxySettings']) {
            this.apiClient.arcasProxyEnabled = true;
            this.resurrectField('httpProxyUrl', [
                Validators.required,
                this.validationService.isHttpOrHttps(),
                this.validationService.noWhitespaceOnEnds()
            ], this.formGroup.value['httpProxyUrl']);
            this.resurrectField('httpProxyUsername', [
                this.validationService.noWhitespaceOnEnds()
            ], this.formGroup.value['httpProxyUsername']);
            this.resurrectField('noProxy', [
                this.validationService.noWhitespaceOnEnds()
            ], this.formGroup.value['noProxy']);
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
            if (this.apiClient.proxyConfiguredVsphere) {
                this.disableProxy();
            }
            this.apiClient.arcasProxyEnabled = false;
            proxySettingFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }
}
