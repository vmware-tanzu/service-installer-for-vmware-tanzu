// Angular imports
import { AfterViewInit, Component, ElementRef, Input, OnInit, ViewChild } from '@angular/core';
import {FormBuilder, FormControl, FormGroup, Validators} from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { Router } from '@angular/router';

// Third party imports
import {Observable, Subscription} from 'rxjs';

// App imports
import { DataService } from 'src/app/shared/service/data.service';
import { VMCDataService } from 'src/app/shared/service/vmc-data.service';
import { VsphereNsxtDataService } from 'src/app/shared/service/vsphere-nsxt-data.service';
import { FormMetaDataStore } from "../wizard/shared/FormMetaDataStore";
import { FormMetaDataService } from 'src/app/shared/service/form-meta-data.service';
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';
import { PROVIDERS, Providers } from '../../../shared/constants/app.constants';
import { APP_ROUTES, Routes } from '../../../shared/constants/routes.constants';
import { AppDataService } from '../../../shared/service/app-data.service';
import { BrandingObj } from '../../../shared/service/branding.service';
import { APIClient } from '../../../swagger/api-client.service';
import { WizardBaseDirective } from '../wizard/shared/wizard-base/wizard-base';

@Component({
    selector: 'app-upload',
    templateUrl: './vsphere-nsxt-upload-wizard.component.html',
    styleUrls: ['./vsphere-nsxt-upload-wizard.component.scss'],
})
export class VsphereNsxtUploadWizardComponent implements OnInit {

    @ViewChild('attachments') public attachment: any;
    public APP_ROUTES: Routes = APP_ROUTES;
    public PROVIDERS: Providers = PROVIDERS;

    public displayWizard = false;
    public fileName: string;
    public fileUploaded = false;
    public file: File;
    public inputFile;
//     edition: string;
    public clusterType: string;
    public provider: Observable<string>;
    public landingPageContent: BrandingObj;
    public loading = false;

    public readFile = false;
    errorNotification = '';
    public noupload = true;
    showLoginLoader = false;

    public subscription: Subscription;
    constructor(
        private apiClient: APIClient, private router: Router,
        private appDataService: AppDataService,
        private dataService: DataService,
        private vmcDataService: VMCDataService,
        private nsxtDataService: VsphereNsxtDataService,

    ) {
        // super(router, el, formMetaDataService, titleService);
        this.provider = this.appDataService.getProviderType();
    }

    public ngOnInit() {
    }

    /**
     * @method navigate
     * @desc helper method to trigger router navigation to specified route
     * @param route - the route to navigate to
     */
    public navigate(route: string): void {
        this.apiClient.redirectedToHome = true;
        this.router.navigate([route]);
    }

    public readInputJsonFile() {
        if (this.fileName !== '' && this.fileUploaded) {
            const reader = new FileReader();
            reader.readAsText(this.file, 'UTF-8');
            // tslint:disable-next-line:only-arrow-functions
            reader.onload = async function (evt) {
                if (typeof evt.target.result === 'string') {
                    const readInput = await (JSON.parse(evt.target.result));
                    await console.log(' ');
                    return readInput;
                }
            };
            // tslint:disable-ne xt-line:only-arrow-functions
            reader.onerror = function (evt) {
                console.log('Error Reading Input File');
            };
        } else {
        }
        // Give an Error here
        return;
    }

    public processArcasProxyParam(input) {
        let http_proxy = input['envSpec']['proxySpec']['arcasVm']['httpProxy'];
        let https_proxy = input['envSpec']['proxySpec']['arcasVm']['httpsProxy'];
        if (http_proxy === https_proxy) {
            let stripUser = http_proxy.substr(7);
            if (stripUser.includes('@')) {
                let username = stripUser.substring(0, stripUser.indexOf(':'));
                let password = stripUser.substring(stripUser.indexOf(':') + 1, stripUser.indexOf('@'));
                let url = 'http://' + stripUser.substr(stripUser.indexOf('@') + 1);
                this.dataService.changeArcasHttpProxyUrl(url);
                this.dataService.changeArcasHttpsProxyUrl(url);
                this.dataService.changeArcasHttpProxyUsername(username);
                this.dataService.changeArcasHttpsProxyUsername(username);
                this.dataService.changeArcasHttpProxyPassword(password);
                this.dataService.changeArcasHttpsProxyPassword(password);
            } else {
                this.dataService.changeArcasHttpProxyUrl(http_proxy);
                this.dataService.changeArcasHttpsProxyUrl(https_proxy);
            }
            this.dataService.changeArcasIsSameAsHttp(true);
        } else {
            let httpStripUser = http_proxy.substr(7);
            this.dataService.changeArcasIsSameAsHttp(false);
            if (httpStripUser.includes('@')) {
                let username = httpStripUser.substring(0, httpStripUser.indexOf(':'));
                this.dataService.changeArcasHttpProxyUsername(username);
                let password = httpStripUser.substring(httpStripUser.indexOf(':') + 1, httpStripUser.indexOf('@'));
                this.dataService.changeArcasHttpProxyPassword(password);
                let url = http_proxy.substring(0, http_proxy.indexOf(':')) + '://' + httpStripUser.substr(httpStripUser.indexOf('@') + 1);
                this.dataService.changeArcasHttpProxyUrl(url);
            } else {
                this.dataService.changeArcasHttpProxyUrl(http_proxy);
            }
            let httpsStripUser = https_proxy.substr(8);
            if (httpsStripUser.includes('@')) {
                let username = httpsStripUser.substring(0, httpsStripUser.indexOf(':'));
                this.dataService.changeArcasHttpsProxyUsername(username);
                let password = httpsStripUser.substring(httpsStripUser.indexOf(':') + 1, httpsStripUser.indexOf('@'));
                this.dataService.changeArcasHttpsProxyPassword(password);
                let url = https_proxy.substring(0, https_proxy.indexOf(':')) + '://' + httpsStripUser.substr(httpsStripUser.indexOf('@') + 1);
                this.dataService.changeArcasHttpsProxyUrl(url);
            } else {
                this.dataService.changeArcasHttpsProxyUrl(https_proxy);
            }
        }
    }

    processMgmtProxyParam(input) {
        let http_proxy = input['envSpec']['proxySpec']['tkgMgmt']['httpProxy'];
        let https_proxy = input['envSpec']['proxySpec']['tkgMgmt']['httpsProxy'];
        if (http_proxy === https_proxy) {
            let stripUser = http_proxy.substr(7);
            if (stripUser.includes('@')) {
                let username = stripUser.substring(0, stripUser.indexOf(':'));
                let password = stripUser.substring(stripUser.indexOf(':') + 1, stripUser.indexOf('@'));
                let url = 'http://' + stripUser.substr(stripUser.indexOf('@') + 1);
                this.dataService.changeMgmtHttpProxyUrl(url);
                this.dataService.changeMgmtHttpsProxyUrl(url);
                this.dataService.changeMgmtHttpProxyUsername(username);
                this.dataService.changeMgmtHttpsProxyUsername(username);
                this.dataService.changeMgmtHttpProxyPassword(password);
                this.dataService.changeMgmtHttpsProxyPassword(password);
            } else {
                this.dataService.changeMgmtHttpProxyUrl(http_proxy);
                this.dataService.changeMgmtHttpsProxyUrl(https_proxy);
            }
            this.dataService.changeMgmtIsSameAsHttp(true);
        } else {
            let httpStripUser = http_proxy.substr(7);
            this.dataService.changeMgmtIsSameAsHttp(false);
            if (httpStripUser.includes('@')) {
                let username = httpStripUser.substring(0, httpStripUser.indexOf(':') );
                this.dataService.changeMgmtHttpProxyUsername(username);
                let password = httpStripUser.substring(httpStripUser.indexOf(':') + 1, httpStripUser.indexOf('@') );
                this.dataService.changeMgmtHttpProxyPassword(password);
                let url = http_proxy.substring(0, http_proxy.indexOf(':')) + '://' + httpStripUser.substr(httpStripUser.indexOf('@') + 1);
                this.dataService.changeMgmtHttpProxyUrl(url);
            } else {
                this.dataService.changeMgmtHttpProxyUrl(http_proxy);
            }
            let httpsStripUser = https_proxy.substr(8);
            if (httpsStripUser.includes('@')) {
                let username = httpsStripUser.substring(0, httpsStripUser.indexOf(':') );
                this.dataService.changeMgmtHttpsProxyUsername(username);
                let password = httpsStripUser.substring(httpsStripUser.indexOf(':') + 1, httpsStripUser.indexOf('@') );
                this.dataService.changeMgmtHttpsProxyPassword(password);
                let url = https_proxy.substring(0, https_proxy.indexOf(':')) + '://' + httpsStripUser.substr(httpsStripUser.indexOf('@') + 1);
                this.dataService.changeMgmtHttpsProxyUrl(url);
            } else {
                this.dataService.changeMgmtHttpsProxyUrl(https_proxy);
            }
        }
    }

    public processSharedProxyParam(input) {
        let http_proxy = input['envSpec']['proxySpec']['tkgSharedservice']['httpProxy'];
        let https_proxy = input['envSpec']['proxySpec']['tkgSharedservice']['httpsProxy'];
        if (http_proxy === https_proxy) {
            let stripUser = http_proxy.substr(7);
            if (stripUser.includes('@')) {
                let username = stripUser.substring(0, stripUser.indexOf(':'));
                let password = stripUser.substring(stripUser.indexOf(':') + 1, stripUser.indexOf('@'));
                let url = 'http://' + stripUser.substr(stripUser.indexOf('@') + 1);
                this.dataService.changeSharedHttpProxyUrl(url);
                this.dataService.changeSharedHttpsProxyUrl(url);
                this.dataService.changeSharedHttpProxyUsername(username);
                this.dataService.changeSharedHttpsProxyUsername(username);
                this.dataService.changeSharedHttpProxyPassword(password);
                this.dataService.changeSharedHttpsProxyPassword(password);
            } else {
                this.dataService.changeSharedHttpProxyUrl(http_proxy);
                this.dataService.changeSharedHttpsProxyUrl(https_proxy);
            }
            this.dataService.changeSharedIsSameAsHttp(true);
        } else {
            let httpStripUser = http_proxy.substr(7);
            this.dataService.changeSharedIsSameAsHttp(false);
            if (httpStripUser.includes('@')) {
                let username = httpStripUser.substring(0, httpStripUser.indexOf(':') );
                this.dataService.changeSharedHttpProxyUsername(username);
                let password = httpStripUser.substring(httpStripUser.indexOf(':') + 1, httpStripUser.indexOf('@') );
                this.dataService.changeSharedHttpProxyPassword(password);
                let url = http_proxy.substring(0, http_proxy.indexOf(':')) + '://' + httpStripUser.substr(httpStripUser.indexOf('@') + 1);
                this.dataService.changeSharedHttpProxyUrl(url);
            } else {
                this.dataService.changeSharedHttpProxyUrl(http_proxy);
            }
            let httpsStripUser = https_proxy.substr(8);
            if (httpsStripUser.includes('@')) {
                let username = httpsStripUser.substring(0, httpsStripUser.indexOf(':') );
                this.dataService.changeSharedHttpsProxyUsername(username);
                let password = httpsStripUser.substring(httpsStripUser.indexOf(':') + 1, httpsStripUser.indexOf('@') );
                this.dataService.changeSharedHttpsProxyPassword(password);
                let url = https_proxy.substring(0, https_proxy.indexOf(':')) + '://' + httpsStripUser.substr(httpsStripUser.indexOf('@') + 1);
                this.dataService.changeSharedHttpsProxyUrl(url);
            } else {
                this.dataService.changeSharedHttpsProxyUrl(https_proxy);
            }
        }
    }

