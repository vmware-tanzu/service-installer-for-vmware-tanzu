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
    selector: 'app-vmc-upload',
    templateUrl: './vmc-upload-wizard.component.html',
    styleUrls: ['./vmc-upload-wizard.component.scss'],
})
export class VMCUploadWizardComponent implements OnInit {

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

    ) {
//         super(router, el, formMetaDataService, titleService);
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

    public processVmcEnableMonitoring(input) {
        if (input['tanzuExtensions'].hasOwnProperty('monitoring')) {
            if (input['tanzuExtensions']['monitoring'].hasOwnProperty('enableLoggingExtension')) {
                if (input['tanzuExtensions']['monitoring']['enableLoggingExtension'] === 'true') {
                    this.vmcDataService.changeEnableMonitoringExtension(true);
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('prometheusFqdn')) {
                        this.vmcDataService.changePrometheusFqdn(input['tanzuExtensions']['monitoring']['prometheusFqdn']);
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('prometheusCertPath')) {
                        this.vmcDataService.changePrometheusCertPath(input['tanzuExtensions']['monitoring']['prometheusCertPath']);
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('prometheusCertKeyPath')) {
                        this.vmcDataService.changePrometheusCertkeyPath(input['tanzuExtensions']['monitoring']['prometheusCertKeyPath']);
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('grafanaFqdn')) {
                        this.vmcDataService.changeGrafanaFqdn(input['tanzuExtensions']['monitoring']['grafanaFqdn']);
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('grafanaPasswordBase64')) {
                        this.vmcDataService.changeGrafanaPassword(atob(input['tanzuExtensions']['monitoring']['grafanaPasswordBase64']));
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('grafanaCertPath')) {
                        this.vmcDataService.changeGrafanaCertPath(input['tanzuExtensions']['monitoring']['grafanaCertPath']);
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('grafanaCertKeyPath')) {}
                        this.vmcDataService.changeGrafanaCertKeyPath(input['tanzuExtensions']['monitoring']['grafanaCertKeyPath']);
                } else {
                    this.vmcDataService.changeEnableMonitoringExtension(false);
                }
            }
        }
    }

    public processVmcEnableLogging(input) {
        if (input['tanzuExtensions'].hasOwnProperty('logging')) {
            if (input['tanzuExtensions']['logging'].hasOwnProperty('syslogEndpoint') &&
                input['tanzuExtensions']['logging'].hasOwnProperty('httpEndpoint') &&
                input['tanzuExtensions']['logging'].hasOwnProperty('kafkaEndpoint')) {
                if (input['tanzuExtensions']['logging']['syslogEndpoint'].hasOwnProperty('enableSyslogEndpoint') &&
                    input['tanzuExtensions']['logging']['httpEndpoint'].hasOwnProperty('enableHttpEndpoint') &&
                    input['tanzuExtensions']['logging']['kafkaEndpoint'].hasOwnProperty('enableKafkaEndpoint')) {
                    if (input['tanzuExtensions']['logging']['syslogEndpoint']['enableSyslogEndpoint'] === 'true') {
                        this.vmcDataService.changeEnableLoggingExtension(true);
                        this.vmcDataService.changeLoggingEndpoint('Syslog');
                        if (input['tanzuExtensions']['logging']['syslogEndpoint'].hasOwnProperty('syslogEndpointAddress')) {
                            this.vmcDataService.changeSyslogAddress(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointAddress']);
                        }
                        if (input['tanzuExtensions']['logging']['syslogEndpoint'].hasOwnProperty('syslogEndpointPort')) {
                            this.vmcDataService.changeSyslogPort(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointPort']);
                        }
                        if (input['tanzuExtensions']['logging']['syslogEndpoint'].hasOwnProperty('syslogEndpointMode')) {
                            this.vmcDataService.changeSyslogMode(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointMode']);
                        }
                        if (input['tanzuExtensions']['logging']['syslogEndpoint'].hasOwnProperty('syslogEndpointFormat')) {
                            this.vmcDataService.changeSyslogFormat(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointFormat']);
                        }
                    } else if(input['tanzuExtensions']['logging']['httpEndpoint']['enableHttpEndpoint'] === 'true') {
                        this.vmcDataService.changeEnableLoggingExtension(true);
                        this.vmcDataService.changeLoggingEndpoint('HTTP');
                        if (input['tanzuExtensions']['logging']['httpEndpoint'].hasOwnProperty('httpEndpointAddress')) {
                            this.vmcDataService.changeHttpAddress(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointAddress']);
                        }
                        if (input['tanzuExtensions']['logging']['httpEndpoint'].hasOwnProperty('httpEndpointPort')) {
                            this.vmcDataService.changeHttpPort(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointPort']);
                        }
                        if (input['tanzuExtensions']['logging']['httpEndpoint'].hasOwnProperty('httpEndpointUri')) {
                            this.vmcDataService.changeHttpUri(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointUri']);
                        }
                        if (input['tanzuExtensions']['logging']['httpEndpoint'].hasOwnProperty('httpEndpointHeaderKeyValue')) {
                            this.vmcDataService.changeHttpHeaderKey(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointHeaderKeyValue']);
                        }
                    // } else if(input['tanzuExtensions']['logging']['elasticSearchEndpoint']['enableElasticSearchEndpoint'] === 'true') {
                    //     this.vmcDataService.changeEnableLoggingExtension(true);
                    //     this.vmcDataService.changeLoggingEndpoint('Elastic Search');
                    //     if (input['tanzuExtensions']['logging']['elasticSearchEndpoint'].hasOwnProperty('elasticSearchEndpointAddress')) {
                    //         this.vmcDataService.changeElasticSearchAddress(input['tanzuExtensions']['logging']['elasticSearchEndpoint']['elasticSearchEndpointAddress']);
                    //     }
                    //     if (input['tanzuExtensions']['logging']['elasticSearchEndpoint'].hasOwnProperty('elasticSearchEndpointPort')) {
                    //         this.vmcDataService.changeElasticSearchPort(input['tanzuExtensions']['logging']['elasticSearchEndpoint']['elasticSearchEndpointPort']);
                    //     }
                    } else if(input['tanzuExtensions']['logging']['kafkaEndpoint']['enableKafkaEndpoint'] === 'true') {
                        this.vmcDataService.changeEnableLoggingExtension(true);
                        this.vmcDataService.changeLoggingEndpoint('Kafka');
                        if (input['tanzuExtensions']['logging']['kafkaEndpoint'].hasOwnProperty('kafkaBrokerServiceName')) {
                            this.vmcDataService.changeKafkaServiceName(input['tanzuExtensions']['logging']['kafkaEndpoint']['kafkaBrokerServiceName']);
                        }
                        if (input['tanzuExtensions']['logging']['kafkaEndpoint'].hasOwnProperty('kafkaTopicName')) {
                            this.vmcDataService.changeKafkaTopicName(input['tanzuExtensions']['logging']['kafkaEndpoint']['kafkaTopicName']);
                        }
                    // } else if(input['tanzuExtensions']['logging']['splunkEndpoint']['enableSplunkEndpoint'] === 'true') {
                    //     this.vmcDataService.changeEnableLoggingExtension(true);
                    //     this.vmcDataService.changeLoggingEndpoint('Splunk');
                    //     if (input['tanzuExtensions']['logging']['splunkEndpoint'].hasOwnProperty('splunkEndpointAddress')) {
                    //         this.vmcDataService.changeSplunkAddress(input['tanzuExtensions']['logging']['splunkEndpoint']['splunkEndpointAddress']);
                    //     }
                    //     if (input['tanzuExtensions']['logging']['splunkEndpoint'].hasOwnProperty('splunkEndpointPort')) {
                    //         this.vmcDataService.changeSplunkPort(input['tanzuExtensions']['logging']['splunkEndpoint']['splunkEndpointPort']);
                    //     }
                    //     if (input['tanzuExtensions']['logging']['splunkEndpoint'].hasOwnProperty('splunkEndpointToken')) {
                    //         this.vmcDataService.changeSplunkToken(input['tanzuExtensions']['logging']['splunkEndpoint']['splunkEndpointToken']);
                    //     }
                    } else {
                        this.vmcDataService.changeEnableLoggingExtension(false);
                    }
                }
            }
        }
    }

    public setVmcParamsFromInputJSON(input) {
        if (input) {
            this.vmcDataService.changeInputFileStatus(true);
            if (input.hasOwnProperty('envVariablesSpec')) {
                if (input['envVariablesSpec'].hasOwnProperty('dnsServersIp')) {
                    const dns = input['envVariablesSpec']['dnsServersIp'];
                    this.vmcDataService.changeDnsServer(dns);
                }
                if (input['envVariablesSpec'].hasOwnProperty('ntpServersIp')) {
                    const ntp = input['envVariablesSpec']['ntpServersIp'];
                    this.vmcDataService.changeNtpServer(ntp);
                }
                if (input['envVariablesSpec'].hasOwnProperty('searchDomains')) {
                    const searchDomain = input['envVariablesSpec']['searchDomains'];
                    this.vmcDataService.changeSearchDomain(searchDomain);
                }
            }
            if (input.hasOwnProperty('envSpec')) {
                if (input['envSpec'].hasOwnProperty('sddcRefreshToken')) {
                    this.vmcDataService.changeSddcToken(input['envSpec']['sddcRefreshToken']);
                }
                if (input['envSpec'].hasOwnProperty('orgName')) {
                    this.vmcDataService.changeOrgName(input['envSpec']['orgName']);
                }
                if (input['envSpec'].hasOwnProperty('sddcName')) {
                    this.vmcDataService.changeSddcName(input['envSpec']['sddcName']);
                }
                if (input['envSpec'].hasOwnProperty('sddcDatacenter')) {
                    this.vmcDataService.changeDatacenter(input['envSpec']['sddcDatacenter']);
                }
                if (input['envSpec'].hasOwnProperty('sddcCluster')) {
                    this.vmcDataService.changeCluster(input['envSpec']['sddcCluster']);
                }
                if (input['envSpec'].hasOwnProperty('sddcDatastore')) {
                    this.vmcDataService.changeDatastore(input['envSpec']['sddcDatastore']);
                }
                if (input['envSpec'].hasOwnProperty('resourcePoolName')) {
                    this.vmcDataService.changeResourcePool(input['envSpec']['resourcePoolName']);
                }
                if (input['envSpec'].hasOwnProperty('contentLibraryName')) {
                    if (input['envSpec']['contentLibraryName'] !== '') {
                        this.vmcDataService.changeIsCustomerConnect(false);
                    }
                    this.vmcDataService.changeContentLib(input['envSpec']['contentLibraryName']);
                }
                if (input['envSpec'].hasOwnProperty('aviOvaName')) {
                    if (input['envSpec']['aviOvaName'] !== '') {
                        this.vmcDataService.changeIsCustomerConnect(false);
                    }
                    this.vmcDataService.changeOvaImage(input['envSpec']['aviOvaName']);
                }
            }
            // if (input.hasOwnProperty('resource-spec')) {
            //     if (input['resource-spec'].hasOwnProperty('customer-connect-user')) {
            //         if (input['envSpec']['aviOvaName'] === '' && input['envSpec']['contentLibraryName'] === '') {
            //             if (input['resource-spec']['customer-connect-user'] !== '') {
            //                 this.vmcDataService.changeIsCustomerConnect(true);
            //             }
            //         }
            //         this.vmcDataService.changeCustUsername(
            //             input['resource-spec']['customer-connect-user']);
            //     }
            //     if (input['resource-spec'].hasOwnProperty('customer-connect-password-base64')) {
            //         this.vmcDataService.changeCustPassword(
            //             atob(input['resource-spec']['customer-connect-password-base64']));
            //     }
            //     if (input['resource-spec'].hasOwnProperty('avi-pulse-jwt-token')) {
            //         this.vmcDataService.changeJwtToken(
            //             input['resource-spec']['avi-pulse-jwt-token']);
            //     }
            //     if (input['resource-spec'].hasOwnProperty('kubernetes-ova')) {
            //         this.vmcDataService.changeKubernetesOva(
            //             input['resource-spec']['kubernetes-ova']);
            //     }
            // }
            if (input.hasOwnProperty('marketplaceSpec')) {
                if (input['marketplaceSpec'].hasOwnProperty('refreshToken')) {
                    if (input['envSpec']['aviOvaName'] === '' && input['envSpec']['contentLibraryName'] === '') {
                        if (input['marketplaceSpec']['refreshToken'] !== '') {
                            this.vmcDataService.changeIsMarketplace(true);
                        }
                    }
                    this.vmcDataService.changeMarketplaceRefreshToken(
                        input['marketplaceSpec']['refreshToken']);
                }
            }
            if(input.hasOwnProperty('ceipParticiaption')) {
                if(input['ceipParticiaption'] === 'true') {
                    this.vmcDataService.changeCeipParticipation(true);
                } else {
                    this.vmcDataService.changeCeipParticipation(false);
                }
            }else {
                this.vmcDataService.changeCeipParticipation(false);
            }
            if (input.hasOwnProperty('saasEndpoints')) {
                if (input['saasEndpoints'].hasOwnProperty('tmcDetails')) {
                    if (input['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcAvailability')) {
                        if (input['saasEndpoints']['tmcDetails']['tmcAvailability'] === 'true') {
                            this.apiClient.tmcEnabled = true;
                            this.vmcDataService.changeEnableTMC(true);
                            if (input['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcRefreshToken')) {
                                this.vmcDataService.changeApiToken(
                                    input['saasEndpoints']['tmcDetails']['tmcRefreshToken']);
                            }
                            if (input['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcInstanceURL')) {
                                this.vmcDataService.changeInstanceUrl(
                                    input['saasEndpoints']['tmcDetails']['tmcInstanceURL']);
                            }

                            if (input['saasEndpoints'].hasOwnProperty('tanzuObservabilityDetails')) {
                                if (input['saasEndpoints']['tanzuObservabilityDetails'].hasOwnProperty('tanzuObservabilityAvailability')) {
                                    if (input['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityAvailability'] === 'true') {
                                        this.apiClient.toEnabled = true;
                                        this.vmcDataService.changeEnableTO(true);
                                        if (input['saasEndpoints']['tanzuObservabilityDetails'].hasOwnProperty('tanzuObservabilityUrl')) {
                                            this.vmcDataService.changeTOUrl(
                                                input['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityUrl']);
                                        }
                                        if (input['saasEndpoints']['tanzuObservabilityDetails'].hasOwnProperty('tanzuObservabilityRefreshToken')) {
                                            this.vmcDataService.changeTOApiToken(
                                                input['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityRefreshToken']);
                                        }
                                    } else {
                                        this.apiClient.toEnabled = false;
                                        this.vmcDataService.changeEnableTO(false);
                                    }
                                }
                            }
                        } else {
                            this.apiClient.tmcEnabled = false;
                            this.vmcDataService.changeEnableTMC(false);
                            this.apiClient.toEnabled = false;
                            this.vmcDataService.changeEnableTO(false);
                            this.vmcDataService.changeEnableTSM(false);
                        }
                    } else {
                        this.apiClient.tmcEnabled = false;
                        this.vmcDataService.changeEnableTMC(false);
                        this.apiClient.toEnabled = false;
                        this.vmcDataService.changeEnableTO(false);
                        this.vmcDataService.changeEnableTSM(false);
                    }
                } else {
                    this.apiClient.tmcEnabled = false;
                    this.vmcDataService.changeEnableTMC(false);
                    this.apiClient.toEnabled = false;
                    this.vmcDataService.changeEnableTO(false);
                    this.vmcDataService.changeEnableTSM(false);
                }
            }
            if (input.hasOwnProperty('componentSpec')) {
                if (input['componentSpec'].hasOwnProperty('aviComponentSpec')) {
                    if (input['componentSpec']['aviComponentSpec'].hasOwnProperty('aviPasswordBase64')) {
                        this.vmcDataService.changeAviPassword(atob(input['componentSpec']['aviComponentSpec']['aviPasswordBase64']));
                    }
                    if (input['componentSpec']['aviComponentSpec'].hasOwnProperty('aviBackupPassPhraseBase64')) {
                        this.vmcDataService.changeAviBackupPassword(atob(input['componentSpec']['aviComponentSpec']['aviBackupPassPhraseBase64']));
                    }
                    if (input['componentSpec']['aviComponentSpec'].hasOwnProperty('enableAviHa')) {
                        if(input['componentSpec']['aviComponentSpec']['enableAviHa'] === 'true') {
                            this.vmcDataService.changeEnableAviHA(true);
                            if (input['componentSpec']['aviComponentSpec'].hasOwnProperty('aviClusterIp')) {
                                this.vmcDataService.changeAviClusterIp(
                                    input['componentSpec']['aviComponentSpec']['aviClusterIp']);
                            }
                            if (input['componentSpec']['aviComponentSpec'].hasOwnProperty('aviClusterFqdn')) {
                                this.vmcDataService.changeAviClusterFqdn(
                                    input['componentSpec']['aviComponentSpec']['aviClusterFqdn']);
                            }
                        } else {
                            this.vmcDataService.changeEnableAviHA(false);
                        }
                    }
                    if (input['componentSpec']['aviComponentSpec'].hasOwnProperty('aviSize')) {
                        this.vmcDataService.changeAviSize(input['componentSpec']['aviComponentSpec']['aviSize']);
                    }
                    if (input['componentSpec']['aviComponentSpec'].hasOwnProperty('aviCertPath')) {
                        this.vmcDataService.changeAviCertPath(input['componentSpec']['aviComponentSpec']['aviCertPath']);
                    }
                    if (input['componentSpec']['aviComponentSpec'].hasOwnProperty('aviCertKeyPath')) {
                        this.vmcDataService.changeAviCertKeyPath(input['componentSpec']['aviComponentSpec']['aviCertKeyPath']);
                    }
//                     if (input['componentSpec']['aviComponentSpec'].hasOwnProperty('aviLicenseKey')) {
//                         this.vmcDataService.changeAviLicenseKey(input['componentSpec']['aviComponentSpec']['aviLicenseKey']);
//                     }
                }
                if (input['componentSpec'].hasOwnProperty('aviMgmtNetworkSpec')) {
                    if (input['componentSpec']['aviMgmtNetworkSpec'].hasOwnProperty('aviMgmtGatewayCidr')) {
                        this.vmcDataService.changeAviGateway(input['componentSpec']['aviMgmtNetworkSpec']['aviMgmtGatewayCidr']);
                    }
                    if (input['componentSpec']['aviMgmtNetworkSpec'].hasOwnProperty('aviMgmtDhcpStartRange')) {
                        this.vmcDataService.changeAviDhcpStart(input['componentSpec']['aviMgmtNetworkSpec']['aviMgmtDhcpStartRange']);
                    }
                    if (input['componentSpec']['aviMgmtNetworkSpec'].hasOwnProperty('aviMgmtDhcpEndRange')) {
                        this.vmcDataService.changeAviDhcpEnd(input['componentSpec']['aviMgmtNetworkSpec']['aviMgmtDhcpEndRange']);
                    }
                }
                if (input['componentSpec'].hasOwnProperty('tkgClusterVipNetwork')) {
                    if (input['componentSpec']['tkgClusterVipNetwork'].hasOwnProperty('tkgClusterVipNetworkName')) {
                        this.vmcDataService.changeAviClusterVipNetworkName(input['componentSpec']['tkgClusterVipNetwork']['tkgClusterVipNetworkName']);
                    }
                    if (input['componentSpec']['tkgClusterVipNetwork'].hasOwnProperty('tkgClusterVipNetworkGatewayCidr')) {
                        this.vmcDataService.changeAviClusterVipGatewayIp(input['componentSpec']['tkgClusterVipNetwork']['tkgClusterVipNetworkGatewayCidr']);
                    }
                    if (input['componentSpec']['tkgClusterVipNetwork'].hasOwnProperty('tkgClusterVipDhcpStartRange')) {
                        this.vmcDataService.changeAviClusterVipStartIp(input['componentSpec']['tkgClusterVipNetwork']['tkgClusterVipDhcpStartRange']);
                    }
                    if (input['componentSpec']['tkgClusterVipNetwork'].hasOwnProperty('tkgClusterVipDhcpEndRange')) {
                        this.vmcDataService.changeAviClusterVipEndIp(input['componentSpec']['tkgClusterVipNetwork']['tkgClusterVipDhcpEndRange']);
                    }
                    if (input['componentSpec']['tkgClusterVipNetwork'].hasOwnProperty('tkgClusterVipIpStartRange')) {
                        this.vmcDataService.changeAviClusterVipSeStartIp(input['componentSpec']['tkgClusterVipNetwork']['tkgClusterVipIpStartRange']);
                    }
                    if (input['componentSpec']['tkgClusterVipNetwork'].hasOwnProperty('tkgClusterVipIpEndRange')) {
                        this.vmcDataService.changeAviClusterVipSeEndIp(input['componentSpec']['tkgClusterVipNetwork']['tkgClusterVipIpEndRange']);
                    }
                }
                if(input['componentSpec'].hasOwnProperty('identityManagementSpec')){
                    if (input['componentSpec']['identityManagementSpec'].hasOwnProperty('identityManagementType')){
                        if (input['componentSpec']['identityManagementSpec']['identityManagementType'] === 'oidc'){
                            this.vmcDataService.changeIdentityManagementType('oidc');
                            this.vmcDataService.changeEnableIdentityManagement(true);
                            this.apiClient.enableIdentityManagement = true;
                            if (input['componentSpec']['identityManagementSpec'].hasOwnProperty('oidcSpec')) {
                                if (input['componentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcIssuerUrl')) {
                                    this.vmcDataService.changeOidcIssuerUrl(
                                        input['componentSpec']['identityManagementSpec']['oidcSpec']['oidcIssuerUrl']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcClientId')) {
                                    this.vmcDataService.changeOidcClientId(
                                        input['componentSpec']['identityManagementSpec']['oidcSpec']['oidcClientId']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcClientSecret')) {
                                    this.vmcDataService.changeOidcClientSecret(
                                        input['componentSpec']['identityManagementSpec']['oidcSpec']['oidcClientSecret']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcScopes')) {
                                    this.vmcDataService.changeOidcScopes(
                                        input['componentSpec']['identityManagementSpec']['oidcSpec']['oidcScopes']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcUsernameClaim')) {
                                    this.vmcDataService.changeOidcUsernameClaim(
                                        input['componentSpec']['identityManagementSpec']['oidcSpec']['oidcUsernameClaim']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcGroupsClaim')) {
                                    this.vmcDataService.changeOidcGroupClaim(
                                        input['componentSpec']['identityManagementSpec']['oidcSpec']['oidcGroupsClaim']);
                                }
                            }
                        } else if (input['componentSpec']['identityManagementSpec']['identityManagementType'] === 'ldap') {
                            this.vmcDataService.changeIdentityManagementType('ldap');
                            this.vmcDataService.changeEnableIdentityManagement(true);
                            this.apiClient.enableIdentityManagement = true;
                            if (input['componentSpec']['identityManagementSpec'].hasOwnProperty('ldapSpec')) {
                                if (input['componentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapEndpointIp')) {
                                    this.vmcDataService.changeLdapEndpointIp(
                                        input['componentSpec']['identityManagementSpec']['ldapSpec']['ldapEndpointIp']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapEndpointPort')) {
                                    this.vmcDataService.changeLdapEndpointPort(
                                        input['componentSpec']['identityManagementSpec']['ldapSpec']['ldapEndpointPort']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapBindPWBase64')) {
                                    this.vmcDataService.changeLdapBindPw(
                                        atob(input['componentSpec']['identityManagementSpec']['ldapSpec']['ldapBindPWBase64']));
                                }
                                if (input['componentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapBindDN')) {
                                    this.vmcDataService.changeLdapBindDN(
                                        input['componentSpec']['identityManagementSpec']['ldapSpec']['ldapBindDN']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapUserSearchBaseDN')) {
                                    this.vmcDataService.changeLdapUserSearchBaseDN(
                                        input['componentSpec']['identityManagementSpec']['ldapSpec']['ldapUserSearchBaseDN']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapUserSearchFilter')) {
                                    this.vmcDataService.changeLdapUserSearchFilter(
                                        input['componentSpec']['identityManagementSpec']['ldapSpec']['ldapUserSearchFilter']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapUserSearchUsername')) {
                                    this.vmcDataService.changeLdapUserSearchUsername(
                                        input['componentSpec']['identityManagementSpec']['ldapSpec']['ldapUserSearchUsername']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapGroupSearchBaseDN')) {
                                    this.vmcDataService.changeLdapGroupSearchBaseDN(
                                        input['componentSpec']['identityManagementSpec']['ldapSpec']['ldapGroupSearchBaseDN']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapGroupSearchFilter')) {
                                    this.vmcDataService.changeLdapGroupSearchFilter(
                                        input['componentSpec']['identityManagementSpec']['ldapSpec']['ldapGroupSearchFilter']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapGroupSearchUserAttr')) {
                                    this.vmcDataService.changeLdapGroupSearchUserAttr(
                                        input['componentSpec']['identityManagementSpec']['ldapSpec']['ldapGroupSearchUserAttr']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapGroupSearchGroupAttr')) {
                                    this.vmcDataService.changeLdapGroupSearchGroupAttr(
                                        input['componentSpec']['identityManagementSpec']['ldapSpec']['ldapGroupSearchGroupAttr']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapGroupSearchNameAttr')) {
                                    this.vmcDataService.changeLdapGroupSearchNameAttr(
                                        input['componentSpec']['identityManagementSpec']['ldapSpec']['ldapGroupSearchNameAttr']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapRootCAData')) {
                                    this.vmcDataService.changeLdapRootCAData(
                                        input['componentSpec']['identityManagementSpec']['ldapSpec']['ldapRootCAData']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapTestUserName')) {
                                    this.vmcDataService.changeLdapTestUserName(
                                        input['componentSpec']['identityManagementSpec']['ldapSpec']['ldapTestUserName']);
                                }
                                if (input['componentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapTestGroupName')) {
                                    this.vmcDataService.changeLdapTestGroupName(
                                        input['componentSpec']['identityManagementSpec']['ldapSpec']['ldapTestGroupName']);
                                }
                            }
                        }
                        else {
                            this.vmcDataService.changeEnableIdentityManagement(false);
                            this.apiClient.enableIdentityManagement = false;
                        }
                    } else {
                        this.vmcDataService.changeEnableIdentityManagement(false);
                        this.apiClient.enableIdentityManagement = false;
                    }
                } else {
                    this.vmcDataService.changeEnableIdentityManagement(false);
                    this.apiClient.enableIdentityManagement = false;
                }
                if (input['componentSpec'].hasOwnProperty('tkgMgmtDataNetworkSpec')) {
                    if (input['componentSpec']['tkgMgmtDataNetworkSpec'].hasOwnProperty('tkgMgmtDataGatewayCidr')) {
                        this.vmcDataService.changeTkgMgmtDataGateway(input['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataGatewayCidr']);
                    }
                    if (input['componentSpec']['tkgMgmtDataNetworkSpec'].hasOwnProperty('tkgMgmtDataDhcpStartRange')) {
                        this.vmcDataService.changeTkgMgmtDataDhcpStart(input['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataDhcpStartRange']);
                    }
                    if (input['componentSpec']['tkgMgmtDataNetworkSpec'].hasOwnProperty('tkgMgmtDataDhcpEndRange')) {
                        this.vmcDataService.changeTkgMgmtDataDhcpEnd(input['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataDhcpEndRange']);
                    }
                    if (input['componentSpec']['tkgMgmtDataNetworkSpec'].hasOwnProperty('tkgMgmtDataServiceStartRange')) {
                        this.vmcDataService.changeTkgMgmtDataServiceStart(input['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataServiceStartRange']);
                    }
                    if (input['componentSpec']['tkgMgmtDataNetworkSpec'].hasOwnProperty('tkgMgmtDataServiceEndRange')) {
                        this.vmcDataService.changeTkgMgmtDataServiceEnd(input['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataServiceEndRange']);
                    }
                }
                if (input['componentSpec'].hasOwnProperty('tkgMgmtSpec')) {
                    if (input['componentSpec']['tkgMgmtSpec'].hasOwnProperty('tkgMgmtClusterName')) {
                        this.vmcDataService.changeMgmtClusterName(input['componentSpec']['tkgMgmtSpec']['tkgMgmtClusterName']);
                    }
                    if (input['componentSpec']['tkgMgmtSpec'].hasOwnProperty('tkgMgmtDeploymentType')) {
                        this.vmcDataService.changeMgmtDeploymentType(input['componentSpec']['tkgMgmtSpec']['tkgMgmtDeploymentType']);
                    }
                    if (input['componentSpec']['tkgMgmtSpec'].hasOwnProperty('tkgMgmtSize')) {
                        this.vmcDataService.changeMgmtDeploymentSize(input['componentSpec']['tkgMgmtSpec']['tkgMgmtSize']);
                    }
                    if(input['componentSpec']['tkgMgmtSpec'].hasOwnProperty('tkgMgmtCpuSize')){
                        this.vmcDataService.changeMgmtCpu(input['componentSpec']['tkgMgmtSpec']['tkgMgmtCpuSize']);
                    }
                    if(input['componentSpec']['tkgMgmtSpec'].hasOwnProperty('tkgMgmtMemorySize')){
                        this.vmcDataService.changeMgmtMemory(input['componentSpec']['tkgMgmtSpec']['tkgMgmtMemorySize']);
                    }
                    if(input['componentSpec']['tkgMgmtSpec'].hasOwnProperty('tkgMgmtStorageSize')){
                        this.vmcDataService.changeMgmtStorage(input['componentSpec']['tkgMgmtSpec']['tkgMgmtStorageSize']);
                    }
                    if (input['componentSpec']['tkgMgmtSpec'].hasOwnProperty('tkgMgmtNetworkName')) {
                        console.log(input['componentSpec']['tkgMgmtSpec']['tkgMgmtNetworkName']);
                        this.vmcDataService.changeMgmtSegment(input['componentSpec']['tkgMgmtSpec']['tkgMgmtNetworkName']);
                    }
                    if (input['componentSpec']['tkgMgmtSpec'].hasOwnProperty('tkgMgmtGatewayCidr')) {
                        this.vmcDataService.changeMgmtGateway(input['componentSpec']['tkgMgmtSpec']['tkgMgmtGatewayCidr']);
                    }
                    if (input['componentSpec']['tkgMgmtSpec'].hasOwnProperty('tkgMgmtClusterCidr')) {
                        if (input['componentSpec']['tkgMgmtSpec']['tkgMgmtClusterCidr'] !== '') {
                            this.vmcDataService.changeMgmtClusterCidr(
                                input['componentSpec']['tkgMgmtSpec']['tkgMgmtClusterCidr']);
                        }
                    }
                    if (input['componentSpec']['tkgMgmtSpec'].hasOwnProperty('tkgMgmtServiceCidr')) {
                        if (input['componentSpec']['tkgMgmtSpec']['tkgMgmtServiceCidr'] !== '') {
                            this.vmcDataService.changeMgmtServiceCidr(
                                input['componentSpec']['tkgMgmtSpec']['tkgMgmtServiceCidr']);
                        }
                    }
                    if (input['componentSpec']['tkgMgmtSpec'].hasOwnProperty('tkgMgmtBaseOs')) {
                        this.vmcDataService.changeMgmtBaseImage(
                            input['componentSpec']['tkgMgmtSpec']['tkgMgmtBaseOs']);
                    }
                    if (this.apiClient.enableIdentityManagement) {
                        if (input['componentSpec']['tkgMgmtSpec'].hasOwnProperty('tkgMgmtRbacUserRoleSpec')) {
                            if (input['componentSpec']['tkgMgmtSpec']['tkgMgmtRbacUserRoleSpec'].hasOwnProperty('clusterAdminUsers')) {
                                this.vmcDataService.changeMgmtClusterAdminUsers(
                                    input['componentSpec']['tkgMgmtSpec']['tkgMgmtRbacUserRoleSpec']['clusterAdminUsers']);
                            }
                            if (input['componentSpec']['tkgMgmtSpec']['tkgMgmtRbacUserRoleSpec'].hasOwnProperty('adminUsers')) {
                                this.vmcDataService.changeMgmtAdminUsers(
                                    input['componentSpec']['tkgMgmtSpec']['tkgMgmtRbacUserRoleSpec']['adminUsers']);
                            }
                            if (input['componentSpec']['tkgMgmtSpec']['tkgMgmtRbacUserRoleSpec'].hasOwnProperty('editUsers')) {
                                this.vmcDataService.changeMgmtEditUsers(
                                    input['componentSpec']['tkgMgmtSpec']['tkgMgmtRbacUserRoleSpec']['editUsers']);
                            }
                            if (input['componentSpec']['tkgMgmtSpec']['tkgMgmtRbacUserRoleSpec'].hasOwnProperty('viewUsers')) {
                                this.vmcDataService.changeMgmtViewUsers(
                                    input['componentSpec']['tkgMgmtSpec']['tkgMgmtRbacUserRoleSpec']['viewUsers']);
                            }
                        }
                    }
                    if (input['componentSpec']['tkgMgmtSpec'].hasOwnProperty('tkgMgmtClusterGroupName')) {
                        this.vmcDataService.changeMgmtClusterGroupName(input['componentSpec']['tkgMgmtSpec']['tkgMgmtClusterGroupName']);
                    }
                }
                if (input['componentSpec'].hasOwnProperty('tkgSharedServiceSpec')) {
                    if (input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedserviceDeploymentType')) {
                        if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceDeploymentType'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.vmcDataService.changeSharedDeploymentType(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceDeploymentType']);
                    }
                    if (input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedserviceSize')) {
                        if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceSize'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.vmcDataService.changeSharedDeploymentSize(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceSize']);
                    }
                    if(input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedserviceCpuSize')){
                        if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceCpuSize'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.vmcDataService.changeSharedCpu(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceCpuSize']);
                    }
                    if(input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedserviceMemorySize')){
                        if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceMemorySize'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.vmcDataService.changeSharedMemory(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceMemorySize']);
                    }
                    if(input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedserviceStorageSize')){
                        if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceStorageSize'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.vmcDataService.changeSharedStorage(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceStorageSize']);
                    }
                    if (input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedClusterName')) {
                        if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedClusterName'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.vmcDataService.changeSharedClusterName(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedClusterName']);
                    }
                    if (input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedserviceWorkerMachineCount')) {
                        if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceWorkerMachineCount'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.vmcDataService.changeSharedWorkerNodeCount(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceWorkerMachineCount']);
                    }
                    if (input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedGatewayCidr')) {
                        if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedGatewayCidr'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.vmcDataService.changeSharedGateway(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedGatewayCidr']);
                    }
                    if (input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedDhcpStartRange')) {
                        if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedDhcpStartRange'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.vmcDataService.changeSharedDhcpStart(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedDhcpStartRange']);
                    }
                    if (input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedDhcpEndRange')) {
                        if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedDhcpEndRange'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.vmcDataService.changeSharedDhcpEnd(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedDhcpEndRange']);
                    }
                    if (input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedserviceClusterCidr')) {
                        if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceClusterCidr'] !== '') {
                            this.vmcDataService.changeSharedClusterCidr(
                                input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceClusterCidr']);
                        }
                    }
                    if (input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedserviceServiceCidr')) {
                        if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceServiceCidr'] !== '') {
                            this.vmcDataService.changeSharedServiceCidr(
                                input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceServiceCidr']);
                        }
                    }
                    if (input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedserviceBaseOs')) {
                        if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceBaseOs'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.vmcDataService.changeSharedBaseImage(
                            input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceBaseOs']);
                    }
                    if (input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedserviceKubeVersion')) {
                        if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceKubeVersion'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.vmcDataService.changeSharedBaseImageVersion(
                            input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceKubeVersion']);
                    }
                    if (this.apiClient.enableIdentityManagement) {
                        if (input['componentSpec'].hasOwnProperty('tkgSharedserviceRbacUserRoleSpec')) {
                            if (input['componentSpec']['tkgSharedserviceRbacUserRoleSpec'].hasOwnProperty('clusterAdminUsers')) {
                                if (input['componentSpec']['tkgSharedserviceRbacUserRoleSpec']['clusterAdminUsers'] !== ""){
                                    this.apiClient.sharedServicesClusterSettings = true;
                                }
                                this.vmcDataService.changeSharedClusterAdminUsers(
                                    input['componentSpec']['tkgSharedserviceRbacUserRoleSpec']['clusterAdminUsers']);
                            }
                            if (input['componentSpec']['tkgSharedserviceRbacUserRoleSpec'].hasOwnProperty('adminUsers')) {
                                if (input['componentSpec']['tkgSharedserviceRbacUserRoleSpec']['adminUsers'] !== ""){
                                    this.apiClient.sharedServicesClusterSettings = true;
                                }
                                this.vmcDataService.changeSharedAdminUsers(
                                    input['componentSpec']['tkgSharedserviceRbacUserRoleSpec']['adminUsers']);
                            }
                            if (input['componentSpec']['tkgSharedserviceRbacUserRoleSpec'].hasOwnProperty('editUsers')) {
                                if (input['componentSpec']['tkgSharedserviceRbacUserRoleSpec']['editUsers'] !== ""){
                                    this.apiClient.sharedServicesClusterSettings = true;
                                }
                                this.vmcDataService.changeSharedEditUsers(
                                    input['componentSpec']['tkgSharedserviceRbacUserRoleSpec']['editUsers']);
                            }
                            if (input['componentSpec']['tkgSharedserviceRbacUserRoleSpec'].hasOwnProperty('viewUsers')) {
                                if (input['componentSpec']['tkgSharedserviceRbacUserRoleSpec']['viewUsers'] !== ""){
                                    this.apiClient.sharedServicesClusterSettings = true;
                                }
                                this.vmcDataService.changeSharedViewUsers(
                                    input['componentSpec']['tkgSharedserviceRbacUserRoleSpec']['viewUsers']);
                            }
                        }
                    }
                    if (input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedserviceEnableDataProtection')) {
                        if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceEnableDataProtection'] === 'true' && this.apiClient.tmcEnabled) {
                            this.vmcDataService.changeSharedEnableDataProtection(true);
                            this.apiClient.sharedDataProtectonEnabled = true;
                            if (input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedClusterCredential')) {
                                if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedClusterCredential'] !== ""){
                                    this.apiClient.sharedServicesClusterSettings = true;
                                }
                                this.vmcDataService.changeSharedDataProtectionCreds(
                                    input['componentSpec']['tkgSharedServiceSpec']['tkgSharedClusterCredential']);
                            }
                            if (input['componentSpec']['tkgSharedServiceSpec'].hasOwnProperty('tkgSharedClusterBackupLocation')) {
                                if (input['componentSpec']['tkgSharedServiceSpec']['tkgSharedClusterBackupLocation'] !== ""){
                                    this.apiClient.sharedServicesClusterSettings = true;
                                }
                                this.vmcDataService.changeSharedDataProtectionTargetLocation(
                                    input['componentSpec']['tkgSharedServiceSpec']['tkgSharedClusterBackupLocation']);
                            }
                        } else{
                            this.apiClient.sharedDataProtectonEnabled = false;
                            this.vmcDataService.changeSharedEnableDataProtection(false);
                        }
                    } else {
                        this.apiClient.sharedDataProtectonEnabled = false;
                        this.vmcDataService.changeSharedEnableDataProtection(false);
                    }
                }
                if (input['componentSpec'].hasOwnProperty('harborSpec')) {
                    this.vmcDataService.changeEnableHarbor(true);
                    if (input['componentSpec']['harborSpec'].hasOwnProperty('harborFqdn')) {
                        if (input['componentSpec']['harborSpec']['harborFqdn'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.vmcDataService.changeHarborFqdn(input['componentSpec']['harborSpec']['harborFqdn']);
                    }
                    if (input['componentSpec']['harborSpec'].hasOwnProperty('harborPasswordBase64')) {
                        if (input['componentSpec']['harborSpec']['harborPasswordBase64'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.vmcDataService.changeHarborPassword(atob(input['componentSpec']['harborSpec']['harborPasswordBase64']));
                    }
                    if (input['componentSpec']['harborSpec'].hasOwnProperty('harborCertPath')) {
                        if (input['componentSpec']['harborSpec']['harborCertPath'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.vmcDataService.changeHarborCertPath(input['componentSpec']['harborSpec']['harborCertPath']);
                    }
                    if (input['componentSpec']['harborSpec'].hasOwnProperty('harborCertKeyPath')) {
                        if (input['componentSpec']['harborSpec']['harborCertKeyPath'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.vmcDataService.changeHarborCertKey(input['componentSpec']['harborSpec']['harborCertKeyPath']);
                    }
                }
                if (input['componentSpec'].hasOwnProperty('tkgWorkloadDataNetworkSpec')) {
                    if (input['componentSpec']['tkgWorkloadDataNetworkSpec'].hasOwnProperty('tkgWorkloadDataGatewayCidr')) {
                        if (input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataGatewayCidr'] !== ""){
                            this.apiClient.workloadDataSettings = true;
                        }
                        this.vmcDataService.changeTkgWrkDataGateway(input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataGatewayCidr']);
                    }
                    if (input['componentSpec']['tkgWorkloadDataNetworkSpec'].hasOwnProperty('tkgWorkloadDataDhcpStartRange')) {
                        if (input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataDhcpStartRange'] !== ""){
                            this.apiClient.workloadDataSettings = true;
                        }
                        this.vmcDataService.changeTkgWrkDataDhcpStart(input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataDhcpStartRange']);
                    }
                    if (input['componentSpec']['tkgWorkloadDataNetworkSpec'].hasOwnProperty('tkgWorkloadDataDhcpEndRange')) {
                        if (input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataDhcpEndRange'] !== ""){
                            this.apiClient.workloadDataSettings = true;
                        }
                        this.vmcDataService.changeTkgWrkDataDhcpEnd(input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataDhcpEndRange']);
                    }
                    if (input['componentSpec']['tkgWorkloadDataNetworkSpec'].hasOwnProperty('tkgWorkloadDataServiceStartRange')) {
                        if (input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataServiceStartRange'] !== ""){
                            this.apiClient.workloadDataSettings = true;
                        }
                        this.vmcDataService.changeTkgWrkDataServiceStart(input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataServiceStartRange']);
                    }
                    if (input['componentSpec']['tkgWorkloadDataNetworkSpec'].hasOwnProperty('tkgWorkloadDataServiceEndRange')) {
                        if (input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataServiceEndRange'] !== ""){
                            this.apiClient.workloadDataSettings = true;
                        }
                        this.vmcDataService.changeTkgWrkDataServiceEnd(input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataServiceEndRange']);
                    }
                }
                if (input['componentSpec'].hasOwnProperty('tkgWorkloadSpec')) {
                    if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadDeploymentType')) {
                        if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadDeploymentType'] !== ""){
                            this.apiClient.workloadClusterSettings = true;
                        }
                        this.vmcDataService.changeWrkDeploymentType(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadDeploymentType']);
                    }
                    if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadSize')) {
                        if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadSize'] !== ""){
                            this.apiClient.workloadClusterSettings = true;
                        }
                        this.vmcDataService.changeWrkDeploymentSize(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadSize']);
                    }
                    if(input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadCpuSize')){
                        if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadCpuSize'] !== ""){
                            this.apiClient.workloadClusterSettings = true;
                        }
                        this.vmcDataService.changeWrkCpu(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadCpuSize']);
                    }
                    if(input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadMemorySize')){
                        if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadMemorySize'] !== ""){
                            this.apiClient.workloadClusterSettings = true;
                        }
                        this.vmcDataService.changeWrkMemory(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadMemorySize']);
                    }
                    if(input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadStorageSize')){
                        if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadStorageSize'] !== ""){
                            this.apiClient.workloadClusterSettings = true;
                        }
                        this.vmcDataService.changeWrkStorage(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadStorageSize']);
                    }
                    if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadWorkerMachineCount')) {
                        if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadWorkerMachineCount'] !== ""){
                            this.apiClient.workloadClusterSettings = true;
                        }
                        this.vmcDataService.changeWrkWorkerNodeCount(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadWorkerMachineCount']);
                    }
                    if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadClusterName')) {
                        if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterName'] !== ""){
                            this.apiClient.workloadClusterSettings = true;
                        }
                        this.vmcDataService.changeWrkClusterName(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterName']);
                    }
                    if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadGatewayCidr')) {
                        if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadGatewayCidr'] !== ""){
                            this.apiClient.workloadClusterSettings = true;
                        }
                        this.vmcDataService.changeWrkGateway(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadGatewayCidr']);
                    }
                    if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadDhcpStartRange')) {
                        if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadDhcpStartRange'] !== ""){
                            this.apiClient.workloadClusterSettings = true;
                        }
                        this.vmcDataService.changeWrkDhcpStart(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadDhcpStartRange']);
                    }
                    if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadDhcpEndRange')) {
                        if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadDhcpEndRange'] !== ""){
                            this.apiClient.workloadClusterSettings = true;
                        }
                        this.vmcDataService.changeWrkDhcpEnd(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadDhcpEndRange']);
                    }
                    if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadClusterCidr')) {
                        if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterCidr'] !== '') {
                            this.vmcDataService.changeWrkClusterCidr(
                                input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterCidr']);
                        }
                    }
                    if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadServiceCidr')) {
                        if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadServiceCidr'] !== '') {
                            this.vmcDataService.changeWrkServiceCidr(
                                input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadServiceCidr']);
                        }
                    }
                    if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadBaseOs')) {
                        if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadBaseOs'] !== ""){
                            this.apiClient.workloadClusterSettings = true;
                        }
                        this.vmcDataService.changeWrkBaseImage(
                            input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadBaseOs']);
                    }
                    if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadKubeVersion')) {
                        if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadKubeVersion'] !== ""){
                            this.apiClient.workloadClusterSettings = true;
                        }
                        this.vmcDataService.changeWrkBaseImageVersion(
                            input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadKubeVersion']);
                    }
                    if (this.apiClient.enableIdentityManagement) {
                        if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadRbacUserRoleSpec')) {
                            if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadRbacUserRoleSpec'].hasOwnProperty('clusterAdminUsers')) {
                                if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadRbacUserRoleSpec']['clusterAdminUsers'] !== ""){
                                    this.apiClient.workloadClusterSettings = true;
                                }
                                this.vmcDataService.changeWrkClusterAdminUsers(
                                    input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadRbacUserRoleSpec']['clusterAdminUsers']);
                            }
                            if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadRbacUserRoleSpec'].hasOwnProperty('adminUsers')) {
                                if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadRbacUserRoleSpec']['adminUsers'] !== ""){
                                    this.apiClient.workloadClusterSettings = true;
                                }
                                this.vmcDataService.changeWrkAdminUsers(
                                    input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadRbacUserRoleSpec']['adminUsers']);
                            }
                            if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadRbacUserRoleSpec'].hasOwnProperty('editUsers')) {
                                if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadRbacUserRoleSpec']['editUsers'] !== ""){
                                    this.apiClient.workloadClusterSettings = true;
                                }
                                this.vmcDataService.changeWrkEditUsers(
                                    input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadRbacUserRoleSpec']['editUsers']);
                            }
                            if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadRbacUserRoleSpec'].hasOwnProperty('viewUsers')) {
                                if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadRbacUserRoleSpec']['viewUsers'] !== ""){
                                    this.apiClient.workloadClusterSettings = true;
                                }
                                this.vmcDataService.changeWrkViewUsers(
                                    input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadRbacUserRoleSpec']['viewUsers']);
                            }
                        }
                    }
                    let tmcEnabled;
                    this.vmcDataService.currentEnableTMC.subscribe(enableTmc => tmcEnabled = enableTmc);
                    if (tmcEnabled) {
                        if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadTsmIntegration')) {
                            if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadTsmIntegration'] === 'true') {
                                this.vmcDataService.changeEnableTSM(true);
                                if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('namespaceExclusions')) {
                                    if (input['componentSpec']['tkgWorkloadSpec']['namespaceExclusions'].hasOwnProperty('exactName')) {
                                        if (input['componentSpec']['tkgWorkloadSpec']['namespaceExclusions']['exactName'] !== ""){
                                            this.apiClient.workloadClusterSettings = true;
                                        }
                                        this.vmcDataService.changeTsmExactNamespaceExclusion(
                                            input['componentSpec']['tkgWorkloadSpec']['namespaceExclusions']['exactName']);
                                    }
                                    if (input['componentSpec']['tkgWorkloadSpec']['namespaceExclusions'].hasOwnProperty('startsWith')) {
                                        if (input['componentSpec']['tkgWorkloadSpec']['namespaceExclusions']['startsWith'] !== ""){
                                            this.apiClient.workloadClusterSettings = true;
                                        }
                                        this.vmcDataService.changeTsmStartsWithNamespaceExclusion(
                                            input['componentSpec']['tkgWorkloadSpec']['namespaceExclusions']['startsWith']);
                                    }
                                }
                            } else {
                                this.vmcDataService.changeEnableTSM(false);
                            }
                        }
                    }
                    if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadClusterGroupName')) {
                        if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterGroupName'] !== ""){
                            this.apiClient.workloadClusterSettings = true;
                        }
                        this.vmcDataService.changeWrkClusterGroupName(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterGroupName']);
                    }
                    if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadEnableDataProtection')) {
                        if(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadEnableDataProtection'] === 'true' && this.apiClient.tmcEnabled) {
                            this.vmcDataService.changeWrkEnableDataProtection(true);
                            this.apiClient.wrkDataProtectionEnabled = true;
                            if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadClusterCredential')) {
                                if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterCredential'] !== ""){
                                    this.apiClient.workloadClusterSettings = true;
                                }
                                this.vmcDataService.changeWrkDataProtectionCreds(
                                    input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterCredential']);
                            }
                            if (input['componentSpec']['tkgWorkloadSpec'].hasOwnProperty('tkgWorkloadClusterBackupLocation')) {
                                if (input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterBackupLocation'] !== ""){
                                    this.apiClient.workloadClusterSettings = true;
                                }
                                this.vmcDataService.changeWrkDataProtectionTargetLocation(
                                    input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterBackupLocation']);
                            }
                        } else {
                            this.vmcDataService.changeWrkEnableDataProtection(false);
                            this.apiClient.wrkDataProtectionEnabled = false;
                        }
                    } else {
                        this.vmcDataService.changeWrkEnableDataProtection(false);
                        this.apiClient.wrkDataProtectionEnabled = false;
                    }
                }
            }
            if (input.hasOwnProperty('tanzuExtensions')) {
                if (input['tanzuExtensions'].hasOwnProperty('enableExtensions')) {
                    if(input['tanzuExtensions']['enableExtensions'] === 'true') {
                        this.vmcDataService.changeEnableTanzuExtension(true);
                        if (input['tanzuExtensions'].hasOwnProperty('tkgClustersName')) {
                            this.vmcDataService.changeTkgClusters(input['tanzuExtensions']['tkgClustersName']);
                            this.processVmcEnableLogging(input);
                            this.processVmcEnableMonitoring(input);
                        }
                    } else {
                        this.vmcDataService.changeEnableTanzuExtension(false);
                        this.vmcDataService.changeEnableLoggingExtension(false);
                        this.vmcDataService.changeEnableMonitoringExtension(false);
                    }
                } else {
                    this.vmcDataService.changeEnableTanzuExtension(false);
                    this.vmcDataService.changeEnableLoggingExtension(false);
                    this.vmcDataService.changeEnableMonitoringExtension(false);
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
        this.vmcDataService.changeInputFileStatus(false);
        FormMetaDataStore.deleteAllSavedData();
        this.clusterType = 'management';
        this.router.navigate([APP_ROUTES.VMC_WIZARD]);
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

        this.setVmcParamsFromInputJSON(this.inputFile);
//         FormMetaDataStore.reset('form');
        FormMetaDataStore.deleteAllSavedData();
//         FormMetaDataStore.reset('dnsNtpForm');
//         FormMetaDataStore.reset('vmcProviderForm');
//         FormMetaDataStore.reset('vmcTanzuSaasSettingForm');
//         FormMetaDataStore.reset('vmcAVINetworkSettingForm');
//         FormMetaDataStore.reset('vmcTKGMgmtDataNWForm');
//         FormMetaDataStore.reset('vmcMgmtNodeSettingForm');
//         FormMetaDataStore.reset('vmcSharedServiceNodeSettingForm');
//         FormMetaDataStore.reset('vmcTKGWorkloadDataNWForm');
//         FormMetaDataStore.reset('vmcWorkloadNodeSettingForm');
//         FormMetaDataStore.reset('vmcExtensionSettingForm');
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
