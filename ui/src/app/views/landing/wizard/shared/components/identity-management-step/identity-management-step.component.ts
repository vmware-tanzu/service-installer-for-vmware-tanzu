// import { LdapParams } from './../../../../../../../swagger/models/ldap-params.model';
import { Component, OnInit } from '@angular/core';
import { FormControl, Validators } from '@angular/forms';
import { distinctUntilChanged, takeUntil, tap } from 'rxjs/operators';
// import { APIClient } from 'src/app/swagger';
import { StepFormDirective } from 'src/app/views/landing/wizard/shared/step-form/step-form';
import { ValidationService } from '../../../shared/validation/validation.service';
import {APIClient} from 'src/app/swagger/api-client.service';
// import { LdapTestResult } from 'src/app/swagger/models';
import { DataService } from 'src/app/shared/service/data.service';
import { VMCDataService } from 'src/app/shared/service/vmc-data.service';
import { VsphereNsxtDataService } from 'src/app/shared/service/vsphere-nsxt-data.service';
import { AppDataService } from 'src/app/shared/service/app-data.service';

const CONNECT = "CONNECT";
const BIND = "BIND";
const USER_SEARCH = "USER_SEARCH";
const GROUP_SEARCH = "GROUP_SEARCH";
const DISCONNECT = "DISCONNECT";

const TEST_SUCCESS = 1;
const TEST_SKIPPED = 2;

const LDAP_TESTS = [CONNECT, BIND, USER_SEARCH, GROUP_SEARCH, DISCONNECT];

const NOT_STARTED = "not-started";
const CURRENT = "current";
const SUCCESS = "success";
const ERROR = "error";
const PROCESSING = "processing";

const oidcFields: Array<string> = [
    'issuerURL',
    'clientId',
    'clientSecret',
    'scopes',
    'oidcUsernameClaim',
    'oidcGroupsClaim'
];

const ldapValidatedFields: Array<string> = [
    'endpointIp',
    'endpointPort',
    'bindPW',
    'userSearchBaseDN',
    'groupSearchBaseDN'
];

const ldapNonValidatedFields: Array<string> = [
    'bindDN',
    'userSearchFilter',
    'userSearchUsername',
    'groupSearchFilter',
    'groupSearchUserAttr',
    'groupSearchGroupAttr',
    'groupSearchNameAttr',
    'ldapRootCAData',
    'testUserName',
    'testGroupName'
];

const LDAP_PARAMS = {
    ldap_bind_dn: "bindDN",
    ldap_bind_password: "bindPW",
    ldap_group_search_base_dn: "groupSearchBaseDN",
    ldap_group_search_filter: "groupSearchFilter",
    ldap_group_search_group_attr: "groupSearchGroupAttr",
    ldap_group_search_name_attr: "groupSearchNameAttr",
    ldap_group_search_user_attr: "groupSearchUserAttr",
    ldap_root_ca: "ldapRootCAData",
    ldap_user_search_base_dn: "userSearchBaseDN",
    ldap_user_search_filter: "userSearchFilter",
    ldap_user_search_name_attr: "userSearchUsername",
    ldap_user_search_username: "userSearchUsername",
    ldap_test_group: "testGroupName",
    ldap_test_user: "testUserName"
}

@Component({
    selector: 'app-shared-identity-step',
    templateUrl: './identity-management-step.component.html',
    styleUrls: ['./identity-management-step.component.scss']
})
export class SharedIdentityStepComponent extends StepFormDirective implements OnInit {
    identityTypeValue: string = 'oidc'
    _verifyLdapConfig = false;

    fields: Array<string> = [...oidcFields, ...ldapValidatedFields, ...ldapNonValidatedFields];

    timelineState = {};
    timelineError = {};

    providerType: string;
    public dataObj;