    public processWrkProxyParam(input) {
        let http_proxy = input['envSpec']['proxySpec']['tkgWorkload']['httpProxy'];
        let https_proxy = input['envSpec']['proxySpec']['tkgWorkload']['httpsProxy'];
        if (http_proxy === https_proxy) {
            let stripUser = http_proxy.substr(7);
            if (stripUser.includes('@')) {
                let username = stripUser.substring(0, stripUser.indexOf(':'));
                let password = stripUser.substring(stripUser.indexOf(':') + 1, stripUser.indexOf('@'));
                let url = 'http://' + stripUser.substr(stripUser.indexOf('@') + 1);
                this.dataService.changeWrkHttpProxyUrl(url);
                this.dataService.changeWrkHttpsProxyUrl(url);
                this.dataService.changeWrkHttpProxyUsername(username);
                this.dataService.changeWrkHttpsProxyUsername(username);
                this.dataService.changeWrkHttpProxyPassword(password);
                this.dataService.changeWrkHttpsProxyPassword(password);
            } else {
                this.dataService.changeWrkHttpProxyUrl(http_proxy);
                this.dataService.changeWrkHttpsProxyUrl(https_proxy);
            }
            this.dataService.changeWrkIsSameAsHttp(true);
        } else {
            let httpStripUser = http_proxy.substr(7);
            this.dataService.changeWrkIsSameAsHttp(false);
            if (httpStripUser.includes('@')) {
                let username = httpStripUser.substring(0, httpStripUser.indexOf(':') );
                this.dataService.changeWrkHttpProxyUsername(username);
                let password = httpStripUser.substring(httpStripUser.indexOf(':') + 1, httpStripUser.indexOf('@') );
                this.dataService.changeWrkHttpProxyPassword(password);
                let url = http_proxy.substring(0, http_proxy.indexOf(':')) + '://' + httpStripUser.substr(httpStripUser.indexOf('@') + 1);
                this.dataService.changeWrkHttpProxyUrl(url);
            } else {
                this.dataService.changeWrkHttpProxyUrl(http_proxy);
            }
            let httpsStripUser = https_proxy.substr(8);
            if (httpsStripUser.includes('@')) {
                let username = httpsStripUser.substring(0, httpsStripUser.indexOf(':') );
                this.dataService.changeWrkHttpsProxyUsername(username);
                let password = httpsStripUser.substring(httpsStripUser.indexOf(':') + 1, httpsStripUser.indexOf('@') );
                this.dataService.changeWrkHttpsProxyPassword(password);
                let url = https_proxy.substring(0, https_proxy.indexOf(':')) + '://' + httpsStripUser.substr(httpsStripUser.indexOf('@') + 1);
                this.dataService.changeWrkHttpsProxyUrl(url);
            } else {
                this.dataService.changeWrkHttpsProxyUrl(https_proxy);
            }
        }
    }

    public processNsxtArcasProxyParam(input) {
        let http_proxy = input['envSpec']['proxySpec']['arcasVm']['httpProxy'];
        let https_proxy = input['envSpec']['proxySpec']['arcasVm']['httpsProxy'];
        if (http_proxy === https_proxy) {
            let stripUser = http_proxy.substr(7);
            if (stripUser.includes('@')) {
                let username = stripUser.substring(0, stripUser.indexOf(':'));
                let password = stripUser.substring(stripUser.indexOf(':') + 1, stripUser.indexOf('@'));
                let url = 'http://' + stripUser.substr(stripUser.indexOf('@') + 1);
                this.nsxtDataService.changeArcasHttpProxyUrl(url);
                this.nsxtDataService.changeArcasHttpsProxyUrl(url);
                this.nsxtDataService.changeArcasHttpProxyUsername(username);
                this.nsxtDataService.changeArcasHttpsProxyUsername(username);
                this.nsxtDataService.changeArcasHttpProxyPassword(password);
                this.nsxtDataService.changeArcasHttpsProxyPassword(password);
            } else {
                this.nsxtDataService.changeArcasHttpProxyUrl(http_proxy);
                this.nsxtDataService.changeArcasHttpsProxyUrl(https_proxy);
            }
            this.nsxtDataService.changeArcasIsSameAsHttp(true);
        } else {
            let httpStripUser = http_proxy.substr(7);
            this.nsxtDataService.changeArcasIsSameAsHttp(false);
            if (httpStripUser.includes('@')) {
                let username = httpStripUser.substring(0, httpStripUser.indexOf(':'));
                this.nsxtDataService.changeArcasHttpProxyUsername(username);
                let password = httpStripUser.substring(httpStripUser.indexOf(':') + 1, httpStripUser.indexOf('@'));
                this.nsxtDataService.changeArcasHttpProxyPassword(password);
                let url = http_proxy.substring(0, http_proxy.indexOf(':')) + '://' + httpStripUser.substr(httpStripUser.indexOf('@') + 1);
                this.nsxtDataService.changeArcasHttpProxyUrl(url);
            } else {
                this.nsxtDataService.changeArcasHttpProxyUrl(http_proxy);
            }
            let httpsStripUser = https_proxy.substr(8);
            if (httpsStripUser.includes('@')) {
                let username = httpsStripUser.substring(0, httpsStripUser.indexOf(':'));
                this.nsxtDataService.changeArcasHttpsProxyUsername(username);
                let password = httpsStripUser.substring(httpsStripUser.indexOf(':') + 1, httpsStripUser.indexOf('@'));
                this.nsxtDataService.changeArcasHttpsProxyPassword(password);
                let url = https_proxy.substring(0, https_proxy.indexOf(':')) + '://' + httpsStripUser.substr(httpsStripUser.indexOf('@') + 1);
                this.nsxtDataService.changeArcasHttpsProxyUrl(url);
            } else {
                this.nsxtDataService.changeArcasHttpsProxyUrl(https_proxy);
            }
        }
    }

    processNsxtMgmtProxyParam(input) {
        let http_proxy = input['envSpec']['proxySpec']['tkgMgmt']['httpProxy'];
        let https_proxy = input['envSpec']['proxySpec']['tkgMgmt']['httpsProxy'];
        if (http_proxy === https_proxy) {
            let stripUser = http_proxy.substr(7);
            if (stripUser.includes('@')) {
                let username = stripUser.substring(0, stripUser.indexOf(':'));
                let password = stripUser.substring(stripUser.indexOf(':') + 1, stripUser.indexOf('@'));
                let url = 'http://' + stripUser.substr(stripUser.indexOf('@') + 1);
                this.nsxtDataService.changeMgmtHttpProxyUrl(url);
                this.nsxtDataService.changeMgmtHttpsProxyUrl(url);
                this.nsxtDataService.changeMgmtHttpProxyUsername(username);
                this.nsxtDataService.changeMgmtHttpsProxyUsername(username);
                this.nsxtDataService.changeMgmtHttpProxyPassword(password);
                this.nsxtDataService.changeMgmtHttpsProxyPassword(password);
            } else {
                this.nsxtDataService.changeMgmtHttpProxyUrl(http_proxy);
                this.nsxtDataService.changeMgmtHttpsProxyUrl(https_proxy);
            }
            this.nsxtDataService.changeMgmtIsSameAsHttp(true);
        } else {
            let httpStripUser = http_proxy.substr(7);
            this.nsxtDataService.changeMgmtIsSameAsHttp(false);
            if (httpStripUser.includes('@')) {
                let username = httpStripUser.substring(0, httpStripUser.indexOf(':') );
                this.nsxtDataService.changeMgmtHttpProxyUsername(username);
                let password = httpStripUser.substring(httpStripUser.indexOf(':') + 1, httpStripUser.indexOf('@') );
                this.nsxtDataService.changeMgmtHttpProxyPassword(password);
                let url = http_proxy.substring(0, http_proxy.indexOf(':')) + '://' + httpStripUser.substr(httpStripUser.indexOf('@') + 1);
                this.nsxtDataService.changeMgmtHttpProxyUrl(url);
            } else {
                this.nsxtDataService.changeMgmtHttpProxyUrl(http_proxy);
            }
            let httpsStripUser = https_proxy.substr(8);
            if (httpsStripUser.includes('@')) {
                let username = httpsStripUser.substring(0, httpsStripUser.indexOf(':') );
                this.nsxtDataService.changeMgmtHttpsProxyUsername(username);
                let password = httpsStripUser.substring(httpsStripUser.indexOf(':') + 1, httpsStripUser.indexOf('@') );
                this.nsxtDataService.changeMgmtHttpsProxyPassword(password);
                let url = https_proxy.substring(0, https_proxy.indexOf(':')) + '://' + httpsStripUser.substr(httpsStripUser.indexOf('@') + 1);
                this.nsxtDataService.changeMgmtHttpsProxyUrl(url);
            } else {
                this.nsxtDataService.changeMgmtHttpsProxyUrl(https_proxy);
            }
        }
    }

    public processNsxtSharedProxyParam(input) {
        let http_proxy = input['envSpec']['proxySpec']['tkgSharedservice']['httpProxy'];
        let https_proxy = input['envSpec']['proxySpec']['tkgSharedservice']['httpsProxy'];
        if (http_proxy === https_proxy) {
            let stripUser = http_proxy.substr(7);
            if (stripUser.includes('@')) {
                let username = stripUser.substring(0, stripUser.indexOf(':'));
                let password = stripUser.substring(stripUser.indexOf(':') + 1, stripUser.indexOf('@'));
                let url = 'http://' + stripUser.substr(stripUser.indexOf('@') + 1);
                this.nsxtDataService.changeSharedHttpProxyUrl(url);
                this.nsxtDataService.changeSharedHttpsProxyUrl(url);
                this.nsxtDataService.changeSharedHttpProxyUsername(username);
                this.nsxtDataService.changeSharedHttpsProxyUsername(username);
                this.nsxtDataService.changeSharedHttpProxyPassword(password);
                this.nsxtDataService.changeSharedHttpsProxyPassword(password);
            } else {
                this.nsxtDataService.changeSharedHttpProxyUrl(http_proxy);
                this.nsxtDataService.changeSharedHttpsProxyUrl(https_proxy);
            }
            this.nsxtDataService.changeSharedIsSameAsHttp(true);
        } else {
            let httpStripUser = http_proxy.substr(7);
            this.nsxtDataService.changeSharedIsSameAsHttp(false);
            if (httpStripUser.includes('@')) {
                let username = httpStripUser.substring(0, httpStripUser.indexOf(':') );
                this.nsxtDataService.changeSharedHttpProxyUsername(username);
                let password = httpStripUser.substring(httpStripUser.indexOf(':') + 1, httpStripUser.indexOf('@') );
                this.nsxtDataService.changeSharedHttpProxyPassword(password);
                let url = http_proxy.substring(0, http_proxy.indexOf(':')) + '://' + httpStripUser.substr(httpStripUser.indexOf('@') + 1);
                this.nsxtDataService.changeSharedHttpProxyUrl(url);
            } else {
                this.nsxtDataService.changeSharedHttpProxyUrl(http_proxy);
            }
            let httpsStripUser = https_proxy.substr(8);
            if (httpsStripUser.includes('@')) {
                let username = httpsStripUser.substring(0, httpsStripUser.indexOf(':') );
                this.nsxtDataService.changeSharedHttpsProxyUsername(username);
                let password = httpsStripUser.substring(httpsStripUser.indexOf(':') + 1, httpsStripUser.indexOf('@') );
                this.nsxtDataService.changeSharedHttpsProxyPassword(password);
                let url = https_proxy.substring(0, https_proxy.indexOf(':')) + '://' + httpsStripUser.substr(httpsStripUser.indexOf('@') + 1);
                this.nsxtDataService.changeSharedHttpsProxyUrl(url);
            } else {
                this.nsxtDataService.changeSharedHttpsProxyUrl(https_proxy);
            }
        }
    }

