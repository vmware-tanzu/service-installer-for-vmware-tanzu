/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular imports
import { Component, OnInit, ViewChild } from '@angular/core';
import { Router } from '@angular/router';

// Third party imports
import { Subscription } from 'rxjs';

// App imports
import { DataService } from 'src/app/shared/service/data.service';
import { VMCDataService } from 'src/app/shared/service/vmc-data.service';
import { VsphereTkgsService } from 'src/app/shared/service/vsphere-tkgs-data.service';
import { VCDDataService } from 'src/app/shared/service/vcd-data.service';
import { FormMetaDataStore } from 'src/app/views/landing/wizard/shared/FormMetaDataStore';
import { PROVIDERS, Providers } from 'src/app/shared/constants/app.constants';
import { APP_ROUTES, Routes } from 'src/app/shared/constants/routes.constants';
import { AppDataService } from 'src/app/shared/service/app-data.service';
import { BrandingObj } from 'src/app/shared/service/branding.service';
import { APIClient } from 'src/app/swagger/api-client.service';
import { id } from '@cds/core/internal';

@Component({
    selector: 'app-upload',
    templateUrl: './vcd-upload-wizard.component.html',
    styleUrls: ['./vcd-upload-wizard.component.scss'],
})
export class VcdUploadWizardComponent implements OnInit {

    @ViewChild('attachments') public attachment: any;
    public APP_ROUTES: Routes = APP_ROUTES;
    public PROVIDERS: Providers = PROVIDERS;

    public displayWizard = false;
    public fileName: string;
    public fileUploaded = false;
    public file: File;
    public inputFile;

    public clusterType: string;
    public provider: string;
    public infraType: string;
    public landingPageContent: BrandingObj;
    public loading = false;

    public readFile = false;
    errorNotification = '';
    public noupload = true;
    showLoginLoader = false;