    // UPLOAD FIELDS
    private uploadStatus = false;
    private enableIdm = false;
    private idmType;
    // OIDC UPLOAD
    private issuerURL;
    private clientId;
    private clientSecret;
    private scopes;
    private oidcUsernameClaim;
    private oidcGroupsClaim;
    // LDAP UPLOAD
    private ldapEndpointIp;
    private ldapEndpointPort;
    private ldapBindPW;
    private ldapBindDN;
    private ldapUserSearchBaseDN;
    private ldapUserSearchFilter;
    private ldapUserSearchUsername;
    private ldapGroupSearchBaseDN;
    private ldapGroupSearchFilter;
    private ldapGroupSearchUserAttr;
    private ldapGroupSearchGroupAttr;
    private ldapGroupSearchNameAttr;
    private ldapRootCAData;
    private ldapTestUserName;
    private ldapTestGroupName;
    //private apiClient: APIClient
    constructor(private validationService: ValidationService,
                private apiClient: APIClient,
                private appDataService: AppDataService,
                private dataService: DataService,
                private vmcDataService: VMCDataService,
                private nsxtDataService: VsphereNsxtDataService) {
        super();
        this.resetTimelineState();
        this.appDataService.getProviderType().asObservable().subscribe((data) => this.providerType = data);
    }