    public processNsxtWrkProxyParam(input) {
        let http_proxy = input['envSpec']['proxySpec']['tkgWorkload']['httpProxy'];
        let https_proxy = input['envSpec']['proxySpec']['tkgWorkload']['httpsProxy'];
        if (http_proxy === https_proxy) {
            let stripUser = http_proxy.substr(7);
            if (stripUser.includes('@')) {
                let username = stripUser.substring(0, stripUser.indexOf(':'));
                let password = stripUser.substring(stripUser.indexOf(':') + 1, stripUser.indexOf('@'));
                let url = 'http://' + stripUser.substr(stripUser.indexOf('@') + 1);
                this.nsxtDataService.changeWrkHttpProxyUrl(url);
                this.nsxtDataService.changeWrkHttpsProxyUrl(url);
                this.nsxtDataService.changeWrkHttpProxyUsername(username);
                this.nsxtDataService.changeWrkHttpsProxyUsername(username);
                this.nsxtDataService.changeWrkHttpProxyPassword(password);
                this.nsxtDataService.changeWrkHttpsProxyPassword(password);
            } else {
                this.nsxtDataService.changeWrkHttpProxyUrl(http_proxy);
                this.nsxtDataService.changeWrkHttpsProxyUrl(https_proxy);
            }
            this.nsxtDataService.changeWrkIsSameAsHttp(true);
        } else {
            let httpStripUser = http_proxy.substr(7);
            this.nsxtDataService.changeWrkIsSameAsHttp(false);
            if (httpStripUser.includes('@')) {
                let username = httpStripUser.substring(0, httpStripUser.indexOf(':') );
                this.nsxtDataService.changeWrkHttpProxyUsername(username);
                let password = httpStripUser.substring(httpStripUser.indexOf(':') + 1, httpStripUser.indexOf('@') );
                this.nsxtDataService.changeWrkHttpProxyPassword(password);
                let url = http_proxy.substring(0, http_proxy.indexOf(':')) + '://' + httpStripUser.substr(httpStripUser.indexOf('@') + 1);
                this.nsxtDataService.changeWrkHttpProxyUrl(url);
            } else {
                this.nsxtDataService.changeWrkHttpProxyUrl(http_proxy);
            }
            let httpsStripUser = https_proxy.substr(8);
            if (httpsStripUser.includes('@')) {
                let username = httpsStripUser.substring(0, httpsStripUser.indexOf(':') );
                this.nsxtDataService.changeWrkHttpsProxyUsername(username);
                let password = httpsStripUser.substring(httpsStripUser.indexOf(':') + 1, httpsStripUser.indexOf('@') );
                this.nsxtDataService.changeWrkHttpsProxyPassword(password);
                let url = https_proxy.substring(0, https_proxy.indexOf(':')) + '://' + httpsStripUser.substr(httpsStripUser.indexOf('@') + 1);
                this.nsxtDataService.changeWrkHttpsProxyUrl(url);
            } else {
                this.nsxtDataService.changeWrkHttpsProxyUrl(https_proxy);
            }
        }
    }