    tkgsStage: string;
    tkgsStageType = ['Enable Workload control plane', 'Namespace and Workload cluster']
    public subscription: Subscription;
    constructor(
        public apiClient: APIClient, private router: Router,
        private appDataService: AppDataService,
        private dataService: DataService,
        private vmcDataService: VMCDataService,
        private vsphereTkgsDataService: VsphereTkgsService,
        private vcdDataService: VCDDataService,

    ) {
        this.appDataService.getProviderType().asObservable().subscribe((data) => this.provider = data);
        this.appDataService.getInfraType().asObservable().subscribe((data) => this.infraType = data);
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
            reader.onload = async function(evt) {
                if (typeof evt.target.result === 'string') {
                    const readInput = await (JSON.parse(evt.target.result));
                    await console.log(' ');
                    return readInput;
                }
            };
            // tslint:disable-ne xt-line:only-arrow-functions
            reader.onerror = function(evt) {
                console.log('Error Reading Input File');
            };
        } else {
        }
        // Give an Error here
        return;
    }

    public setParamsFromInputJSONForVCD(input) {
        if(input) {
            this.vcdDataService.changeInputFileStatus(true);
            if(input.hasOwnProperty('envSpec')) {

                if (input['envSpec'].hasOwnProperty('marketplaceSpec')) {
                    if (input['envSpec']['marketplaceSpec'].hasOwnProperty('refreshToken')) {
                        if (input['envSpec']['marketplaceSpec']['refreshToken'] !== '') {
                            this.vcdDataService.changeIsMarketplace(true);
                        } else this.vcdDataService.changeIsMarketplace(false);
                        this.vcdDataService.changeMarketplaceRefreshToken(input['envSpec']['marketplaceSpec']['refreshToken']);
                    } else this.vcdDataService.changeIsMarketplace(false);
                } else this.vcdDataService.changeIsMarketplace(false);

                if(input['envSpec'].hasOwnProperty('infraComponents')) {
                    if (input['envSpec']['infraComponents'].hasOwnProperty('dnsServersIp')) {
                        this.vcdDataService.changeDnsServer(input['envSpec']['infraComponents']['dnsServersIp']);
                    }
                    if (input['envSpec']['infraComponents'].hasOwnProperty('searchDomains')) {
                        this.vcdDataService.changeSearchDomain(input['envSpec']['infraComponents']['searchDomains']);
                    }
                    if (input['envSpec']['infraComponents'].hasOwnProperty('ntpServers')) {
                        this.vcdDataService.changeNtpServer(input['envSpec']['infraComponents']['ntpServers']);
                    }
                }

                if(input['envSpec'].hasOwnProperty('ceipParticipation')) {
                    if(input['envSpec']['ceipParticipation'] === 'true') {
                        this.vcdDataService.changeCeipParticipation(true);
                    }
                    else this.vcdDataService.changeCeipParticipation(false);
                } else this.vcdDataService.changeCeipParticipation(false);

                if(input['envSpec'].hasOwnProperty('vcdSpec')) {
                    if(input['envSpec']['vcdSpec'].hasOwnProperty('vcdComponentSpec')) {
                        if(input['envSpec']['vcdSpec']['vcdComponentSpec'].hasOwnProperty('vcdAddress')) {
                            this.vcdDataService.changeVcdAddress(input['envSpec']['vcdSpec']['vcdComponentSpec']['vcdAddress']);
                        }
                        if(input['envSpec']['vcdSpec']['vcdComponentSpec'].hasOwnProperty('vcdSysAdminUserName')) {
                            this.vcdDataService.changeVcdUsername(input['envSpec']['vcdSpec']['vcdComponentSpec']['vcdSysAdminUserName']);
                        }
                        if(input['envSpec']['vcdSpec']['vcdComponentSpec'].hasOwnProperty('vcdSysAdminPassword')) {
                            this.vcdDataService.changeVcdPassword(atob(input['envSpec']['vcdSpec']['vcdComponentSpec']['vcdSysAdminPassword']));
                        }
                    }
                }
                if(input['envSpec'].hasOwnProperty('aviCtrlDeploySpec')) {
                    if(input['envSpec']['aviCtrlDeploySpec'].hasOwnProperty('deployAvi')) {
                        if(input['envSpec']['aviCtrlDeploySpec']['deployAvi'] === 'true') {
                            this.vcdDataService.aviGreenfield = true;
                            this.vcdDataService.configureAviNsxtCloud = true;
                            this.vcdDataService.createSeGroup = true;
                            this.vcdDataService.changeDeployAvi(true);
                        } else {
                            this.vcdDataService.aviGreenfield = false;
                            this.vcdDataService.changeDeployAvi(false);
                        }
                    }
                    if(input['envSpec']['aviCtrlDeploySpec'].hasOwnProperty('vcenterDetails')) {
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('vcenterAddress')) {
                            this.vcdDataService.changeVCAddress(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterAddress']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('vcenterSsoUser')) {
                            this.vcdDataService.changeVCUser(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterSsoUser']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('vcenterSsoPasswordBase64')) {
                            this.vcdDataService.changeVCPass(atob(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterSsoPasswordBase64']));
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('vcenterDatacenter')) {
                            this.vcdDataService.changeDatacenter(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterDatacenter']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('vcenterCluster')) {
                            this.vcdDataService.changeCluster(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterCluster']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('vcenterDatastore')) {
                            this.vcdDataService.changeDatastore(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterDatastore']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('resourcePoolName')) {
                            this.vcdDataService.changeResourcePool(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['resourcePoolName']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('contentLibraryName')) {
                            this.vcdDataService.changeContentLib(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['contentLibraryName']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('aviOvaName')) {
                            this.vcdDataService.changeOvaImage(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['aviOvaName']);
                        }
                    }
                    if(input['envSpec']['aviCtrlDeploySpec'].hasOwnProperty('aviMgmtNetwork')) {
                        if(input['envSpec']['aviCtrlDeploySpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtNetworkName')) {
                            this.vcdDataService.changeAviMgmtNetworkName(input['envSpec']['aviCtrlDeploySpec']['aviMgmtNetwork']['aviMgmtNetworkName']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtNetworkGatewayCidr')) {
                            this.vcdDataService.changeAviMgmtNetworkGatewayCidr(input['envSpec']['aviCtrlDeploySpec']['aviMgmtNetwork']['aviMgmtNetworkGatewayCidr']);
                        }
                    }
                    if(input['envSpec']['aviCtrlDeploySpec'].hasOwnProperty('aviComponentsSpec')) {
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviUsername')) {
                            this.vcdDataService.changeAviUsername(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviUsername']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviPasswordBase64')) {
                            this.vcdDataService.changeAviPasswordBase64(atob(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviPasswordBase64']));
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviBackupPassphraseBase64')) {
                            this.vcdDataService.changeAviBackupPasswordBase64(atob(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviBackupPassphraseBase64']));
                        }

                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('enableAviHa')) {
                            if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['enableAviHa'] === 'true') {
                                this.vcdDataService.changeEnableAviHa(true);
                            } else this.vcdDataService.changeEnableAviHa(false);
                        } else this.vcdDataService.changeEnableAviHa(false);

                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviController01Ip')) {
                            this.vcdDataService.changeAviController01Ip(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController01Ip']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviController01Fqdn')) {
                            this.vcdDataService.changeAviController01Fqdn(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController01Fqdn']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviController02Ip')) {
                            this.vcdDataService.changeAviController02Ip(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController02Ip']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviController02Fqdn')) {
                            this.vcdDataService.changeAviController02Fqdn(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController02Fqdn']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviController03Ip')) {
                            this.vcdDataService.changeAviController03Ip(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController03Ip']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviController03Fqdn')) {
                            this.vcdDataService.changeAviController03Fqdn(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController03Fqdn']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviClusterIp')) {
                            this.vcdDataService.changeAviClusterIp(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviClusterIp']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviClusterFqdn')) {
                            this.vcdDataService.changeAviClusterFqdn(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviClusterFqdn']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviSize')) {
                            this.vcdDataService.changeAviSize(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviSize']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviCertPath')) {
                            this.vcdDataService.changeAviCertPath(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviCertPath']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviCertKeyPath')) {
                            this.vcdDataService.changeAviCertKeyPath(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviCertKeyPath']);
                        }
                    }
                    if(input['envSpec']['aviCtrlDeploySpec'].hasOwnProperty('aviVcdDisplayName')) {
                        this.vcdDataService.changeAviVcdDisplayName(input['envSpec']['aviCtrlDeploySpec']['aviVcdDisplayName']);
                    }
                }
                if(input['envSpec'].hasOwnProperty('aviNsxCloudSpec')) {
                    if (input['envSpec']['aviNsxCloudSpec'].hasOwnProperty('configureAviNsxtCloud')) {
                        if(input['envSpec']['aviNsxCloudSpec']['configureAviNsxtCloud'] === 'true'){
                            this.vcdDataService.configureAviNsxtCloud = true;
                            this.vcdDataService.createSeGroup = true;
                            this.vcdDataService.changeConfigureNsxtCloud(true);
                        } else {
                            this.vcdDataService.changeConfigureNsxtCloud(false);
                            this.vcdDataService.configureAviNsxtCloud = false;
                        }
                    } else{
                        this.vcdDataService.changeConfigureNsxtCloud(false);
                        this.vcdDataService.configureAviNsxtCloud = false;
                    }

                    if(input['envSpec']['aviNsxCloudSpec'].hasOwnProperty('nsxDetails')) {
                        if(input['envSpec']['aviNsxCloudSpec']['nsxDetails'].hasOwnProperty('nsxtAddress')) {
                            this.vcdDataService.changeNsxtAddress(input['envSpec']['aviNsxCloudSpec']['nsxDetails']['nsxtAddress']);
                        }
                        if(input['envSpec']['aviNsxCloudSpec']['nsxDetails'].hasOwnProperty('nsxtUser')) {
                            this.vcdDataService.changeNsxtUser(input['envSpec']['aviNsxCloudSpec']['nsxDetails']['nsxtUser']);
                        }
                        if(input['envSpec']['aviNsxCloudSpec']['nsxDetails'].hasOwnProperty('nsxtUserPasswordBase64')) {
                            this.vcdDataService.changeNsxtUserPasswordBase64(atob(input['envSpec']['aviNsxCloudSpec']['nsxDetails']['nsxtUserPasswordBase64']));
                        }
                    }

                    if(input['envSpec']['aviNsxCloudSpec'].hasOwnProperty('aviNsxCloudName')) {
                        this.vcdDataService.changeAviNsxCloudName(input['envSpec']['aviNsxCloudSpec']['aviNsxCloudName']);
                    }

                    if(input['envSpec']['aviNsxCloudSpec'].hasOwnProperty('nsxtCloudVcdDisplayName')) {
                        this.vcdDataService.changeNsxtCloudVcdDisplayName(input['envSpec']['aviNsxCloudSpec']['nsxtCloudVcdDisplayName']);
                    }

                    if(input['envSpec']['aviNsxCloudSpec'].hasOwnProperty('vcenterDetails')) {
                        if(input['envSpec']['aviNsxCloudSpec']['vcenterDetails'].hasOwnProperty('vcenterAddress')) {
                            this.vcdDataService.changeVcenterAddressCloud(input['envSpec']['aviNsxCloudSpec']['vcenterDetails']['vcenterAddress']);
                        }
                        if(input['envSpec']['aviNsxCloudSpec']['vcenterDetails'].hasOwnProperty('vcenterSsoUser')) {
                            this.vcdDataService.changeVcenterSsoUserCloud(input['envSpec']['aviNsxCloudSpec']['vcenterDetails']['vcenterSsoUser']);
                        }
                        if(input['envSpec']['aviNsxCloudSpec']['vcenterDetails'].hasOwnProperty('vcenterSsoPasswordBase64')) {
                            this.vcdDataService.changeVcenterSsoPasswordBase64Cloud(atob(input['envSpec']['aviNsxCloudSpec']['vcenterDetails']['vcenterSsoPasswordBase64']));
                        }
                    }

                    if(input['envSpec']['aviNsxCloudSpec'].hasOwnProperty('aviSeTier1Details')) {
                        if(input['envSpec']['aviNsxCloudSpec']['aviSeTier1Details'].hasOwnProperty('nsxtTier1SeMgmtNetworkName')){
                            this.vcdDataService.changeNsxtTier1SeMgmtNetworkName(input['envSpec']['aviNsxCloudSpec']['aviSeTier1Details']['nsxtTier1SeMgmtNetworkName']);
                        }
                        if(input['envSpec']['aviNsxCloudSpec']['aviSeTier1Details'].hasOwnProperty('nsxtOverlay')){
                            this.vcdDataService.changeNsxtOverlay(input['envSpec']['aviNsxCloudSpec']['aviSeTier1Details']['nsxtOverlay']);
                        }
                    }

                    if(input['envSpec']['aviNsxCloudSpec'].hasOwnProperty('aviSeMgmtNetwork')) {
                        if(input['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork'].hasOwnProperty('aviSeMgmtNetworkName')) {
                            this.vcdDataService.changeAviSeMgmtNetworkName(input['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork']['aviSeMgmtNetworkName']);
                        }
                        if(input['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork'].hasOwnProperty('aviSeMgmtNetworkGatewayCidr')) {
                            this.vcdDataService.changeAviSeMgmtNetworkGatewayCidr(input['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork']['aviSeMgmtNetworkGatewayCidr']);
                        }
                        if(input['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork'].hasOwnProperty('aviSeMgmtNetworkDhcpStartRange')) {
                            this.vcdDataService.changeAviSeMgmtNetworkDhcpStartRange(input['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork']['aviSeMgmtNetworkDhcpStartRange']);
                        }
                        if(input['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork'].hasOwnProperty('aviSeMgmtNetworkDhcpEndRange')) {
                            this.vcdDataService.changeAviSeMgmtNetworkDhcpEndRange(input['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork']['aviSeMgmtNetworkDhcpEndRange']);
                        }
                    }
                }

                if(input['envSpec'].hasOwnProperty('cseSpec')) {
                    if(input['envSpec']['cseSpec'].hasOwnProperty('svcOrgSpec')) {
                        if(input['envSpec']['cseSpec']['svcOrgSpec'].hasOwnProperty('svcOrgName')) {
                            this.vcdDataService.changeSvcOrgName(input['envSpec']['cseSpec']['svcOrgSpec']['svcOrgName']);
                        }
                        if(input['envSpec']['cseSpec']['svcOrgSpec'].hasOwnProperty('svcOrgFullName')) {
                            this.vcdDataService.changeSvcOrgFullName(input['envSpec']['cseSpec']['svcOrgSpec']['svcOrgFullName']);
                        }
                    }
                    if(input['envSpec']['cseSpec'].hasOwnProperty('svcOrgVdcSpec')) {
                        if(input['envSpec']['cseSpec']['svcOrgVdcSpec'].hasOwnProperty('svcOrgVdcName')) {
                            this.vcdDataService.changeSvcOrgVdcName(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcName']);
                        }
                        if(input['envSpec']['cseSpec']['svcOrgVdcSpec'].hasOwnProperty('svcOrgVdcResourceSpec')) {
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('providerVDC')) {
                                this.vcdDataService.changeProviderVDC(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['providerVDC']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('cpuAllocation')) {
                                this.vcdDataService.changeCpuAllocation(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['cpuAllocation']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('cpuGuaranteed')) {
                                this.vcdDataService.changeCpuGuaranteed(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['cpuGuaranteed']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('memoryAllocation')) {
                                this.vcdDataService.changeMemoryAllocation(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['memoryAllocation']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('memoryGuaranteed')) {
                                this.vcdDataService.changeMemoryGuaranteed(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['memoryGuaranteed']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('vcpuSpeed')) {
                                this.vcdDataService.changeVcpuSpeed(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['vcpuSpeed']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('isElastic')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['isElastic'] === true) {
                                    this.vcdDataService.changeIsElastic(true);
                                }
                                else this.vcdDataService.changeIsElastic(false);
                            } else this.vcdDataService.changeIsElastic(false);

                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('includeMemoryOverhead')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['includeMemoryOverhead'] === 'true') {
                                    this.vcdDataService.changeIncludeMemoryOverhead(true);
                                } else this.vcdDataService.changeIncludeMemoryOverhead(false);
                            } else this.vcdDataService.changeIncludeMemoryOverhead(false);

                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('vmQuota')) {
                                this.vcdDataService.changeVmQuota(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['vmQuota']);
                            }
                            //STORAGE POLICY
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('storagePolicySpec')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['storagePolicySpec'].hasOwnProperty('storagePolicies')) {
                                    const storagePolicy: Map<string, string> = new Map<string, string>();
                                    let policyName;
                                    let policyLimit;
                                    let inputVal = input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['storagePolicySpec']['storagePolicies'];
                                    for(const spec in inputVal) {
                                        if(inputVal[spec].hasOwnProperty('storagePolicy') && inputVal[spec].hasOwnProperty('storageLimit')) {
                                            policyName = inputVal[spec]['storagePolicy'];
                                            policyLimit = inputVal[spec]['storageLimit'];
                                            storagePolicy.set(policyName, policyLimit);
                                        } else if (inputVal[spec].hasOwnProperty('storagePolicy')) {
                                            policyName = inputVal[spec]['storagePolicy'];
                                            storagePolicy.set(policyName, "");
                                        }
                                    }
                                    this.vcdDataService.changeStorageSpec(storagePolicy);
                                }

                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['storagePolicySpec'].hasOwnProperty('defaultStoragePolicy')) {
                                    this.vcdDataService.changeDefaultStoragePolicy(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['storagePolicySpec']['defaultStoragePolicy']);
                                }
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('thinProvisioning')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['thinProvisioning'] === 'true') {
                                    this.vcdDataService.changeThinProvisioning(true);
                                } else this.vcdDataService.changeThinProvisioning(false);
                            } else this.vcdDataService.changeThinProvisioning(false);
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('fastProvisioning')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['fastProvisioning'] === 'true') {
                                    this.vcdDataService.changeFastProvisioning(true);
                                } else this.vcdDataService.changeFastProvisioning(false);
                            } else this.vcdDataService.changeFastProvisioning(false);
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('networkPoolName')) {
                                this.vcdDataService.changeNetworkPoolName(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['networkPoolName']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('networkQuota')) {
                                this.vcdDataService.changeNetworkQuota(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['networkQuota']);
                            }
                        }

                        if(input['envSpec']['cseSpec']['svcOrgVdcSpec'].hasOwnProperty('serviceEngineGroup')) {
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup'].hasOwnProperty('createSeGroup')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['createSeGroup'] === 'true' || this.vcdDataService.aviGreenfield || this.vcdDataService.configureAviNsxtCloud) {
                                    this.vcdDataService.changeImportSEG(true);
                                    this.vcdDataService.createSeGroup = true;
                                } else{
                                    this.vcdDataService.createSeGroup = false;
                                    this.vcdDataService.changeImportSEG(false);
                                }
                            } else {
                                this.vcdDataService.changeImportSEG(false);
                                this.vcdDataService.createSeGroup = false;
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup'].hasOwnProperty('serviceEngineGroupName')) {
                                this.vcdDataService.changeServiceEngineGroupname(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['serviceEngineGroupName']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup'].hasOwnProperty('serviceEngineGroupVcdDisplayName')) {
                                this.vcdDataService.changeServiceEngineGroupVcdDisplayName(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['serviceEngineGroupVcdDisplayName']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup'].hasOwnProperty('reservationType')) {
                                this.vcdDataService.changeReservationType(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['reservationType']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup'].hasOwnProperty('vcenterPlacementDetails')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['vcenterPlacementDetails'].hasOwnProperty('vcenterDatacenter')) {
                                    this.vcdDataService.changeVcenterDatacenterCloud(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['vcenterPlacementDetails']['vcenterDatacenter']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['vcenterPlacementDetails'].hasOwnProperty('vcenterCluster')) {
                                    this.vcdDataService.changeVcenterClusterCloud(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['vcenterPlacementDetails']['vcenterCluster']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['vcenterPlacementDetails'].hasOwnProperty('vcenterDatastore')) {
                                    this.vcdDataService.changeVcenterDatastoreCloud(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['vcenterPlacementDetails']['vcenterDatastore']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['vcenterPlacementDetails'].hasOwnProperty('vcenterContentSeLibrary')) {
                                    this.vcdDataService.changeVcenterContentSeLibrary(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['vcenterPlacementDetails']['vcenterContentSeLibrary']);
                                }
                            }
                        }

                        if(input['envSpec']['cseSpec']['svcOrgVdcSpec'].hasOwnProperty('svcOrgVdcGatewaySpec')) {
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec'].hasOwnProperty('tier0GatewaySpec')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec'].hasOwnProperty('importTier0')) {
                                    if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec']['importTier0'] === 'true') {
                                        this.vcdDataService.changeImportTier0(true);
                                        this.vcdDataService.importTier0Nsxt = true;
                                    } else {
                                        this.vcdDataService.changeImportTier0(false);
                                        this.vcdDataService.importTier0Nsxt = false;
                                    }
                                } else {
                                    this.vcdDataService.changeImportTier0(false);
                                    this.vcdDataService.importTier0Nsxt = false;
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec'].hasOwnProperty('tier0Router')) {
                                    this.vcdDataService.changeTier0Router(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec']['tier0Router']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec'].hasOwnProperty('tier0GatewayName')) {
                                    this.vcdDataService.changeTier0GatewayName(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec']['tier0GatewayName']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec'].hasOwnProperty('extNetGatewayCIDR')) {
                                    this.vcdDataService.changeExtNetgatewayCIDR(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec']['extNetGatewayCIDR']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec'].hasOwnProperty('extNetStartIP')) {
                                    this.vcdDataService.changeExtNetStartIP(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec']['extNetStartIP']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec'].hasOwnProperty('extNetEndIP')) {
                                    this.vcdDataService.changeExtNetEndIP(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec']['extNetEndIP']);
                                }
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec'].hasOwnProperty('tier1GatewaySpec')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec'].hasOwnProperty('tier1GatewayName')) {
                                    this.vcdDataService.changeTier1Gatewayname(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec']['tier1GatewayName']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec'].hasOwnProperty('isDedicated')) {
                                    if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec']['isDedicated'] === 'true') {
                                        this.vcdDataService.changeIsDedicated(true);
                                    } else this.vcdDataService.changeIsDedicated(false);
                                } else this.vcdDataService.changeIsDedicated(false);
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec'].hasOwnProperty('primaryIp')) {
                                    this.vcdDataService.changePrimaryIp(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec']['primaryIp']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec'].hasOwnProperty('ipAllocationStartIP')) {
                                    this.vcdDataService.changeIpAllocationStartIP(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec']['ipAllocationStartIP']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec'].hasOwnProperty('ipAllocationEndIP')) {
                                    this.vcdDataService.changeIpAllocationEndIP(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec']['ipAllocationEndIP']);
                                }
                            }
                        }
                        if(input['envSpec']['cseSpec']['svcOrgVdcSpec'].hasOwnProperty('svcOrgVdcNetworkSpec')) {
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec'].hasOwnProperty('networkName')) {
                                this.vcdDataService.changeNetworkName(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec']['networkName']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec'].hasOwnProperty('gatewayCIDR')) {
                                this.vcdDataService.changeGatewayCIDR(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec']['gatewayCIDR']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec'].hasOwnProperty('staticIpPoolStartAddress')) {
                                this.vcdDataService.changeStaticIpPoolstartAddress(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec']['staticIpPoolStartAddress']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec'].hasOwnProperty('staticIpPoolEndAddress')) {
                                this.vcdDataService.changeStaticIpPoolendAddress(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec']['staticIpPoolEndAddress']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec'].hasOwnProperty('primaryDNS')) {
                                this.vcdDataService.changePrimaryDNS(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec']['primaryDNS']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec'].hasOwnProperty('secondaryDNS')) {
                                this.vcdDataService.changeSecondaryDNS(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec']['secondaryDNS']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec'].hasOwnProperty('dnsSuffix')) {
                                this.vcdDataService.changeDnsSuffix(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec']['dnsSuffix']);
                            }
                        }
                        if(input['envSpec']['cseSpec']['svcOrgVdcSpec'].hasOwnProperty('svcOrgCatalogSpec')) {
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgCatalogSpec'].hasOwnProperty('cseOvaCatalogName')) {
                                this.vcdDataService.changeCseOvaCatalogName(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgCatalogSpec']['cseOvaCatalogName']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgCatalogSpec'].hasOwnProperty('k8sTemplatCatalogName')) {
                                this.vcdDataService.changeK8sTemplatCatalogName(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgCatalogSpec']['k8sTemplatCatalogName']);
                            }
                        }
                    }
                    if(input['envSpec']['cseSpec'].hasOwnProperty('cseServerDeploySpec')){
                        if(input['envSpec']['cseSpec']['cseServerDeploySpec'].hasOwnProperty('vAppName')){
                            this.vcdDataService.changeVappName(input['envSpec']['cseSpec']['cseServerDeploySpec']['vAppName']);
                        }
                        if(input['envSpec']['cseSpec']['cseServerDeploySpec'].hasOwnProperty('customCseProperties')){
                            if(input['envSpec']['cseSpec']['cseServerDeploySpec']['customCseProperties'].hasOwnProperty('cseSvcAccountName')) {
                                this.vcdDataService.changeCseSvcAccountName(input['envSpec']['cseSpec']['cseServerDeploySpec']['customCseProperties']['cseSvcAccountName']);
                            }
                            if(input['envSpec']['cseSpec']['cseServerDeploySpec']['customCseProperties'].hasOwnProperty('cseSvcAccountPasswordBase64')) {
                                this.vcdDataService.changeCseSvcAccountPasswordBase64(atob(input['envSpec']['cseSpec']['cseServerDeploySpec']['customCseProperties']['cseSvcAccountPasswordBase64']));
                            }
                        }
                    }
                }
            }
        }
    }


    public navigateToWizardWithoutUpload(): void {
        this.loading = true;
        this.noupload = true;
        this.inputFile = null;
        this.readFile = false;
        if (this.infraType === 'tkgm') {
            this.attachment.nativeElement.value = '';
        }
        this.fileUploaded = false;
        this.fileName = '';
        this.file = null;
        this.dataService.changeInputFileStatus(false);
        FormMetaDataStore.deleteAllSavedData();
        this.clusterType = 'management';
        if (this.infraType === PROVIDERS.TKGM) {
            if (this.provider === PROVIDERS.VSPHERE) this.router.navigate([APP_ROUTES.WIZARD_MGMT_CLUSTER]);
            else this.router.navigate([APP_ROUTES.VCD_WIZARD]);
        } else if (this.infraType === PROVIDERS.TKGS) {
            this.router.navigate([APP_ROUTES.TKGS_VSPHERE_WIZARD]);
        }
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
        if (this.infraType === PROVIDERS.TKGM) {
            if(this.provider === PROVIDERS.VCD) {
                this.setParamsFromInputJSONForVCD(this.inputFile);
            }
            FormMetaDataStore.deleteAllSavedData();
        }
        let wizard;
        switch (this.infraType) {
            case PROVIDERS.TKGM: {
                if (this.provider === PROVIDERS.VSPHERE){
                    wizard = APP_ROUTES.WIZARD_MGMT_CLUSTER;
                }
                else {
                    wizard = APP_ROUTES.VCD_WIZARD;
                }
                break;
            }
            case PROVIDERS.TKGS: {
                wizard = APP_ROUTES.TKGS_VSPHERE_WIZARD;
                break;
            }
        }
        this.router.navigate([wizard]);
    }

    public openFormPanel() {
    }

    public uploadFile(event) {
        if (!event || !event.target || !event.target.files || event.target.files.length === 0) {
            this.fileUploaded = false;
            this.noupload = true;
            return;
        }
        this.noupload = false;
        this.file = event.target.files[0];
        const file = this.file;
        const name = this.file.name;
        const lastDot = name.lastIndexOf('.');

        this.fileName = name.substring(0, lastDot);
        this.fileUploaded = true;
        const ext = name.substring(lastDot + 1);
        this.fileName = this.fileName + '.' + ext;

        const self = this;
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
            if (this.infraType === 'tkgm') {
            this.attachment.nativeElement.value = '';
        }
            this.fileUploaded = false;
            this.fileName = '';
            this.file = null;
        }
    }
    getEnvType(): string {
        return this.apiClient.tkgsStage;
    }

    cardClick(nodeType: string) {
        if(nodeType === 'Enable Workload control plane') {
            this.apiClient.tkgsStage = 'wcp';
        } else if (nodeType === 'Namespace and Workload cluster'){
            this.apiClient.tkgsStage = 'namespace';
        } else {
            this.apiClient.tkgsStage = '';
        }
    }
}