    ngOnInit(): void {
        super.ngOnInit();
        if (this.providerType === 'vsphere') {
            this.dataObj = this.dataService;
        } else if (this.providerType === 'vmc') {
            this.dataObj = this.vmcDataService;
        } else if (this.providerType === 'vsphere-nsxt') {
            this.dataObj = this.nsxtDataService;
        }

        this.formGroup.addControl('identityType', new FormControl('oidc', []));
        this.formGroup.addControl('idmSettings', new FormControl(false, []));

        this.fields.forEach(field => this.formGroup.addControl(field, new FormControl('', [])));

        this.formGroup.get('identityType').valueChanges.pipe(
            distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr)),
            takeUntil(this.unsubscribe)
        ).subscribe(data => {
            this.identityTypeValue = data;
            this.unsetAllValidators();
            if (this.identityTypeValue === 'oidc') {
                this.setOIDCValidators();
                this.formGroup.get('clientSecret').setValue('');
            } else if (this.identityTypeValue === 'ldap') {
                this.setLDAPValidators();
            } else {
                this.disarmField('identityType', true);
            }
        });
        this.identityTypeValue = this.getSavedValue('identityType', 'oidc');
        this.formGroup.get('identityType').setValue(this.identityTypeValue);
        setTimeout(_ => {
            this.dataObj.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if(this.uploadStatus) {
                this.dataObj.currentEnableIdentityManagement.subscribe(
                    (enable) => this.enableIdm = enable);
                this.formGroup.get('idmSettings').setValue(this.enableIdm);
                this.apiClient.enableIdentityManagement = this.enableIdm;
                if (this.enableIdm) {
                    this.dataObj.currentIdentityManagementType.subscribe(
                        (type) => this.idmType = type);
                    this.formGroup.get('identityType').setValue(this.idmType);
                    if (this.idmType === 'oidc') {
                        this.dataObj.currentOidcIssuerUrl.subscribe(
                            (url) => this.issuerURL = url);
                        this.formGroup.get('issuerURL').setValue(this.issuerURL);
                        this.dataObj.currentOidcClientId.subscribe(
                            (clientId) => this.clientId = clientId);
                        this.formGroup.get('clientId').setValue(this.clientId);
                        this.dataObj.currentOidcClientSecret.subscribe(
                            (clientSecret) => this.clientSecret = clientSecret);
                        this.formGroup.get('clientSecret').setValue(this.clientSecret);
                        this.dataObj.currentOidcScopes.subscribe(
                            (scopes) => this.scopes = scopes);
                        this.formGroup.get('scopes').setValue(this.scopes);
                        this.dataObj.currentOidcUsernameClaim.subscribe(
                            (usernameClaim) => this.oidcUsernameClaim = usernameClaim);
                        this.formGroup.get('oidcUsernameClaim').setValue(this.oidcUsernameClaim);
                        this.dataObj.currentOidcGroupsClaim.subscribe(
                            (groupClaim) => this.oidcGroupsClaim = groupClaim);
                        this.formGroup.get('oidcGroupsClaim').setValue(this.oidcGroupsClaim);
                    } else if (this.idmType === 'ldap') {
                        this.dataObj.currentLdapEndpointIp.subscribe(
                            (ip) => this.ldapEndpointIp = ip);
                        this.formGroup.get('endpointIp').setValue(this.ldapEndpointIp);
                        this.dataObj.currentLdapEndpointPort.subscribe(
                            (port) =>  this.ldapEndpointPort = port);
                        this.formGroup.get('endpointPort').setValue(this.ldapEndpointPort);

                        this.dataObj.currentLdapBindPW.subscribe(
                            (pass) => this.ldapBindPW = pass);
                        this.formGroup.get('bindPW').setValue(this.ldapBindPW);

                        this.dataObj.currentLdapBindDN.subscribe(
                            (bindDN) => this.ldapBindDN = bindDN);
                        this.formGroup.get('bindDN').setValue(this.ldapBindDN);

                        this.dataObj.currentLdapUserSearchBaseDN.subscribe(
                            (baseDn) => this.ldapUserSearchBaseDN = baseDn);
                        this.formGroup.get('userSearchBaseDN').setValue(this.ldapUserSearchBaseDN);

                        this.dataObj.currentLdapUserSearchFilter.subscribe(
                            (filter) => this.ldapUserSearchFilter = filter);
                        this.formGroup.get('userSearchFilter').setValue(this.ldapUserSearchFilter);

                        this.dataObj.currentLdapUserSearchUsername.subscribe(
                            (uname) => this.ldapUserSearchUsername = uname);
                        this.formGroup.get('userSearchUsername').setValue(this.ldapUserSearchUsername);

                        this.dataObj.currentLdapGroupSearchBaseDN.subscribe(
                            (baseDn) => this.ldapGroupSearchBaseDN = baseDn);
                        this.formGroup.get('groupSearchBaseDN').setValue(this.ldapGroupSearchBaseDN);

                        this.dataObj.currentLdapGroupSearchFilter.subscribe(
                            (filter) => this.ldapGroupSearchFilter = filter);
                        this.formGroup.get('groupSearchFilter').setValue(this.ldapGroupSearchFilter);

                        this.dataObj.currentLdapGroupSearchUserAttr.subscribe(
                            (attr) => this.ldapGroupSearchUserAttr = attr);
                        this.formGroup.get('groupSearchUserAttr').setValue(this.ldapGroupSearchUserAttr);

                        this.dataObj.currentLdapGroupSearchGroupAttr.subscribe(
                            (attr) => this.ldapGroupSearchGroupAttr = attr);
                        this.formGroup.get('groupSearchGroupAttr').setValue(this.ldapGroupSearchGroupAttr);

                        this.dataObj.currentLdapGroupSearchNameAttr.subscribe(
                            (attr) => this.ldapGroupSearchNameAttr = attr);
                        this.formGroup.get('groupSearchNameAttr').setValue(this.ldapGroupSearchNameAttr);

                        this.dataObj.currentLdapRootCAData.subscribe(
                            (rootCa) => this.ldapRootCAData = rootCa);
                        this.formGroup.get('ldapRootCAData').setValue(this.ldapRootCAData);

                        this.dataObj.currentLdapTestUserName.subscribe(
                            (uname) => this.ldapTestUserName = uname);
                        this.formGroup.get('testUserName').setValue(this.ldapTestUserName);

                        this.dataObj.currentLdapTestGroupName.subscribe(
                            (grpName) => this.ldapTestGroupName = grpName);
                        this.formGroup.get('testGroupName').setValue(this.ldapTestGroupName);
                    }
                }
            }
        });
    }

    setOIDCValidators() {
        this.resurrectField('issuerURL', [
            Validators.required,
            this.validationService.noWhitespaceOnEnds(),
            this.validationService.isValidIpOrFqdnWithHttpsProtocol(),
            this.validationService.isStringWithoutUrlFragment(),
            this.validationService.isStringWithoutQueryParams(),
        ], this.getSavedValue('issuerURL', ''));

        this.resurrectField('clientId', [
            Validators.required,
            this.validationService.noWhitespaceOnEnds()
        ], this.getSavedValue('clientId', ''));

        this.resurrectField('clientSecret', [
            Validators.required,
            this.validationService.noWhitespaceOnEnds()
        ], '');

        this.resurrectField('scopes', [
            Validators.required,
            this.validationService.noWhitespaceOnEnds(),
            this.validationService.isCommaSeperatedList()
        ], this.getSavedValue('scopes', ''));

        this.resurrectField('oidcUsernameClaim', [
            Validators.required
        ], this.getSavedValue('oidcUsernameClaim', ''));

        this.resurrectField('oidcGroupsClaim', [
            Validators.required
        ], this.getSavedValue('oidcGroupsClaim', ''));
    }

    setLDAPValidators() {
        this.resurrectField('endpointIp', [
            Validators.required
        ], this.getSavedValue('endpointIp', ''));

        this.resurrectField('endpointPort', [
            Validators.required,
            this.validationService.noWhitespaceOnEnds(),
            this.validationService.isValidLdap(this.formGroup.get('endpointIp'))
        ], this.getSavedValue('endpointPort', ''));

        this.resurrectField('bindPW', [], '');

        this.resurrectField('userSearchBaseDN', [
            Validators.required,
            this.validationService.noWhitespaceOnEnds()
        ], this.getSavedValue('userSearchBaseDN', ''));
        this.resurrectField('groupSearchBaseDN', [
            Validators.required,
            this.validationService.noWhitespaceOnEnds()
        ], this.getSavedValue('groupSearchBaseDN', ''));

        ldapNonValidatedFields.forEach(field => this.resurrectField(
            field, [], this.getSavedValue(field, '')));
    }

    unsetAllValidators() {
        this.fields.forEach(field => this.disarmField(field, true));
    }

    toggleIdmSetting() {
        if (this.formGroup.value['idmSettings']) {
            this.apiClient.enableIdentityManagement = true;
            this.formGroup.controls['identityType'].setValue('oidc');
        } else {
            this.apiClient.enableIdentityManagement = false;
            this.formGroup.controls['identityType'].setValue('none');
        }
    }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
        this.formGroup.get('clientSecret').setValue('');
        if (!this.formGroup.value['idmSettings']) {
            this.formGroup.get('identityType').setValue('none');
        }
    }

    /**
     * @method ldapEndpointInputValidity return true if ldap endpoint inputs are valid
     */
    ldapEndpointInputValidity(): boolean {
        return this.formGroup.get('endpointIp').valid &&
            this.formGroup.get('endpointPort').valid;
    }

    resetTimelineState() {
        LDAP_TESTS.forEach(t => {
            this.timelineState[t] = NOT_STARTED;
            this.timelineError[t] = null;
        })
    }