    public processEnableMonitoring(input) {
        if (input['tanzuExtensions'].hasOwnProperty('monitoring')) {
            if (input['tanzuExtensions']['monitoring'].hasOwnProperty('enableLoggingExtension')) {
                if (input['tanzuExtensions']['monitoring']['enableLoggingExtension'] === 'true') {
                    this.dataService.changeEnableMonitoringExtension(true);
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('prometheusFqdn')) {
                        this.dataService.changePrometheusFqdn(input['tanzuExtensions']['monitoring']['prometheusFqdn']);
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('prometheusCertPath')) {
                        this.dataService.changePrometheusCertPath(input['tanzuExtensions']['monitoring']['prometheusCertPath']);
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('prometheusCertKeyPath')) {
                        this.dataService.changePrometheusCertkeyPath(input['tanzuExtensions']['monitoring']['prometheusCertKeyPath']);
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('grafanaFqdn')) {
                        this.dataService.changeGrafanaFqdn(input['tanzuExtensions']['monitoring']['grafanaFqdn']);
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('grafanaPasswordBase64')) {
                        this.dataService.changeGrafanaPassword(atob(input['tanzuExtensions']['monitoring']['grafanaPasswordBase64']));
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('grafanaCertPath')) {
                        this.dataService.changeGrafanaCertPath(input['tanzuExtensions']['monitoring']['grafanaCertPath']);
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('grafanaCertKeyPath')) {}
                        this.dataService.changeGrafanaCertKeyPath(input['tanzuExtensions']['monitoring']['grafanaCertKeyPath']);
                } else {
                    this.dataService.changeEnableMonitoringExtension(false);
                }
            }
        }

    }

    public processEnableLogging(input) {
        if (input['tanzuExtensions'].hasOwnProperty('logging')) {
            if (input['tanzuExtensions']['logging'].hasOwnProperty('syslogEndpoint') &&
                input['tanzuExtensions']['logging'].hasOwnProperty('httpEndpoint') &&
                input['tanzuExtensions']['logging'].hasOwnProperty('kafkaEndpoint')) {
                if (input['tanzuExtensions']['logging']['syslogEndpoint'].hasOwnProperty('enableSyslogEndpoint') &&
                    input['tanzuExtensions']['logging']['httpEndpoint'].hasOwnProperty('enableHttpEndpoint') &&
                    input['tanzuExtensions']['logging']['kafkaEndpoint'].hasOwnProperty('enableKafkaEndpoint')) {
                    if (input['tanzuExtensions']['logging']['syslogEndpoint']['enableSyslogEndpoint'] === 'true') {
                        this.dataService.changeEnableLoggingExtension(true);
                        this.dataService.changeLoggingEndpoint('Syslog');
                        if (input['tanzuExtensions']['logging']['syslogEndpoint'].hasOwnProperty('syslogEndpointAddress')) {
                            this.dataService.changeSyslogAddress(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointAddress']);
                        }
                        if (input['tanzuExtensions']['logging']['syslogEndpoint'].hasOwnProperty('syslogEndpointPort')) {
                            this.dataService.changeSyslogPort(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointPort']);
                        }
                        if (input['tanzuExtensions']['logging']['syslogEndpoint'].hasOwnProperty('syslogEndpointMode')) {
                            this.dataService.changeSyslogMode(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointMode']);
                        }
                        if (input['tanzuExtensions']['logging']['syslogEndpoint'].hasOwnProperty('syslogEndpointFormat')) {
                            this.dataService.changeSyslogFormat(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointFormat']);
                        }
                    } else if(input['tanzuExtensions']['logging']['httpEndpoint']['enableHttpEndpoint'] === 'true') {
                        this.dataService.changeEnableLoggingExtension(true);
                        this.dataService.changeLoggingEndpoint('HTTP');
                        if (input['tanzuExtensions']['logging']['httpEndpoint'].hasOwnProperty('httpEndpointAddress')) {
                            this.dataService.changeHttpAddress(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointAddress']);
                        }
                        if (input['tanzuExtensions']['logging']['httpEndpoint'].hasOwnProperty('httpEndpointPort')) {
                            this.dataService.changeHttpPort(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointPort']);
                        }
                        if (input['tanzuExtensions']['logging']['httpEndpoint'].hasOwnProperty('httpEndpointUri')) {
                            this.dataService.changeHttpUri(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointUri']);
                        }
                        if (input['tanzuExtensions']['logging']['httpEndpoint'].hasOwnProperty('httpEndpointHeaderKeyValue')) {
                            this.dataService.changeHttpHeaderKey(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointHeaderKeyValue']);
                        }
                    // } else if(input['tanzuExtensions']['logging']['elasticSearchEndpoint']['enableElasticSearchEndpoint'] === 'true') {
                    //     this.dataService.changeEnableLoggingExtension(true);
                    //     this.dataService.changeLoggingEndpoint('Elastic Search');
                    //     if (input['tanzuExtensions']['logging']['elasticSearchEndpoint'].hasOwnProperty('elasticSearchEndpointAddress')) {
                    //         this.dataService.changeElasticSearchAddress(input['tanzuExtensions']['logging']['elasticSearchEndpoint']['elasticSearchEndpointAddress']);
                    //     }
                    //     if (input['tanzuExtensions']['logging']['elasticSearchEndpoint'].hasOwnProperty('elasticSearchEndpointPort')) {
                    //         this.dataService.changeElasticSearchPort(input['tanzuExtensions']['logging']['elasticSearchEndpoint']['elasticSearchEndpointPort']);
                    //     }
                    } else if(input['tanzuExtensions']['logging']['kafkaEndpoint']['enableKafkaEndpoint'] === 'true') {
                        this.dataService.changeEnableLoggingExtension(true);
                        this.dataService.changeLoggingEndpoint('Kafka');
                        if (input['tanzuExtensions']['logging']['kafkaEndpoint'].hasOwnProperty('kafkaBrokerServiceName')) {
                            this.dataService.changeKafkaServiceName(input['tanzuExtensions']['logging']['kafkaEndpoint']['kafkaBrokerServiceName']);
                        }
                        if (input['tanzuExtensions']['logging']['kafkaEndpoint'].hasOwnProperty('kafkaTopicName')) {
                            this.dataService.changeKafkaTopicName(input['tanzuExtensions']['logging']['kafkaEndpoint']['kafkaTopicName']);
                        }
                    // } else if(input['tanzuExtensions']['logging']['splunkEndpoint']['enableSplunkEndpoint'] === 'true') {
                    //     this.dataService.changeEnableLoggingExtension(true);
                    //     this.dataService.changeLoggingEndpoint('Splunk');
                    //     if (input['tanzuExtensions']['logging']['splunkEndpoint'].hasOwnProperty('splunkEndpointAddress')) {
                    //         this.dataService.changeSplunkAddress(input['tanzuExtensions']['logging']['splunkEndpoint']['splunkEndpointAddress']);
                    //     }
                    //     if (input['tanzuExtensions']['logging']['splunkEndpoint'].hasOwnProperty('splunkEndpointPort')) {
                    //         this.dataService.changeSplunkPort(input['tanzuExtensions']['logging']['splunkEndpoint']['splunkEndpointPort']);
                    //     }
                    //     if (input['tanzuExtensions']['logging']['splunkEndpoint'].hasOwnProperty('splunkEndpointToken')) {
                    //         this.dataService.changeSplunkToken(input['tanzuExtensions']['logging']['splunkEndpoint']['splunkEndpointToken']);
                    //     }
                    } else {
                        this.dataService.changeEnableLoggingExtension(false);
                    }
                }
            }
        }
    }

    public processVmcEnableMonitoring(input) {
        if (input['tanzuExtensions']['monitoring']['enableLoggingExtension'] === 'true') {
            this.vmcDataService.changeEnableMonitoringExtension(true);
            this.vmcDataService.changePrometheusFqdn(input['tanzuExtensions']['monitoring']['prometheusFqdn']);
            this.vmcDataService.changePrometheusCertPath(input['tanzuExtensions']['monitoring']['prometheusCertPath']);
            this.vmcDataService.changePrometheusCertkeyPath(input['tanzuExtensions']['monitoring']['prometheusCertKeyPath']);
            this.vmcDataService.changeGrafanaFqdn(input['tanzuExtensions']['monitoring']['grafanaFqdn']);
            this.vmcDataService.changeGrafanaPassword(atob(input['tanzuExtensions']['monitoring']['grafanaPasswordBase64']));
            this.vmcDataService.changeGrafanaCertPath(input['tanzuExtensions']['monitoring']['grafanaCertPath']);
            this.vmcDataService.changeGrafanaCertKeyPath(input['tanzuExtensions']['monitoring']['grafanaCertKeyPath']);
        } else {
            this.vmcDataService.changeEnableMonitoringExtension(false);
        }
    }

    public processNsxtEnableLogging(input) {
        if (input['tanzuExtensions']['logging']['syslogEndpoint']['enableSyslogEndpoint'] === 'true') {
            this.nsxtDataService.changeEnableLoggingExtension(true);
            this.nsxtDataService.changeLoggingEndpoint('Syslog');
            this.nsxtDataService.changeSyslogAddress(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointAddress']);
            this.nsxtDataService.changeSyslogPort(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointPort']);
            this.nsxtDataService.changeSyslogMode(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointMode']);
            this.nsxtDataService.changeSyslogFormat(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointFormat']);
        } else if(input['tanzuExtensions']['logging']['httpEndpoint']['enableHttpEndpoint'] === 'true') {
            this.nsxtDataService.changeEnableLoggingExtension(true);
            this.nsxtDataService.changeLoggingEndpoint('HTTP');
            this.nsxtDataService.changeHttpAddress(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointAddress']);
            this.nsxtDataService.changeHttpPort(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointPort']);
            this.nsxtDataService.changeHttpUri(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointUri']);
            this.nsxtDataService.changeHttpHeaderKey(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointHeaderKeyValue']);
        // } else if(input['tanzuExtensions']['logging']['elasticSearchEndpoint']['enableElasticSearchEndpoint'] === 'true') {
        //     this.nsxtDataService.changeEnableLoggingExtension(true);
        //     this.nsxtDataService.changeLoggingEndpoint('Elastic Search');
        //     this.nsxtDataService.changeElasticSearchAddress(input['tanzuExtensions']['logging']['elasticSearchEndpoint']['elasticSearchEndpointAddress']);
        //     this.nsxtDataService.changeElasticSearchPort(input['tanzuExtensions']['logging']['elasticSearchEndpoint']['elasticSearchEndpointPort']);
        } else if(input['tanzuExtensions']['logging']['kafkaEndpoint']['enableKafkaEndpoint'] === 'true') {
            this.nsxtDataService.changeEnableLoggingExtension(true);
            this.nsxtDataService.changeLoggingEndpoint('Kafka');
            this.nsxtDataService.changeKafkaServiceName(input['tanzuExtensions']['logging']['kafkaEndpoint']['kafkaBrokerServiceName']);
            this.nsxtDataService.changeKafkaTopicName(input['tanzuExtensions']['logging']['kafkaEndpoint']['kafkaTopicName']);
        // } else if(input['tanzuExtensions']['logging']['splunkEndpoint']['enableSplunkEndpoint'] === 'true') {
        //     this.nsxtDataService.changeEnableLoggingExtension(true);
        //     this.nsxtDataService.changeLoggingEndpoint('Splunk');
        //     this.nsxtDataService.changeSplunkAddress(input['tanzuExtensions']['logging']['splunkEndpoint']['splunkEndpointAddress']);
        //     this.nsxtDataService.changeSplunkPort(input['tanzuExtensions']['logging']['splunkEndpoint']['splunkEndpointPort']);
        //     this.nsxtDataService.changeSplunkToken(input['tanzuExtensions']['logging']['splunkEndpoint']['splunkEndpointToken']);
        }
    }

    public processNsxtEnableMonitoring(input) {
        if (input['tanzuExtensions']['monitoring']['enableLoggingExtension'] === 'true') {
            this.nsxtDataService.changeEnableMonitoringExtension(true);
            this.nsxtDataService.changePrometheusFqdn(input['tanzuExtensions']['monitoring']['prometheusFqdn']);
            this.nsxtDataService.changePrometheusCertPath(input['tanzuExtensions']['monitoring']['prometheusCertPath']);
            this.nsxtDataService.changePrometheusCertkeyPath(input['tanzuExtensions']['monitoring']['prometheusCertKeyPath']);
            this.nsxtDataService.changeGrafanaFqdn(input['tanzuExtensions']['monitoring']['grafanaFqdn']);
            this.nsxtDataService.changeGrafanaPassword(atob(input['tanzuExtensions']['monitoring']['grafanaPasswordBase64']));
            this.nsxtDataService.changeGrafanaCertPath(input['tanzuExtensions']['monitoring']['grafanaCertPath']);
            this.nsxtDataService.changeGrafanaCertKeyPath(input['tanzuExtensions']['monitoring']['grafanaCertKeyPath']);
        } else {
            this.nsxtDataService.changeEnableMonitoringExtension(false);
        }
    }

    public processVmcEnableLogging(input) {
        if (input['tanzuExtensions']['logging']['syslogEndpoint']['enableSyslogEndpoint'] === 'true') {
            this.vmcDataService.changeEnableLoggingExtension(true);
            this.vmcDataService.changeLoggingEndpoint('Syslog');
            this.vmcDataService.changeSyslogAddress(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointAddress']);
            this.vmcDataService.changeSyslogPort(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointPort']);
            this.vmcDataService.changeSyslogMode(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointMode']);
            this.vmcDataService.changeSyslogFormat(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointFormat']);
        } else if(input['tanzuExtensions']['logging']['httpEndpoint']['enableHttpEndpoint'] === 'true') {
            this.vmcDataService.changeEnableLoggingExtension(true);
            this.vmcDataService.changeLoggingEndpoint('HTTP');
            this.vmcDataService.changeHttpAddress(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointAddress']);
            this.vmcDataService.changeHttpPort(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointPort']);
            this.vmcDataService.changeHttpUri(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointUri']);
            this.vmcDataService.changeHttpHeaderKey(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointHeaderKeyValue']);
        } else if(input['tanzuExtensions']['logging']['elasticSearchEndpoint']['enableElasticSearchEndpoint'] === 'true') {
            this.vmcDataService.changeEnableLoggingExtension(true);
            this.vmcDataService.changeLoggingEndpoint('Elastic Search');
            this.vmcDataService.changeElasticSearchAddress(input['tanzuExtensions']['logging']['elasticSearchEndpoint']['elasticSearchEndpointAddress']);
            this.vmcDataService.changeElasticSearchPort(input['tanzuExtensions']['logging']['elasticSearchEndpoint']['elasticSearchEndpointPort']);
        } else if(input['tanzuExtensions']['logging']['kafkaEndpoint']['enableKafkaEndpoint'] === 'true') {
            this.vmcDataService.changeEnableLoggingExtension(true);
            this.vmcDataService.changeLoggingEndpoint('Kafka');
            this.vmcDataService.changeKafkaServiceName(input['tanzuExtensions']['logging']['kafkaEndpoint']['kafkaBrokerServiceName']);
            this.vmcDataService.changeKafkaTopicName(input['tanzuExtensions']['logging']['kafkaEndpoint']['kafkaTopicName']);
        } else if(input['tanzuExtensions']['logging']['splunkEndpoint']['enableSplunkEndpoint'] === 'true') {
            this.vmcDataService.changeEnableLoggingExtension(true);
            this.vmcDataService.changeLoggingEndpoint('Splunk');
            this.vmcDataService.changeSplunkAddress(input['tanzuExtensions']['logging']['splunkEndpoint']['splunkEndpointAddress']);
            this.vmcDataService.changeSplunkPort(input['tanzuExtensions']['logging']['splunkEndpoint']['splunkEndpointPort']);
            this.vmcDataService.changeSplunkToken(input['tanzuExtensions']['logging']['splunkEndpoint']['splunkEndpointToken']);
        }
    }
    public setVmcParamsFromInputJSON(input) {
        if (input) {
            this.vmcDataService.changeInputFileStatus(true);
            // Dumy Component
            let dns = input['envVariablesSpec']['dnsServersIp'];
            let ntp = input['envVariablesSpec']['ntpServersIp'];
            this.vmcDataService.changeDnsServer(dns);
            this.vmcDataService.changeNtpServer(ntp);
            // Iaas Provider
            this.vmcDataService.changeSddcToken(input['envSpec']['sddcRefreshToken']);
            this.vmcDataService.changeOrgName(input['envSpec']['orgName']);
            this.vmcDataService.changeSddcName(input['envSpec']['sddcName']);
            this.vmcDataService.changeDatacenter(input['envSpec']['sddcDatacenter']);
            this.vmcDataService.changeCluster(input['envSpec']['sddcCluster']);
            this.vmcDataService.changeDatastore(input['envSpec']['sddcDatastore']);

            // Tanzu SaaS Endpoints
            if (input['saasEndpoints']['tmcDetails']['tmcAvailability'] === 'true') {
                this.vmcDataService.changeEnableTMC(true);
                this.vmcDataService.changeApiToken(input['saasEndpoints']['tmcDetails']['tmcRefreshToken']);
            } else {
                this.vmcDataService.changeEnableTMC(false);
            }
            if (input['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityAvailability'] === 'true') {
                this.vmcDataService.changeEnableTO(true);
                this.vmcDataService.changeTOUrl(input['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityUrl']);
                this.vmcDataService.changeTOApiToken(input['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityRefreshToken']);
            } else {
                this.vmcDataService.changeEnableTO(false);
            }
            // AVI Component
            this.vmcDataService.changeAviPassword(atob(input['componentSpec']['aviComponentSpec']['aviPasswordBase64']));
            this.vmcDataService.changeAviBackupPassword(atob(input['componentSpec']['aviComponentSpec']['aviBackupPassPhraseBase64']));
            this.vmcDataService.changeAviGateway(input['componentSpec']['aviMgmtNetworkSpec']['aviMgmtGatewayCidr']);
            this.vmcDataService.changeAviDhcpStart(input['componentSpec']['aviMgmtNetworkSpec']['aviMgmtDhcpStartRange']);
            this.vmcDataService.changeAviDhcpEnd(input['componentSpec']['aviMgmtNetworkSpec']['aviMgmtDhcpEndRange']);
            this.vmcDataService.changeAviClusterVipNetworkName(input['componentSpec']['aviClusterVipNetwork']['aviClusterVipNetworkName']);
            this.vmcDataService.changeAviClusterVipGatewayIp(input['componentSpec']['aviClusterVipNetwork']['aviClusterVipNetworkGatewayCidr']);
            this.vmcDataService.changeAviClusterVipStartIp(input['componentSpec']['aviClusterVipNetwork']['aviClusterVipDhcpStartRange']);
            this.vmcDataService.changeAviClusterVipEndIp(input['componentSpec']['aviClusterVipNetwork']['aviClusterVipDhcpEndRange']);
            this.vmcDataService.changeAviClusterVipSeStartIp(input['componentSpec']['aviClusterVipNetwork']['aviClusterVipIpStartRange']);
            this.vmcDataService.changeAviClusterVipSeEndIp(input['componentSpec']['aviClusterVipNetwork']['aviClusterVipIpEndRange']);
            // TKG Mgmt Data Network
            this.vmcDataService.changeTkgMgmtDataGateway(input['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataGatewayCidr']);
            this.vmcDataService.changeTkgMgmtDataDhcpStart(input['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataDhcpStartRange']);
            this.vmcDataService.changeTkgMgmtDataDhcpEnd(input['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataDhcpEndRange']);
            this.vmcDataService.changeTkgMgmtDataServiceStart(input['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataServiceStartRange']);
            this.vmcDataService.changeTkgMgmtDataServiceEnd(input['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataServiceEndRange']);
            // TKG Mgmt Cluster Settings
            this.vmcDataService.changeMgmtClusterName(input['componentSpec']['tkgMgmtSpec']['tkgMgmtClusterName']);
            this.vmcDataService.changeMgmtDeploymentType(input['componentSpec']['tkgMgmtSpec']['tkgMgmtDeploymentType']);
            this.vmcDataService.changeMgmtDeploymentSize(input['componentSpec']['tkgMgmtSpec']['tkgMgmtSize']);
            this.vmcDataService.changeMgmtSegment(input['componentSpec']['tkgMgmtSpec']['tkgMgmtNetworkName']);
            this.vmcDataService.changeMgmtGateway(input['componentSpec']['tkgMgmtSpec']['tkgMgmtGatewayCidr']);
            // Shared Service Cluster Settings
            this.vmcDataService.changeSharedDeploymentType(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceDeploymentType']);
            this.vmcDataService.changeSharedDeploymentSize(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceSize']);
            this.vmcDataService.changeSharedClusterName(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedClusterName']);
            this.vmcDataService.changeSharedWorkerNodeCount(input['componentSpec']['tkgSharedServiceSpec']['tkSharedserviceWorkerMachineCount']);
            this.vmcDataService.changeSharedGateway(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedGatewayCidr']);
            this.vmcDataService.changeSharedDhcpStart(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedDhcpStartRange']);
            this.vmcDataService.changeSharedDhcpEnd(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedDhcpEndRange']);
            this.vmcDataService.changeEnableHarbor(true);
            this.vmcDataService.changeHarborFqdn(input['componentSpec']['harborSpec']['harborFqdn']);
            this.vmcDataService.changeHarborPassword(atob(input['componentSpec']['harborSpec']['harborPasswordBase64']));
            this.vmcDataService.changeHarborCertPath(input['componentSpec']['harborSpec']['harborCertPath']);
            this.vmcDataService.changeHarborCertKey(input['componentSpec']['harborSpec']['harborCertKeyPath']);
            // TKG Workload Data Network Settings
            this.vmcDataService.changeTkgWrkDataGateway(input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataGatewayCidr']);
            this.vmcDataService.changeTkgWrkDataDhcpStart(input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataDhcpStartRange']);
            this.vmcDataService.changeTkgWrkDataDhcpEnd(input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataDhcpEndRange']);
            this.vmcDataService.changeTkgWrkDataServiceStart(input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataServiceStartRange']);
            this.vmcDataService.changeTkgWrkDataServiceEnd(input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataServiceEndRange']);
            // Workload Cluster Settings
            this.vmcDataService.changeWrkDeploymentType(input['componentSpec']['tkgWorkloadSpec']['tkWorkloadDeploymentType']);
            this.vmcDataService.changeWrkDeploymentSize(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadSize']);
            this.vmcDataService.changeWrkWorkerNodeCount(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadWorkerMachineCount']);
            this.vmcDataService.changeWrkClusterName(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterName']);
            this.vmcDataService.changeWrkGateway(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadGatewayCidr']);
            this.vmcDataService.changeWrkDhcpStart(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadDhcpStartRange']);
            this.vmcDataService.changeWrkDhcpEnd(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadDhcpEndRange']);
            // Extension
            if(input['tanzuExtensions']['enableExtensions'] === 'true') {
                this.vmcDataService.changeEnableTanzuExtension(true);
            } else {
                this.vmcDataService.changeEnableTanzuExtension(false);
            }
            if (input['tanzuExtensions']['enableExtensions'] === 'true') {
                this.vmcDataService.changeTkgClusters(input['tanzuExtensions']['tkgClustersName']);
                this.processVmcEnableLogging(input);
                this.processVmcEnableMonitoring(input);
            } else {
                this.vmcDataService.changeEnableLoggingExtension(false);
                this.vmcDataService.changeEnableMonitoringExtension(false);
            }
            this.errorNotification = '';
        } else {
            this.errorNotification = 'Error Occurred while reading ' + this.fileName + ' file';
        }
    }

    public setParamsFromInputJSON(input) {
        if (input) {
            this.nsxtDataService.changeInputFileStatus(true);
            let missingKeys;
            // Dumy Component
            if (input.hasOwnProperty('envSpec')) {
                if (input['envSpec'].hasOwnProperty('infraComponents')) {
                    if (input['envSpec']['infraComponents'].hasOwnProperty('dnsServersIp')) {
                        const dns = input['envSpec']['infraComponents']['dnsServersIp'];
                        this.nsxtDataService.changeDnsServer(dns);
                    }
                    if (input['envSpec']['infraComponents'].hasOwnProperty('ntpServers')) {
                        const ntp = input['envSpec']['infraComponents']['ntpServers'];
                        this.nsxtDataService.changeNtpServer(ntp);
                    }
                    if (input['envSpec']['infraComponents'].hasOwnProperty('searchDomains')) {
                        const searchDomain = input['envSpec']['infraComponents']['searchDomains'];
                        this.nsxtDataService.changeSearchDomain(searchDomain);
                    }
                }
                if (input['envSpec'].hasOwnProperty('proxySpec')) {
                    if (input['envSpec']['proxySpec'].hasOwnProperty('arcasVm')) {
                        if (input['envSpec']['proxySpec']['arcasVm'].hasOwnProperty('enableProxy')) {
                            if (input['envSpec']['proxySpec']['arcasVm']['enableProxy'] === 'true') {
                                this.nsxtDataService.changeArcasEnableProxy(true);
                                if (input['envSpec']['proxySpec']['arcasVm'].hasOwnProperty('httpProxy') &&
                                    input['envSpec']['proxySpec']['arcasVm'].hasOwnProperty('httpsProxy')) {
                                        this.processNsxtArcasProxyParam(input);
                                    }
                                if (input['envSpec']['proxySpec']['arcasVm'].hasOwnProperty('noProxy')) {
                                    this.nsxtDataService.changeArcasNoProxy(
                                        input['envSpec']['proxySpec']['arcasVm']['noProxy']);
                                }
                            } else {
                                this.nsxtDataService.changeArcasEnableProxy(false);
                            }
                        }
                    }
                    if (input['envSpec']['proxySpec'].hasOwnProperty('tkgMgmt')) {
                        if (input['envSpec']['proxySpec']['tkgMgmt'].hasOwnProperty('enableProxy')) {
                            if (input['envSpec']['proxySpec']['tkgMgmt']['enableProxy'] === 'true') {
                                this.nsxtDataService.changeMgmtEnableProxy(true);
                                if (input['envSpec']['proxySpec']['tkgMgmt'].hasOwnProperty('httpProxy') &&
                                    input['envSpec']['proxySpec']['tkgMgmt'].hasOwnProperty('httpsProxy')) {
                                        this.processNsxtMgmtProxyParam(input);
                                    }
                                if (input['envSpec']['proxySpec']['tkgMgmt'].hasOwnProperty('noProxy')) {
                                    this.nsxtDataService.changeMgmtNoProxy(
                                        input['envSpec']['proxySpec']['tkgMgmt']['noProxy']);
                                }
                            } else {
                                this.nsxtDataService.changeMgmtEnableProxy(false);
                            }
                        }
                    }
                    if (input['envSpec']['proxySpec'].hasOwnProperty('tkgSharedservice')) {
                        if (input['envSpec']['proxySpec']['tkgSharedservice'].hasOwnProperty('enableProxy')) {
                            if (input['envSpec']['proxySpec']['tkgSharedservice']['enableProxy'] === 'true') {
                                this.nsxtDataService.changeSharedEnableProxy(true);
                                if (input['envSpec']['proxySpec']['tkgSharedservice'].hasOwnProperty('httpProxy') &&
                                    input['envSpec']['proxySpec']['tkgSharedservice'].hasOwnProperty('httpsProxy')) {
                                    this.processNsxtSharedProxyParam(input);
                                }
                                if (input['envSpec']['proxySpec']['tkgSharedservice'].hasOwnProperty('noProxy')) {
                                    this.nsxtDataService.changeSharedNoProxy(
                                        input['envSpec']['proxySpec']['tkgSharedservice']['noProxy']);
                                }
                            } else {
                                this.nsxtDataService.changeSharedEnableProxy(false);
                            }
                        }
                    }
                    if (input['envSpec']['proxySpec'].hasOwnProperty('tkgWorkload')) {
                        if (input['envSpec']['proxySpec']['tkgWorkload'].hasOwnProperty('enableProxy')) {
                            if (input['envSpec']['proxySpec']['tkgWorkload']['enableProxy'] === 'true') {
                                this.nsxtDataService.changeWrkEnableProxy(true);
                                if (input['envSpec']['proxySpec']['tkgWorkload'].hasOwnProperty('httpProxy') &&
                                    input['envSpec']['proxySpec']['tkgWorkload'].hasOwnProperty('httpProxy')) {
                                        this.processNsxtWrkProxyParam(input);
                                    }
                                if (input['envSpec']['proxySpec']['tkgWorkload'].hasOwnProperty('noProxy')) {
                                    this.nsxtDataService.changeWrkNoProxy(
                                        input['envSpec']['proxySpec']['tkgWorkload']['noProxy']);
                                }
                            } else {
                                this.nsxtDataService.changeWrkEnableProxy(false);
                            }
                        }
                    }
                }
                if (input['envSpec'].hasOwnProperty('vcenterDetails')) {
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterAddress')) {
                        this.nsxtDataService.changeVCAddress(
                            input['envSpec']['vcenterDetails']['vcenterAddress']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterSsoUser')) {
                        this.nsxtDataService.changeVCUser(
                            input['envSpec']['vcenterDetails']['vcenterSsoUser']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterSsoPasswordBase64')) {
                        this.nsxtDataService.changeVCPass(
                            atob(input['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']));
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterDatastore')) {
                        this.nsxtDataService.changeDatastore(
                            input['envSpec']['vcenterDetails']['vcenterDatastore']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterCluster')) {
                        this.nsxtDataService.changeCluster(
                            input['envSpec']['vcenterDetails']['vcenterCluster']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterDatacenter')) {
                        this.nsxtDataService.changeDatacenter(
                            input['envSpec']['vcenterDetails']['vcenterDatacenter']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('contentLibraryName')) {
                        if(input['envSpec']['vcenterDetails']['contentLibraryName'] !== '') {
                            this.nsxtDataService.changeIsCustomerConnect(false);
                        }
                        this.nsxtDataService.changeContentLib(
                            input['envSpec']['vcenterDetails']['contentLibraryName']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('aviOvaName')) {
                        if (input['envSpec']['vcenterDetails']['aviOvaName'] !== '') {
                            this.nsxtDataService.changeIsCustomerConnect(false);
                        }
                        this.nsxtDataService.changeOvaImage(
                            input['envSpec']['vcenterDetails']['aviOvaName']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('resourcePoolName')) {
                        this.nsxtDataService.changeResourcePool(
                            input['envSpec']['vcenterDetails']['resourcePoolName']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('nsxtAddress')) {
                        this.nsxtDataService.changeNsxtAddress(
                            input['envSpec']['vcenterDetails']['nsxtAddress']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('nsxtUser')) {
                        this.nsxtDataService.changeNsxtUsername(
                            input['envSpec']['vcenterDetails']['nsxtUser']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('nsxtUserPasswordBase64')) {
                        this.nsxtDataService.changeNsxtPassword(
                            atob(input['envSpec']['vcenterDetails']['nsxtUserPasswordBase64']));
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('nsxtTier1RouterDisplayName')) {
                        this.nsxtDataService.changeTier1Router(
                            input['envSpec']['vcenterDetails']['nsxtTier1RouterDisplayName']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('nsxtOverlay')) {
                        this.nsxtDataService.changeNsxtOverlay(
                            input['envSpec']['vcenterDetails']['nsxtOverlay']);
                    }
                }
                // if (input['envSpec'].hasOwnProperty('resource-spec')) {
                //     if (input['envSpec']['resource-spec'].hasOwnProperty('customer-connect-user')) {
                //         if (input['envSpec']['vcenterDetails']['aviOvaName'] === '' &&
                //             input['envSpec']['vcenterDetails']['contentLibraryName'] === '') {
                //                 if(input['envSpec']['resource-spec']['customer-connect-user'] !== '') {
                //                     this.nsxtDataService.changeIsCustomerConnect(true);
                //                 }
                //             }
                //         this.nsxtDataService.changeCustUsername(
                //             input['envSpec']['resource-spec']['customer-connect-user']);
                //     }
                //     if (input['envSpec']['resource-spec'].hasOwnProperty('customer-connect-password-base64')) {
                //         this.nsxtDataService.changeCustPassword(
                //             atob(input['envSpec']['resource-spec']['customer-connect-password-base64']));
                //     }
                //     if (input['envSpec']['resource-spec'].hasOwnProperty('avi-pulse-jwt-token')) {
                //         this.nsxtDataService.changeJwtToken(
                //             input['envSpec']['resource-spec']['avi-pulse-jwt-token']);
                //     }
                //     if (input['envSpec']['resource-spec'].hasOwnProperty('kubernetes-ova')) {
                //         this.nsxtDataService.changeKubernetesOva(
                //             input['envSpec']['resource-spec']['kubernetes-ova']);
                //     }
                // }
                if (input['envSpec'].hasOwnProperty('marketplaceSpec')) {
                    if (input['envSpec']['marketplaceSpec'].hasOwnProperty('refreshToken')) {
                        if (input['envSpec']['vcenterDetails']['aviOvaName'] === '' &&
                            input['envSpec']['vcenterDetails']['contentLibraryName'] === '') {
                            if (input['envSpec']['marketplaceSpec']['refreshToken'] !== '') {
                                this.nsxtDataService.changeIsMarketplace(true);
                            }
                        }
                        this.nsxtDataService.changeMarketplaceRefreshToken(
                            input['envSpec']['marketplaceSpec']['refreshToken']);
                    }
                }
                if (input['envSpec'].hasOwnProperty('saasEndpoints')) {
                    if (input['envSpec']['saasEndpoints'].hasOwnProperty('tmcDetails')) {
                        if (input['envSpec']['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcAvailability')) {
                            if (input['envSpec']['saasEndpoints']['tmcDetails']['tmcAvailability'] === 'true') {
                                this.apiClient.tmcEnabled = true;
                                this.nsxtDataService.changeEnableTMC(true);
                                if (input['envSpec']['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcRefreshToken')) {
                                    this.nsxtDataService.changeApiToken(
                                        input['envSpec']['saasEndpoints']['tmcDetails']['tmcRefreshToken']);
                                }
                                if (input['envSpec']['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcInstanceURL')) {
                                    this.nsxtDataService.changeInstanceUrl(
                                        input['envSpec']['saasEndpoints']['tmcDetails']['tmcInstanceURL']);
                                }
                                if (input['envSpec']['saasEndpoints'].hasOwnProperty('tanzuObservabilityDetails')) {
                                    if (input['envSpec']['saasEndpoints']['tanzuObservabilityDetails'].hasOwnProperty('tanzuObservabilityAvailability')) {
                                        if (input['envSpec']['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityAvailability'] === 'true') {
                                            this.nsxtDataService.changeEnableTO(true);
                                            this.apiClient.toEnabled = true;
                                            if (input['envSpec']['saasEndpoints']['tanzuObservabilityDetails'].hasOwnProperty('tanzuObservabilityUrl')) {
                                                this.nsxtDataService.changeTOUrl(
                                                    input['envSpec']['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityUrl']);
                                            }
                                            if (input['envSpec']['saasEndpoints']['tanzuObservabilityDetails'].hasOwnProperty('tanzuObservabilityRefreshToken')) {
                                                this.nsxtDataService.changeTOApiToken(
                                                    input['envSpec']['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityRefreshToken']);
                                            }
                                        } else {
                                            this.apiClient.toEnabled = false;
                                            this.nsxtDataService.changeEnableTO(false);
                                        }
                                    }
                                }
                            } else {
                                this.apiClient.tmcEnabled = false;
                                this.nsxtDataService.changeEnableTMC(false);
                                this.apiClient.toEnabled = false;
                                this.nsxtDataService.changeEnableTO(false);
                                this.nsxtDataService.changeEnableTSM(false);
                            }
                        } else {
                            this.apiClient.tmcEnabled = false;
                            this.nsxtDataService.changeEnableTMC(false);
                            this.apiClient.toEnabled = false;
                            this.nsxtDataService.changeEnableTO(false);
                            this.nsxtDataService.changeEnableTSM(false);
                        }
                    } else {
                        this.apiClient.tmcEnabled = false;
                        this.nsxtDataService.changeEnableTMC(false);
                        this.apiClient.toEnabled = false;
                        this.nsxtDataService.changeEnableTO(false);
                        this.nsxtDataService.changeEnableTSM(false);
                    }
                }
                if (input['envSpec'].hasOwnProperty('customRepositorySpec')) {
                    if (input['envSpec']['customRepositorySpec'].hasOwnProperty('tkgCustomImageRepository')) {
                        if (input['envSpec']['customRepositorySpec']['tkgCustomImageRepository'] !== '') {
                            this.nsxtDataService.changeEnableRepoSettings(true);
                            this.nsxtDataService.changeRepoImage(
                                input['envSpec']['customRepositorySpec']['tkgCustomImageRepository']);
                            if (input['envSpec']['customRepositorySpec'].hasOwnProperty('tkgCustomImageRepositoryPublicCaCert')) {
                                if (input['envSpec']['customRepositorySpec']['tkgCustomImageRepositoryPublicCaCert'] === 'true') {
                                    this.nsxtDataService.changeCaCert(true);
                                } else {
                                    this.nsxtDataService.changeCaCert(false);
                                }
                            }
//                             if (input['envSpec']['customRepositorySpec'].hasOwnProperty('tkgCustomImageRepositoryUsername')) {
//                                 this.nsxtDataService.changeRepoUsername(
//                                     input['envSpec']['customRepositorySpec']['tkgCustomImageRepositoryUsername']);
//                             }
//                             if (input['envSpec']['customRepositorySpec'].hasOwnProperty('tkgCustomImageRepositoryPasswordBase64')) {
//                                 this.nsxtDataService.changeRepoPassword(
//                                    atob(input['envSpec']['customRepositorySpec']['tkgCustomImageRepositoryPasswordBase64']));
//                             }
                        } else {
                            this.nsxtDataService.changeEnableRepoSettings(false);
                        }
                    }
                }
            }
            if (input.hasOwnProperty('tkgComponentSpec')) {
                if (input['tkgComponentSpec'].hasOwnProperty('aviComponents')) {
                    if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviController01Fqdn')) {
                        this.nsxtDataService.changeAviFqdn(
                            input['tkgComponentSpec']['aviComponents']['aviController01Fqdn']);
                    }
                    if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviController01Ip')) {
                        this.nsxtDataService.changeAviIp(
                            input['tkgComponentSpec']['aviComponents']['aviController01Ip']);
                    }
                    if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('enableAviHa')) {
                        if(input['tkgComponentSpec']['aviComponents']['enableAviHa'] === 'true') {
                            this.nsxtDataService.changeEnableAviHA(true);
                            if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviController02Fqdn')) {
                                this.nsxtDataService.changeAviFqdn02(
                                    input['tkgComponentSpec']['aviComponents']['aviController02Fqdn']);
                            }
                            if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviController02Ip')) {
                                this.nsxtDataService.changeAviIp02(
                                    input['tkgComponentSpec']['aviComponents']['aviController02Ip']);
                            }
                            if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviController03Fqdn')) {
                                this.nsxtDataService.changeAviFqdn03(
                                    input['tkgComponentSpec']['aviComponents']['aviController03Fqdn']);
                            }
                            if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviController03Ip')) {
                                this.nsxtDataService.changeAviIp03(
                                    input['tkgComponentSpec']['aviComponents']['aviController03Ip']);
                            }
                            if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviClusterIp')) {
                                this.nsxtDataService.changeAviClusterIp(
                                    input['tkgComponentSpec']['aviComponents']['aviClusterIp']);
                            }
                            if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviClusterFqdn')) {
                                this.nsxtDataService.changeAviClusterFqdn(
                                    input['tkgComponentSpec']['aviComponents']['aviClusterFqdn']);
                            }
                        } else {
                            this.nsxtDataService.changeEnableAviHA(false);
                        }
                    }
                    if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviSize')) {
                        this.nsxtDataService.changeAviSize(input['tkgComponentSpec']['aviComponents']['aviSize']);
                    }
                    if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviCertPath')) {
                        this.nsxtDataService.changeAviCertPath(input['tkgComponentSpec']['aviComponents']['aviCertPath']);
                    }
                    if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviCertKeyPath')) {
                        this.nsxtDataService.changeAviCertKeyPath(input['tkgComponentSpec']['aviComponents']['aviCertKeyPath']);
                    }
//                     if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviLicenseKey')) {
//                         this.nsxtDataService.changeAviLicenseKey(input['tkgComponentSpec']['aviComponents']['aviLicenseKey']);
//                     }
                    if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviPasswordBase64')) {
                        this.nsxtDataService.changeAviPassword(
                            atob(input['tkgComponentSpec']['aviComponents']['aviPasswordBase64']));
                    }
                    if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviBackupPassphraseBase64')) {
                        this.nsxtDataService.changeAviBackupPassword(
                            atob(input['tkgComponentSpec']['aviComponents']['aviBackupPassphraseBase64']));
                    }
                }
                if (input['tkgComponentSpec'].hasOwnProperty('aviMgmtNetwork')) {
                    if (input['tkgComponentSpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtNetworkName')) {
                        this.nsxtDataService.changeAviSegment(
                            input['tkgComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkName']);
                    }
                    if (input['tkgComponentSpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtNetworkGatewayCidr')) {
                        this.nsxtDataService.changeAviGateway(
                            input['tkgComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkGatewayCidr']);
                    }
                    if (input['tkgComponentSpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtServiceIpStartRange')) {
                        this.nsxtDataService.changeAviDhcpStart(
                            input['tkgComponentSpec']['aviMgmtNetwork']['aviMgmtServiceIpStartRange']);
                    }
                    if (input['tkgComponentSpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtServiceIpEndRange')) {
                        this.nsxtDataService.changeAviDhcpEnd(
                            input['tkgComponentSpec']['aviMgmtNetwork']['aviMgmtServiceIpEndRange']);
                    }
                }
                if (input['tkgComponentSpec'].hasOwnProperty('tkgClusterVipNetwork')) {
                    if (input['tkgComponentSpec']['tkgClusterVipNetwork'].hasOwnProperty('tkgClusterVipNetworkName')) {
                        this.nsxtDataService.changeAviClusterVipNetworkName(
                            input['tkgComponentSpec']['tkgClusterVipNetwork']['tkgClusterVipNetworkName']);
                    }
                    if (input['tkgComponentSpec']['tkgClusterVipNetwork'].hasOwnProperty('tkgClusterVipNetworkGatewayCidr')) {
                        this.nsxtDataService.changeAviClusterVipGatewayIp(
                            input['tkgComponentSpec']['tkgClusterVipNetwork']['tkgClusterVipNetworkGatewayCidr']);
                    }
                    if (input['tkgComponentSpec']['tkgClusterVipNetwork'].hasOwnProperty('tkgClusterVipIpStartRange')) {
                        this.nsxtDataService.changeAviClusterVipStartIp(
                            input['tkgComponentSpec']['tkgClusterVipNetwork']['tkgClusterVipIpStartRange']);
                    }
                    if (input['tkgComponentSpec']['tkgClusterVipNetwork'].hasOwnProperty('tkgClusterVipIpEndRange')) {
                        this.nsxtDataService.changeAviClusterVipEndIp(
                            input['tkgComponentSpec']['tkgClusterVipNetwork']['tkgClusterVipIpEndRange']);
                    }
                }
                if(input['tkgComponentSpec'].hasOwnProperty('identityManagementSpec')){
                    if (input['tkgComponentSpec']['identityManagementSpec'].hasOwnProperty('identityManagementType')){
                        if (input['tkgComponentSpec']['identityManagementSpec']['identityManagementType'] === 'oidc'){
                            this.nsxtDataService.changeIdentityManagementType('oidc');
                            this.nsxtDataService.changeEnableIdentityManagement(true);
                            this.apiClient.enableIdentityManagement = true;
                            if (input['tkgComponentSpec']['identityManagementSpec'].hasOwnProperty('oidcSpec')) {
                                if (input['tkgComponentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcIssuerUrl')) {
                                    this.nsxtDataService.changeOidcIssuerUrl(
                                        input['tkgComponentSpec']['identityManagementSpec']['oidcSpec']['oidcIssuerUrl']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcClientId')) {
                                    this.nsxtDataService.changeOidcClientId(
                                        input['tkgComponentSpec']['identityManagementSpec']['oidcSpec']['oidcClientId']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcClientSecret')) {
                                    this.nsxtDataService.changeOidcClientSecret(
                                        input['tkgComponentSpec']['identityManagementSpec']['oidcSpec']['oidcClientSecret']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcScopes')) {
                                    this.nsxtDataService.changeOidcScopes(
                                        input['tkgComponentSpec']['identityManagementSpec']['oidcSpec']['oidcScopes']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcUsernameClaim')) {
                                    this.nsxtDataService.changeOidcUsernameClaim(
                                        input['tkgComponentSpec']['identityManagementSpec']['oidcSpec']['oidcUsernameClaim']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcGroupsClaim')) {
                                    this.nsxtDataService.changeOidcGroupClaim(
                                        input['tkgComponentSpec']['identityManagementSpec']['oidcSpec']['oidcGroupsClaim']);
                                }
                            }
                        } else if (input['tkgComponentSpec']['identityManagementSpec']['identityManagementType'] === 'ldap') {
                            this.nsxtDataService.changeIdentityManagementType('ldap');
                            this.nsxtDataService.changeEnableIdentityManagement(true);
                            this.apiClient.enableIdentityManagement = true;
                            if (input['tkgComponentSpec']['identityManagementSpec'].hasOwnProperty('ldapSpec')) {
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapEndpointIp')) {
                                    this.nsxtDataService.changeLdapEndpointIp(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapEndpointIp']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapEndpointPort')) {
                                    this.nsxtDataService.changeLdapEndpointPort(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapEndpointPort']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapBindPWBase64')) {
                                    this.nsxtDataService.changeLdapBindPw(
                                        atob(input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapBindPWBase64']));
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapBindDN')) {
                                    this.nsxtDataService.changeLdapBindDN(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapBindDN']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapUserSearchBaseDN')) {
                                    this.nsxtDataService.changeLdapUserSearchBaseDN(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapUserSearchBaseDN']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapUserSearchFilter')) {
                                    this.nsxtDataService.changeLdapUserSearchFilter(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapUserSearchFilter']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapUserSearchUsername')) {
                                    this.nsxtDataService.changeLdapUserSearchUsername(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapUserSearchUsername']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapGroupSearchBaseDN')) {
                                    this.nsxtDataService.changeLdapGroupSearchBaseDN(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapGroupSearchBaseDN']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapGroupSearchFilter')) {
                                    this.nsxtDataService.changeLdapGroupSearchFilter(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapGroupSearchFilter']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapGroupSearchUserAttr')) {
                                    this.nsxtDataService.changeLdapGroupSearchUserAttr(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapGroupSearchUserAttr']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapGroupSearchGroupAttr')) {
                                    this.nsxtDataService.changeLdapGroupSearchGroupAttr(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapGroupSearchGroupAttr']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapGroupSearchNameAttr')) {
                                    this.nsxtDataService.changeLdapGroupSearchNameAttr(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapGroupSearchNameAttr']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapRootCAData')) {
                                    this.nsxtDataService.changeLdapRootCAData(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapRootCAData']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapTestUserName')) {
                                    this.nsxtDataService.changeLdapTestUserName(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapTestUserName']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapTestGroupName')) {
                                    this.nsxtDataService.changeLdapTestGroupName(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapTestGroupName']);
                                }
                            }
                        }
                        else {
                            this.nsxtDataService.changeEnableIdentityManagement(false);
                            this.apiClient.enableIdentityManagement = false;
                        }
                    } else {
                        this.nsxtDataService.changeEnableIdentityManagement(false);
                        this.apiClient.enableIdentityManagement = false;
                    }
                } else {
                    this.nsxtDataService.changeEnableIdentityManagement(false);
                    this.apiClient.enableIdentityManagement = false;
                }
                if (input['tkgComponentSpec'].hasOwnProperty('tkgMgmtComponents')) {
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtSize')) {
                        this.nsxtDataService.changeMgmtDeploymentSize(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtSize']);
                    }
                    if(input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtCpuSize')) {
                        this.nsxtDataService.changeMgmtCpu(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtCpuSize']);
                    }
                    if(input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtMemorySize')) {
                        this.nsxtDataService.changeMgmtMemory(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtMemorySize']);
                    }
                    if(input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtStorageSize')) {
                        this.nsxtDataService.changeMgmtStorage(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtStorageSize']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtDeploymentType')) {
                        this.nsxtDataService.changeMgmtDeploymentType(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtDeploymentType']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtClusterName')) {
                        this.nsxtDataService.changeMgmtClusterName(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterName']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtGatewayCidr')) {
                        this.nsxtDataService.changeMgmtGateway(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtGatewayCidr']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtNetworkName')) {
                        this.nsxtDataService.changeMgmtSegment(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtNetworkName']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtClusterCidr')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterCidr'] !== '') {
                            this.nsxtDataService.changeMgmtClusterCidr(
                                input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterCidr']);
                        }
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtServiceCidr')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtServiceCidr'] !== '') {
                            this.nsxtDataService.changeMgmtServiceCidr(
                                input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtServiceCidr']);
                        }
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtBaseOs')) {
                        this.nsxtDataService.changeMgmtBaseImage(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtBaseOs']);
                    }
                    if (this.apiClient.enableIdentityManagement) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtRbacUserRoleSpec')) {
                            if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec'].hasOwnProperty('clusterAdminUsers')) {
                                this.nsxtDataService.changeMgmtClusterAdminUsers(
                                    input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec']['clusterAdminUsers']);
                            }
                            if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec'].hasOwnProperty('adminUsers')) {
                                this.nsxtDataService.changeMgmtAdminUsers(
                                    input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec']['adminUsers']);
                            }
                            if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec'].hasOwnProperty('editUsers')) {
                                this.nsxtDataService.changeMgmtEditUsers(
                                    input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec']['editUsers']);
                            }
                            if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec'].hasOwnProperty('viewUsers')) {
                                this.nsxtDataService.changeMgmtViewUsers(
                                    input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec']['viewUsers']);
                            }
                        }
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtClusterGroupName')) {
                        this.nsxtDataService.changeMgmtClusterGroupName(input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterGroupName']);
                    }
                }
                if (input['tkgComponentSpec'].hasOwnProperty('tkgSharedserviceSpec')) {
                    if (input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceNetworkName')) {
                        this.nsxtDataService.changeSharedSegmentName(
                            input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceNetworkName']);
                    }
                    if (input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceGatewayCidr')) {
                        this.nsxtDataService.changeSharedGatewayAddress(
                            input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceGatewayCidr']);
                    }
                    if (input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceDhcpStartRange')) {
                        this.nsxtDataService.changeSharedDhcpStart(
                            input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceDhcpStartRange']);
                    }
                    if (input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceDhcpEndRange')) {
                        this.nsxtDataService.changeSharedDhcpEnd(
                            input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceDhcpEndRange']);
                    }
                    if (input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceClusterName')) {
                        this.nsxtDataService.changeSharedClusterName(
                            input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceClusterName']);
                    }
                    if (input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceSize')) {
                        this.nsxtDataService.changeSharedDeploymentSize(
                            input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceSize']);
                    }
                    if(input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceCpuSize')) {
                        this.nsxtDataService.changeSharedCpu(
                            input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceCpuSize']);
                    }
                    if(input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceMemorySize')) {
                        this.nsxtDataService.changeSharedMemory(
                            input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceMemorySize']);
                    }
                    if(input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceStorageSize')) {
                        this.nsxtDataService.changeSharedStorage(
                            input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceStorageSize']);
                    }
                    if (input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceDeploymentType')) {
                        this.nsxtDataService.changeSharedDeploymentType(
                            input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceDeploymentType']);
                    }
                    if (input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceWorkerMachineCount')) {
                        this.nsxtDataService.changeSharedWorkerNodeCount(
                            input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceWorkerMachineCount']);
                    }
                    if (input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceClusterCidr')) {
                        if (input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceClusterCidr'] !== '') {
                            this.nsxtDataService.changeSharedClusterCidr(
                                input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceClusterCidr']);
                        }
                    }
                    if (input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceServiceCidr')) {
                        if (input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceServiceCidr'] !== '') {
                            this.nsxtDataService.changeSharedServiceCidr(
                                input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceServiceCidr']);
                        }
                    }
                    if (input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceBaseOs')) {
                        this.nsxtDataService.changeSharedBaseImage(
                            input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceBaseOs']);
                    }
                    if (input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceKubeVersion')) {
                        this.nsxtDataService.changeSharedBaseImageVersion(
                            input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceKubeVersion']);
                    }
                    if (this.apiClient.enableIdentityManagement) {
                        if (input['tkgComponentSpec'].hasOwnProperty('tkgSharedserviceRbacUserRoleSpec')) {
                            if (input['tkgComponentSpec']['tkgSharedserviceRbacUserRoleSpec'].hasOwnProperty('clusterAdminUsers')) {
                                this.nsxtDataService.changeSharedClusterAdminUsers(
                                    input['tkgComponentSpec']['tkgSharedserviceRbacUserRoleSpec']['clusterAdminUsers']);
                            }
                            if (input['tkgComponentSpec']['tkgSharedserviceRbacUserRoleSpec'].hasOwnProperty('adminUsers')) {
                                this.nsxtDataService.changeSharedAdminUsers(
                                    input['tkgComponentSpec']['tkgSharedserviceRbacUserRoleSpec']['adminUsers']);
                            }
                            if (input['tkgComponentSpec']['tkgSharedserviceRbacUserRoleSpec'].hasOwnProperty('editUsers')) {
                                this.nsxtDataService.changeSharedEditUsers(
                                    input['tkgComponentSpec']['tkgSharedserviceRbacUserRoleSpec']['editUsers']);
                            }
                            if (input['tkgComponentSpec']['tkgSharedserviceRbacUserRoleSpec'].hasOwnProperty('viewUsers')) {
                                this.nsxtDataService.changeSharedViewUsers(
                                    input['tkgComponentSpec']['tkgSharedserviceRbacUserRoleSpec']['viewUsers']);
                            }
                        }
                    }
                    if (input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceClusterGroupName')) {
                        this.nsxtDataService.changeSharedClusterGroupName(
                            input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceClusterGroupName']);
                    }
                    if (input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedserviceEnableDataProtection')) {
                        if (input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceEnableDataProtection'] === 'true' && this.apiClient.tmcEnabled) {
                            this.nsxtDataService.changeSharedEnableDataProtection(true);
                            this.apiClient.sharedDataProtectonEnabled = true;
                            if (input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedClusterCredential')) {
                                this.nsxtDataService.changeSharedDataProtectionCreds(
                                    input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedClusterCredential']);
                            }
                            if (input['tkgComponentSpec']['tkgSharedserviceSpec'].hasOwnProperty('tkgSharedClusterBackupLocation')) {
                                this.nsxtDataService.changeSharedDataProtectionTargetLocation(
                                    input['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedClusterBackupLocation']);
                            }
                        } else{
                            this.apiClient.sharedDataProtectonEnabled = false;
                            this.nsxtDataService.changeSharedEnableDataProtection(false);
                        }
                    } else {
                        this.apiClient.sharedDataProtectonEnabled = false;
                        this.nsxtDataService.changeSharedEnableDataProtection(false);
                    }
                }
            }
            if (input.hasOwnProperty('tkgMgmtDataNetwork')) {
                if (input['tkgMgmtDataNetwork'].hasOwnProperty('tkgMgmtDataNetworkGatewayCidr')) {
                    this.nsxtDataService.changeTkgMgmtDataGateway(
                        input['tkgMgmtDataNetwork']['tkgMgmtDataNetworkGatewayCidr']);
                }
                if (input['tkgMgmtDataNetwork'].hasOwnProperty('tkgMgmtDataNetworkName')) {
                    this.nsxtDataService.changeTkgMgmtDataSegment(
                        input['tkgMgmtDataNetwork']['tkgMgmtDataNetworkName']);
                }
                if (input['tkgMgmtDataNetwork'].hasOwnProperty('tkgMgmtAviServiceIpStartRange')) {
                    this.nsxtDataService.changeTkgMgmtDataDhcpStart(
                        input['tkgMgmtDataNetwork']['tkgMgmtAviServiceIpStartRange']);
                }
                if (input['tkgMgmtDataNetwork'].hasOwnProperty('tkgMgmtAviServiceIpEndRange')) {
                    this.nsxtDataService.changeTkgMgmtDataDhcpEnd(
                        input['tkgMgmtDataNetwork']['tkgMgmtAviServiceIpEndRange']);
                }
            }
            if (input.hasOwnProperty('tkgWorkloadDataNetwork')) {
                if (input['tkgWorkloadDataNetwork'].hasOwnProperty('tkgWorkloadDataNetworkName')) {
                    this.nsxtDataService.changeTkgWrkDataSegment(
                        input['tkgWorkloadDataNetwork']['tkgWorkloadDataNetworkName']);
                }
                if (input['tkgWorkloadDataNetwork'].hasOwnProperty('tkgWorkloadDataNetworkGatewayCidr')) {
                    this.nsxtDataService.changeTkgWrkDataGateway(
                        input['tkgWorkloadDataNetwork']['tkgWorkloadDataNetworkGatewayCidr']);
                }
                if (input['tkgWorkloadDataNetwork'].hasOwnProperty('tkgWorkloadAviServiceIpStartRange')) {
                    this.nsxtDataService.changeTkgWrkDataDhcpStart(
                        input['tkgWorkloadDataNetwork']['tkgWorkloadAviServiceIpStartRange']);
                }
                if (input['tkgWorkloadDataNetwork'].hasOwnProperty('tkgWorkloadAviServiceIpEndRange')) {
                    this.nsxtDataService.changeTkgWrkDataDhcpEnd(
                        input['tkgWorkloadDataNetwork']['tkgWorkloadAviServiceIpEndRange']);
                }
            }
            if (input.hasOwnProperty('tkgWorkloadComponents')) {
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadNetworkName')) {
                    this.nsxtDataService.changeWrkSegment(
                        input['tkgWorkloadComponents']['tkgWorkloadNetworkName']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadGatewayCidr')) {
                    this.nsxtDataService.changeWrkGateway(
                        input['tkgWorkloadComponents']['tkgWorkloadGatewayCidr']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadDhcpStartRange')) {
                    this.nsxtDataService.changeWrkDhcpStart(
                        input['tkgWorkloadComponents']['tkgWorkloadDhcpStartRange']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadDhcpEndRange')) {
                    this.nsxtDataService.changeWrkDhcpEnd(
                        input['tkgWorkloadComponents']['tkgWorkloadDhcpEndRange']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadClusterName')) {
                    this.nsxtDataService.changeWrkClusterName(
                        input['tkgWorkloadComponents']['tkgWorkloadClusterName']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadSize')) {
                    this.nsxtDataService.changeWrkDeploymentSize(
                        input['tkgWorkloadComponents']['tkgWorkloadSize']);
                }
                if(input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadCpuSize')) {
                    this.nsxtDataService.changeWrkCpu(
                        input['tkgWorkloadComponents']['tkgWorkloadCpuSize']);
                }
                if(input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadMemorySize')) {
                    this.nsxtDataService.changeWrkMemory(
                        input['tkgWorkloadComponents']['tkgWorkloadMemorySize']);
                }
                if(input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadStorageSize')) {
                    this.nsxtDataService.changeWrkStorage(
                        input['tkgWorkloadComponents']['tkgWorkloadStorageSize']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadDeploymentType')) {
                    this.nsxtDataService.changeWrkDeploymentType(
                        input['tkgWorkloadComponents']['tkgWorkloadDeploymentType']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadWorkerMachineCount')) {
                    this.nsxtDataService.changeWrkWorkerNodeCount(
                        input['tkgWorkloadComponents']['tkgWorkloadWorkerMachineCount']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadClusterCidr')) {
                    if (input['tkgWorkloadComponents']['tkgWorkloadClusterCidr'] !== '') {
                        this.nsxtDataService.changeWrkClusterCidr(
                            input['tkgWorkloadComponents']['tkgWorkloadClusterCidr']);
                    }
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadServiceCidr')) {
                    if (input['tkgWorkloadComponents']['tkgWorkloadServiceCidr'] !== '') {
                        this.nsxtDataService.changeWrkServiceCidr(
                            input['tkgWorkloadComponents']['tkgWorkloadServiceCidr']);
                    }
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadBaseOs')) {
                    this.nsxtDataService.changeWrkBaseImage(
                        input['tkgWorkloadComponents']['tkgWorkloadBaseOs']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadKubeVersion')) {
                    this.nsxtDataService.changeWrkBaseImageVersion(
                        input['tkgWorkloadComponents']['tkgWorkloadKubeVersion']);
                }
                if (this.apiClient.enableIdentityManagement) {
                    if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadRbacUserRoleSpec')) {
                        if (input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec'].hasOwnProperty('clusterAdminUsers')) {
                            this.nsxtDataService.changeWrkClusterAdminUsers(
                                input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec']['clusterAdminUsers']);
                        }
                        if (input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec'].hasOwnProperty('adminUsers')) {
                            this.nsxtDataService.changeWrkAdminUsers(
                                input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec']['adminUsers']);
                        }
                        if (input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec'].hasOwnProperty('editUsers')) {
                            this.nsxtDataService.changeWrkEditUsers(
                                input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec']['editUsers']);
                        }
                        if (input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec'].hasOwnProperty('viewUsers')) {
                            this.nsxtDataService.changeWrkViewUsers(
                                input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec']['viewUsers']);
                        }
                    }
                }
                let tmcEnabled;
                this.nsxtDataService.currentEnableTMC.subscribe(enableTmc => tmcEnabled = enableTmc);
                if (tmcEnabled) {
                    if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadTsmIntegration')) {
                        if (input['tkgWorkloadComponents']['tkgWorkloadTsmIntegration'] === 'true') {
                            this.nsxtDataService.changeEnableTSM(true);
                            if (input['tkgWorkloadComponents'].hasOwnProperty('namespaceExclusions')) {
                                if (input['tkgWorkloadComponents']['namespaceExclusions'].hasOwnProperty('exactName')) {
                                    this.nsxtDataService.changeTsmExactNamespaceExclusion(input['tkgWorkloadComponents']['namespaceExclusions']['exactName']);
                                }
                                if (input['tkgWorkloadComponents']['namespaceExclusions'].hasOwnProperty('startsWith')) {
                                    this.nsxtDataService.changeTsmStartsWithNamespaceExclusion(input['tkgWorkloadComponents']['namespaceExclusions']['startsWith']);
                                }
                            }
                        } else {
                            this.nsxtDataService.changeEnableTSM(false);
                        }
                    }
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadClusterGroupName')) {
                    this.nsxtDataService.changeWrkClusterGroupName(input['tkgWorkloadComponents']['tkgWorkloadClusterGroupName']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadEnableDataProtection')) {
                    if(input['tkgWorkloadComponents']['tkgWorkloadEnableDataProtection'] === 'true' && this.apiClient.tmcEnabled) {
                        this.nsxtDataService.changeWrkEnableDataProtection(true);
                        this.apiClient.wrkDataProtectionEnabled = true;
                        if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadClusterCredential')) {
                            this.nsxtDataService.changeWrkDataProtectionCreds(
                                input['tkgWorkloadComponents']['tkgWorkloadClusterCredential']);
                        }
                        if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadClusterBackupLocation')) {
                            this.nsxtDataService.changeWrkDataProtectionTargetLocation(
                                input['tkgWorkloadComponents']['tkgWorkloadClusterBackupLocation']);
                        }
                    } else {
                        this.nsxtDataService.changeWrkEnableDataProtection(false);
                        this.apiClient.wrkDataProtectionEnabled = false;
                    }
                } else {
                    this.nsxtDataService.changeWrkEnableDataProtection(false);
                    this.apiClient.wrkDataProtectionEnabled = false;
                }
            }
            if (input.hasOwnProperty('harborSpec')) {
                this.nsxtDataService.changeEnableHarbor(true);
                if (input['harborSpec'].hasOwnProperty('harborFqdn')) {
                    this.nsxtDataService.changeHarborFqdn(
                        input['harborSpec']['harborFqdn']);
                }
                if (input['harborSpec'].hasOwnProperty('harborPasswordBase64')) {
                    this.nsxtDataService.changeHarborPassword(
                        atob(input['harborSpec']['harborPasswordBase64']));
                }
                if (input['harborSpec'].hasOwnProperty('harborCertPath')) {
                    this.nsxtDataService.changeHarborCertPath(
                        input['harborSpec']['harborCertPath']);
                }
                if (input['harborSpec'].hasOwnProperty('harborCertKeyPath')) {
                    this.nsxtDataService.changeHarborCertKey(
                        input['harborSpec']['harborCertKeyPath']);
                }
            }
            if (input.hasOwnProperty('tanzuExtensions')) {
                if (input['tanzuExtensions'].hasOwnProperty('enableExtensions')) {
                    if(input['tanzuExtensions']['enableExtensions'] === 'true') {
                        this.nsxtDataService.changeEnableTanzuExtension(true);
                        if (input['tanzuExtensions'].hasOwnProperty('tkgClustersName')) {
                            this.nsxtDataService.changeTkgClusters(input['tanzuExtensions']['tkgClustersName']);
                            this.processNsxtEnableLogging(input);
                            this.processNsxtEnableMonitoring(input);
                        }
                    } else {
                        this.nsxtDataService.changeEnableTanzuExtension(false);
                        this.nsxtDataService.changeEnableLoggingExtension(false);
                        this.nsxtDataService.changeEnableMonitoringExtension(false);
                    }
                } else {
                    this.nsxtDataService.changeEnableTanzuExtension(false);
                    this.nsxtDataService.changeEnableLoggingExtension(false);
                    this.nsxtDataService.changeEnableMonitoringExtension(false);
                }
            }
        }
    }

    public navigateToWizardWithoutUpload(): void {
        this.loading = true;
        this.noupload = true;
        this.inputFile = null;
        this.readFile = false;
        this.attachment.nativeElement.value = '';
        this.fileUploaded = false;
        this.fileName = '';
        this.file = null;
        this.nsxtDataService.changeInputFileStatus(false);
        FormMetaDataStore.deleteAllSavedData();
        this.clusterType = 'management';
        this.router.navigate([APP_ROUTES.VSPHERE_NSXT_WIZARD]);
    }

    /**
     * @method navigateToWizard
     * @desc helper method to trigger router navigation to wizard
     * @param provider - the provider to load wizard for
     */
    public navigateToWizard(providerType: string): void {
        this.loading = true;
        this.showLoginLoader = true;
        this.clusterType = 'management';
        this.setParamsFromInputJSON(this.inputFile);
        FormMetaDataStore.deleteAllSavedData();
        let wizard;
        switch (providerType) {
            case PROVIDERS.VSPHERE: {
                wizard = APP_ROUTES.WIZARD_MGMT_CLUSTER;
                break;
            }
            case PROVIDERS.VMC: {
                wizard = APP_ROUTES.VMC_WIZARD;
                break;
            }
            case PROVIDERS.AZURE: {
                wizard = APP_ROUTES.AZURE_WIZARD;
                break;
            }
            case PROVIDERS.DOCKER: {
                wizard = APP_ROUTES.DOCKER_WIZARD;
                break;
            }
            case PROVIDERS.VSPHERE_NSXT: {
                wizard = APP_ROUTES.VSPHERE_NSXT_WIZARD;
                break;
            }
        }
        this.router.navigate([wizard]);
    }

    public openFormPanel() {
        // this.readInputFile();
        // this.setFormInput();
//         this.displayWizard = true;
        // this.show = true;
    }

    public uploadFile(event) {
        if (!event || !event.target || !event.target.files || event.target.files.length === 0) {
            this.fileUploaded = false;
            this.noupload = true;
            return;
        }
        this.noupload = false;
        this.file = event.target.files[0];
        let file = this.file
        const name = this.file.name;
        const lastDot = name.lastIndexOf('.');

        this.fileName = name.substring(0, lastDot);
        this.fileUploaded = true;
        const ext = name.substring(lastDot + 1);
        this.fileName = this.fileName + '.' + ext;

        let self = this;
        if (this.fileName !== '' && this.fileUploaded) {
            const reader = new FileReader();
            // tslint:disable-next-line:only-arrow-functions
            reader.readAsText(file, 'UTF-8');
            reader.onload = async function(evt) {
                if (typeof evt.target.result === 'string') {
                    self.inputFile = await (JSON.parse(evt.target.result));
                    if (await self.inputFile !== null) {
                        self.readFile = true;
                    }
                    await console.log(' ');
                }
            };
            // tslint:disable-next-line:only-arrow-functions
            reader.onerror = function(evt) {
                console.log('Error Reading Input File');
                self.inputFile = null;
            };
        } else {
        }
    }

    public removeFile() {
        if (this.fileName) {
            this.noupload = true;
            this.inputFile = null;
            this.readFile = false;
            this.attachment.nativeElement.value = '';
            this.fileUploaded = false;
            this.fileName = '';
            this.file = null;
        }
    }
}