//     cropLdapConfig(): LdapParams {
//         const ldapParams: LdapParams = {};
//
//         Object.entries(LDAP_PARAMS).forEach(([k, v]) => {
//             if (this.formGroup.get(v)) {
//                 ldapParams[k] = this.formGroup.get(v).value || "";
//             } else {
//                 console.log("Unable to find field: " + v);
//             }
//         });
//         ldapParams.ldap_url = "ldaps://" + this.formGroup.get('endpointIp').value + ':' + this.formGroup.get('endpointPort').value;
//
//         return ldapParams;
//     }

    formatError(err) {
        if (err) {
            return err?.error?.message || err?.message || JSON.stringify(err, null, 4);
        }
        return "";
    }

    async startVerifyLdapConfig() {
        this.resetTimelineState();
        try {
            this.timelineState[CONNECT] = PROCESSING;
            let ldapConnectData = {
                'ldapEndpointIp': this.formGroup.get('endpointIp').value,
                'ldapEndpointPort': this.formGroup.get('endpointPort').value,
                'ldapRootCAData': this.formGroup.get('ldapRootCAData').value,
            };
            await this.apiClient.verifyLdapConnect(ldapConnectData, this.providerType).subscribe((data: any) => {
                if (data && data !== null) {
                    if (data.responseType === 'SUCCESS') {
                        this.timelineState[CONNECT] = SUCCESS;
                    } else if (data.responseType === 'ERROR') {
                        this.timelineState[CONNECT] = ERROR;
                        this.timelineError[CONNECT] = data.msg;
                    }
                } else {
                    this.timelineState[CONNECT] = ERROR;
                    this.timelineError[CONNECT] = "Failed to connect to LDAP server";
                }
            }, (error: any) => {
                if (error.responseType === 'ERROR') {
                    this.timelineState[CONNECT] = ERROR;
                    this.timelineError[CONNECT] = error.msg;
                } else {
                    this.timelineState[CONNECT] = ERROR;
                    this.timelineError[CONNECT] = "Failed to connect to LDAP server";
                }
            });
        } catch (err) {
            console.log(JSON.stringify(err, null, 8));
            this.timelineState[CONNECT] = ERROR;
            this.timelineError[CONNECT] = this.formatError(err);
        }

        try {
            this.timelineState[BIND] = PROCESSING;
            let ldapBindData = {
                'ldapEndpointIp': this.formGroup.get('endpointIp').value,
                'ldapEndpointPort': this.formGroup.get('endpointPort').value,
                'ldapRootCAData': this.formGroup.get('ldapRootCAData').value,
                'ldapBindDN': this.formGroup.get('bindDN').value,
                'ldapBindPW': this.formGroup.get('bindPW').value,
            };
            await this.apiClient.verifyLdapBind(ldapBindData, this.providerType).subscribe((data: any) => {
                if (data && data !== null) {
                    if (data.responseType === 'SUCCESS') {
                        this.timelineState[BIND] = SUCCESS;
                    } else if (data.responseType === 'ERROR') {
                        this.timelineState[BIND] = ERROR;
                        this.timelineError[BIND] = data.msg;
                    }
                } else {
                    this.timelineState[BIND] = ERROR;
                    this.timelineError[BIND] = "Failed to bind to LDAP server";
                }
            }, (error: any) => {
                if (error.responseType === 'ERROR') {
                    this.timelineState[BIND] = ERROR;
                    this.timelineError[BIND] = error.msg;
                } else {
                    this.timelineState[BIND] = ERROR;
                    this.timelineError[BIND] = "Failed to bind to LDAP server";
                }
            });
        } catch (err) {
            console.log(JSON.stringify(err, null, 8));
            this.timelineState[BIND] = ERROR;
            this.timelineError[BIND] = this.formatError(err);
        }

        try {
            this.timelineState[USER_SEARCH] = PROCESSING;
            let ldapUserSearchData = {
                'ldapEndpointIp': this.formGroup.get('endpointIp').value,
                'ldapEndpointPort': this.formGroup.get('endpointPort').value,
                'ldapRootCAData': this.formGroup.get('ldapRootCAData').value,
                'ldapBindDN': this.formGroup.get('bindDN').value,
                'ldapBindPW': this.formGroup.get('bindPW').value,
                'ldapUserSearchBaseDN': this.formGroup.get('userSearchBaseDN').value,
                'ldapUserSearchFilter': this.formGroup.get('userSearchFilter').value,
                'ldapUserSearchUsername': this.formGroup.get('userSearchUsername').value,
                'ldapTestUserName': this.formGroup.get('testUserName').value,
            };
            await this.apiClient.verifyLdapUserSearch(ldapUserSearchData, this.providerType).subscribe((data: any) => {
                if (data && data !== null) {
                    if (data.responseType === 'SUCCESS') {
                        this.timelineState[USER_SEARCH] = SUCCESS;
                    } else if (data.responseType === 'ERROR') {
                        this.timelineState[USER_SEARCH] = ERROR;
                        this.timelineError[USER_SEARCH] = data.msg;
                    }
                } else {
                    this.timelineState[USER_SEARCH] = ERROR;
                    this.timelineError[USER_SEARCH] = "Failed to perform user search on LDAP server";
                }
            }, (error: any) => {
                if (error.responseType === 'ERROR') {
                    this.timelineState[USER_SEARCH] = ERROR;
                    this.timelineError[USER_SEARCH] = error.msg;
                } else {
                    this.timelineState[USER_SEARCH] = ERROR;
                    this.timelineError[USER_SEARCH] = "Failed to perform user search on LDAP server";
                }
            });
        } catch (err) {
            console.log(JSON.stringify(err, null, 8));
            this.timelineState[USER_SEARCH] = ERROR;
            this.timelineError[USER_SEARCH] = this.formatError(err);
        }

        try {
            this.timelineState[GROUP_SEARCH] = PROCESSING;
            let ldapGroupSearchData = {
                'ldapEndpointIp': this.formGroup.get('endpointIp').value,
                'ldapEndpointPort': this.formGroup.get('endpointPort').value,
                'ldapRootCAData': this.formGroup.get('ldapRootCAData').value,
                'ldapBindDN': this.formGroup.get('bindDN').value,
                'ldapBindPW': this.formGroup.get('bindPW').value,
                'ldapGroupSearchBaseDN': this.formGroup.get('groupSearchBaseDN').value,
                'ldapGroupSearchFilter': this.formGroup.get('groupSearchFilter').value,
                'ldapGroupSearchUserAttr': this.formGroup.get('groupSearchUserAttr').value,
                'ldapGroupSearchGroupAttr': this.formGroup.get('groupSearchGroupAttr').value,
                'ldapGroupSearchNameAttr': this.formGroup.get('groupSearchNameAttr').value,
                'ldapTestGroupName': this.formGroup.get('testUserName').value,
            };
            await this.apiClient.verifyLdapGroupSearch(ldapGroupSearchData, this.providerType).subscribe((data: any) => {
                if (data && data !== null) {
                    if (data.responseType === 'SUCCESS') {
                        this.timelineState[GROUP_SEARCH] = SUCCESS;
                    } else if (data.responseType === 'ERROR') {
                        this.timelineState[GROUP_SEARCH] = ERROR;
                        this.timelineError[GROUP_SEARCH] = data.msg;
                    }
                } else {
                    this.timelineState[GROUP_SEARCH] = ERROR;
                    this.timelineError[GROUP_SEARCH] = "Failed to perform group search on LDAP server";
                }
            }, (error: any) => {
                if (error.responseType === 'ERROR') {
                    this.timelineState[GROUP_SEARCH] = ERROR;
                    this.timelineError[GROUP_SEARCH] = error.msg;
                } else {
                    this.timelineState[GROUP_SEARCH] = ERROR;
                    this.timelineError[GROUP_SEARCH] = "Failed to perform group search on LDAP server";
                }
            });
        } catch (err) {
            console.log(JSON.stringify(err, null, 8));
            this.timelineState[GROUP_SEARCH] = ERROR;
            this.timelineError[GROUP_SEARCH] = this.formatError(err);
        }

        try {
            this.timelineState[DISCONNECT] = PROCESSING;
            await setTimeout(() => {
                this.timelineState[DISCONNECT] = SUCCESS;
            }, 100);
            // let ldapDisconnectData = {};
            // this.apiClient.verifyLdapCloseConnection(ldapDisconnectData, this.providerType).subscribe((data: any) => {
            //     if (data && data !== null) {
            //         if (data.responseType === 'SUCCESS') {
            //             this.timelineState[DISCONNECT] = SUCCESS;
            //         } else if (data.responseType === 'ERROR') {
            //             this.timelineState[DISCONNECT] = ERROR;
            //             this.timelineError[DISCONNECT] = data.msg;
            //         }
            //     } else {
            //         this.timelineState[DISCONNECT] = ERROR;
            //         this.timelineError[DISCONNECT] = "Failed to disconnect LDAP server";
            //     }
            // }, (error: any) => {
            //     if (error.responseType === 'ERROR') {
            //         this.timelineState[DISCONNECT] = ERROR;
            //         this.timelineError[DISCONNECT] = error.msg;
            //     } else {
            //         this.timelineState[DISCONNECT] = ERROR;
            //         this.timelineError[DISCONNECT] = "Failed to disconnect LDAP server";
            //     }
            // });
        } catch (err) {
            console.log(JSON.stringify(err, null, 8));
            this.timelineState[DISCONNECT] = ERROR;
            this.timelineError[DISCONNECT] = this.formatError(err);
        }
    }

    get verifyLdapConfig(): boolean {
        return this._verifyLdapConfig;
    }

    set verifyLdapConfig(vlc: boolean) {
        this._verifyLdapConfig = vlc;
        this.resetTimelineState();
    }
}
