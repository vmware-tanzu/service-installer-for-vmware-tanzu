// Angular imports
import {Component, OnInit, ViewChild} from '@angular/core';

// Third party imports
import {
    BehaviorSubject
} from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { LogMessage as NgxLogMessage } from 'ngx-log-monitor';

// App imports
import { BasicSubscriber } from '../../../shared/abstracts/basic-subscriber';
import { APP_ROUTES, Routes } from '../../../shared/constants/routes.constants';
import { WebsocketService } from '../../../shared/service/websocket.service';
import { AppDataService } from '../../../shared/service/app-data.service';
import { APIClient } from 'src/app/swagger/api-client.service';
import { FormMetaDataStore } from '../wizard/shared/FormMetaDataStore';

@Component({
    // tslint:disable-next-line:component-selector
    selector: 'tkg-kickstart-ui-deploy-progress',
    templateUrl: './deploy-progress.component.html',
    styleUrls: ['./deploy-progress.component.scss']
})
export class DeployProgressComponent extends BasicSubscriber implements OnInit {
    @ViewChild('output') public logOutput: any;
    logOutputText;

    deploymentSteps = ['Precheck', 'AVI Configuration', 'Management Cluster Configuration', 'Shared Services Cluster Configuration', 'Workload Pre-configuration', 'Workload Cluster Configuration', 'Deploy Extensions'];
    selectedStep = [];
    showProgressStatus: boolean = false;
    public errorNotification: string = '';

    precheckSuccess: boolean = false;
    preconfigurationSuccess: boolean = false;
    aviSuccess: boolean = false;
    mgmtSuccess: boolean = false;
    sharedSuccess: boolean = false;
    wrkPreconfigSuccess: boolean = false;
    wrkSuccess: boolean = false;
    extensionSuccess: boolean = false;

    precheckStatus = 'not-started';
    preconfigurationStatus = 'not-started';
    aviStatus = 'not-started';
    mgmtStatus = 'not-started';
    sharedStatus = 'not-started';
    wrkPreConfigStatus = 'not-started';
    wrkStatus = 'not-started';
    extensionStatus = 'not-started';

    stream = 'http://172.16.40.170:8888/api/tanzu/streamLogs';

    precheckFailMsg: string;
    preconfigurationFailMsg: string;
    aviFailMsg: string;
    mgmtFailMsg: string;
    sharedFailMsg: string;
    wrkPreConfigFailMsg: string;
    wrkConfigFailMsg: string;
    extensionFailMsg: string;

    providerType: string = '';
    cli: string = '';
    pageTitle: string = '';
    clusterType: string;
    messages: any[] = [];
    msgs$ = new BehaviorSubject<NgxLogMessage>(null);
    curStatus: any = {
        msg: '',
        status: '',
        curPhase: '',
        finishedCount: 0,
        totalCount: 0,
    };

    APP_ROUTES: Routes = APP_ROUTES;
    phases: Array<string> = [];
    currentPhaseIdx: number;

    constructor(private websocketService: WebsocketService,
                private appDataService: AppDataService,
                private apiClient: APIClient) {
        super();
//         Broker.messenger.getSubject(TkgEventType.CLI_CHANGED)
//             .pipe(takeUntil(this.unsubscribe))
//             .subscribe(event => {
//                 this.cli = event.payload;
//             });
    }

    ngOnInit(): void {
//         this.initWebSocket();
//         Broker.messenger.getSubject(TkgEventType.BRANDING_CHANGED)
//             .pipe(takeUntil(this.unsubscribe))
//             .subscribe((data: TkgEvent) => {
//                 this.pageTitle = data.payload.branding.title;
//                 this.clusterType = data.payload.clusterType;
//             });

        this.appDataService.getProviderType()
            .pipe(takeUntil(this.unsubscribe))
            .subscribe((provider) => {
                if (provider && provider.includes('vsphere')) {
                    this.providerType = 'vSphere';
                } else if (provider && provider.includes('vcf')) {
                    this.providerType = 'VCF';
                } else if (provider && provider.includes('vmc')) {
                    this.providerType = 'VMC';
                } else if (provider && provider.includes('docker')) {
                    this.providerType = 'Docker';
                }
            });

        setTimeout(() => {
            if (this.providerType === 'vSphere') {
                this.vspherePrecheckStage();
            } else if (this.providerType === 'VCF') {
                this.vspherePrecheckStage();
            } else if (this.providerType === 'VMC') {
                this.vmcPrecheckStage();
            }
        }, 10000);

    }

    startLogging() {
        console.log('inside start logging');
        this.apiClient.streamLogs().subscribe((data: any) => {
            if (data && data !== null) {
                console.log(data.response);
                setInterval(function() {
                    this.logOutputText = data.response;
                }, 100);
            }
        });
        // const xhr = new XMLHttpRequest();
        // xhr.open('GET', 'http://172.16.40.170:5000/api/tanzu/streamLogs');
        // xhr.send();
        // console.log(xhr.responseText);
        // setInterval(function() {
        //     this.logOutput.textContent = xhr.responseText;
        // }, 1000);
    }

    vspherePrecheckStage() {
        this.precheckStatus = 'running';
        // setTimeout(() => {
        //     // Dumy Steps
        //     this.precheckStatus = 'success';
        //     this.precheckSuccess = true;
        //     this.vsphereAviStage();
        // }, 10000);
//         this.streamLogsFromPythonServer();
        let payload;
        if (this.providerType === 'vSphere') {
            payload = this.apiClient.vspherePayload;
        } else if (this.providerType === 'VCF') {
            payload = this.apiClient.vsphereNsxtPayload;
        }
        this.apiClient.triggerPrecheck(this.providerType.toLowerCase(), payload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.precheckStatus = 'success';
                    this.precheckSuccess = true;
                    this.vsphereAviStage();
                } else if (data.responseType === 'ERROR') {
                    this.precheckStatus = 'error';
                    this.precheckSuccess = false;
                    this.precheckFailMsg = data.msg;
                }
            } else {
                this.precheckStatus = 'error';
                this.precheckSuccess = false;
                this.precheckFailMsg = 'Session : Precheck failed. Download Support Bundle for logs.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.precheckStatus = 'error';
                this.precheckSuccess = false;
                this.precheckFailMsg = error.msg;
            } else {
                this.precheckStatus = 'error';
                this.precheckSuccess = false;
                this.precheckFailMsg = 'Session : Precheck failed. Download Support Bundle for logs.';
            }
        });
    }

    vmcPrecheckStage() {
        this.precheckStatus = 'running';
        // setTimeout(() => {
        //     // Dumy Steps
        //     this.precheckStatus = 'success';
        //     this.precheckSuccess = true;
        //     this.vsphereAviStage();
        // }, 10000);
//         this.streamLogsFromPythonServer();
        this.apiClient.triggerPrecheck(this.providerType.toLowerCase(), this.apiClient.vmcPayload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.precheckStatus = 'success';
                    this.precheckSuccess = true;
                    this.vmcPreConfiguration();
                } else if (data.responseType === 'ERROR') {
                    this.precheckStatus = 'error';
                    this.precheckSuccess = false;
                    this.precheckFailMsg = data.msg;
                }
            } else {
                this.precheckStatus = 'error';
                this.precheckSuccess = false;
                this.precheckFailMsg = 'Session : Precheck failed. Download Support Bundle for logs.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.precheckStatus = 'error';
                this.precheckSuccess = false;
                this.precheckFailMsg = error.msg;
            } else {
                this.precheckStatus = 'error';
                this.precheckSuccess = false;
                this.precheckFailMsg = 'Session : Precheck failed. Download Support Bundle for logs.';
            }
        });
    }

    vmcPreConfiguration() {
        this.preconfigurationStatus = 'running';
        this.apiClient.triggerVmcPreConfiguration(this.providerType.toLowerCase(), this.apiClient.vmcPayload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.preconfigurationStatus = 'success';
                    this.preconfigurationSuccess = true;
                    this.vmcAviStage();
                } else if (data.responseType === 'ERROR') {
                    this.preconfigurationStatus = 'error';
                    this.preconfigurationSuccess = false;
                    this.preconfigurationFailMsg = data.msg;
                }
            } else {
                this.preconfigurationStatus = 'error';
                this.preconfigurationSuccess = false;
                this.preconfigurationFailMsg = 'VMC_Pre_Configuration : VMC Pre-Configurations failed. Download Support Bundle for logs.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.preconfigurationStatus = 'error';
                this.preconfigurationSuccess = false;
                this.preconfigurationFailMsg = error.msg;
            } else {
                this.preconfigurationStatus = 'error';
                this.preconfigurationSuccess = false;
                this.preconfigurationFailMsg = 'VMC_Pre_Configuration : VMC Pre-Configurations failed. Download Support Bundle for logs.';
            }
        });
    }

    vsphereAviStage() {
        this.aviStatus = 'running';
//         setTimeout(() => {
//             // Dumy Steps
//             this.aviStatus = 'success';
//             this.aviSuccess = true;
//             this.vsphereMgmtStage();
//         }, 1000);
       let payload;
       if(this.providerType === 'vSphere') {
            payload = this.apiClient.vspherePayload;
       } else if (this.providerType === 'VCF') {
            payload = this.apiClient.vsphereNsxtPayload;
       }
        this.apiClient.triggerAvi(this.providerType.toLowerCase(), payload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.aviStatus = 'success';
                    this.aviSuccess = true;
                    this.vsphereMgmtStage();
                } else if (data.responseType === 'ERROR') {
                    this.aviStatus = 'failed';
                    this.aviSuccess = false;
                    this.aviFailMsg = data.msg;
                }
            } else {
                this.aviStatus = 'failed';
                this.aviSuccess = false;
                this.aviFailMsg = 'AVI_Configuration: AVI configured failed. Download Support Bundle for logs.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.aviStatus = 'failed';
                this.aviSuccess = false;
                this.aviFailMsg = error.msg;
            } else {
                this.aviStatus = 'failed';
                this.aviSuccess = false;
                this.aviFailMsg = 'AVI_Configuration: AVI configured failed. Download Support Bundle for logs.';
            }
        });
    }

    vmcAviStage() {
        this.aviStatus = 'running';
//         setTimeout(() => {
//             // Dumy Steps
//             this.aviStatus = 'success';
//             this.aviSuccess = true;
//             this.vsphereMgmtStage();
//         }, 1000);
        this.apiClient.triggerVmcAvi(this.providerType.toLowerCase(), this.apiClient.vmcPayload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.aviStatus = 'success';
                    this.aviSuccess = true;
                    this.vmcMgmtStage();
                } else if (data.responseType === 'ERROR') {
                    this.aviStatus = 'failed';
                    this.aviSuccess = false;
                    this.aviFailMsg = data.msg;
                }
            } else {
                this.aviStatus = 'failed';
                this.aviSuccess = false;
                this.aviFailMsg = 'AVI_Configuration: AVI configured failed. Download Support Bundle for logs.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.aviStatus = 'failed';
                this.aviSuccess = false;
                this.aviFailMsg = error.msg;
            } else {
                this.aviStatus = 'failed';
                this.aviSuccess = false;
                this.aviFailMsg = 'AVI_Configuration: AVI configured failed. Download Support Bundle for logs.';
            }
        });
    }

    vsphereMgmtStage() {
        this.mgmtStatus = 'running';
//         setTimeout(() => {
//             // Dumy Steps
//             this.mgmtStatus = 'success';
//             this.mgmtSuccess = true;
//             this.vsphereSharedStage();
//         }, 1000);
       let payload;
       if(this.providerType === 'vSphere') {
            payload = this.apiClient.vspherePayload;
       } else if (this.providerType === 'VCF') {
            payload = this.apiClient.vsphereNsxtPayload;
       }
        this.apiClient.triggerMgmt(this.providerType.toLowerCase(), payload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.mgmtStatus = 'success';
                    this.mgmtSuccess = true;
                    this.vsphereSharedStage();
                } else if (data.responseType === 'ERROR') {
                    this.mgmtStatus = 'failed';
                    this.mgmtSuccess = false;
                    this.mgmtFailMsg = data.msg;
                }
            } else {
                this.mgmtStatus = 'failed';
                this.mgmtSuccess = false;
                this.mgmtFailMsg = 'TKG_Mgmt_Configuration: TKG Management Cluster Configuration failed. Download Support Bundle for logs.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.mgmtStatus = 'failed';
                this.mgmtSuccess = false;
                this.mgmtFailMsg = error.msg;
            } else {
                this.mgmtStatus = 'failed';
                this.mgmtSuccess = false;
                this.mgmtFailMsg = 'TKG_Mgmt_Configuration: TKG Management Cluster Configuration failed. Download Support Bundle for logs.';
            }
        });
    }

    vmcMgmtStage() {
        this.mgmtStatus = 'running';
//         setTimeout(() => {
//             // Dumy Steps
//             this.mgmtStatus = 'success';
//             this.mgmtSuccess = true;
//             this.vsphereSharedStage();
//         }, 1000);

        this.apiClient.triggerVmcMgmt(this.providerType.toLowerCase(), this.apiClient.vmcPayload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.mgmtStatus = 'success';
                    this.mgmtSuccess = true;
                    this.vmcSharedStage();
                } else if (data.responseType === 'ERROR') {
                    this.mgmtStatus = 'failed';
                    this.mgmtSuccess = false;
                    this.mgmtFailMsg = data.msg;
                }
            } else {
                this.mgmtStatus = 'failed';
                this.mgmtSuccess = false;
                this.mgmtFailMsg = 'TKG_Mgmt_Configuration: TKG Management Cluster Configuration failed. Download Support Bundle for logs.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.mgmtStatus = 'failed';
                this.mgmtSuccess = false;
                this.mgmtFailMsg = error.msg;
            } else {
                this.mgmtStatus = 'failed';
                this.mgmtSuccess = false;
                this.mgmtFailMsg = 'TKG_Mgmt_Configuration: TKG Management Cluster Configuration failed. Download Support Bundle for logs.';
            }
        });
    }

    vsphereSharedStage() {
        this.sharedStatus = 'running';
//         setTimeout(() => {
//             // Dumy Steps
//             this.sharedStatus = 'error';
//             this.sharedSuccess = false;
//             this.vsphereWrkPreConfigStage();
//         }, 1000);
       let payload;
       if(this.providerType === 'vSphere') {
            payload = this.apiClient.vspherePayload;
       } else if (this.providerType === 'VCF') {
            payload = this.apiClient.vsphereNsxtPayload;
       }
        this.apiClient.triggerShared(this.providerType.toLowerCase(), payload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.sharedStatus = 'success';
                    this.sharedSuccess = true;
                    this.vsphereWrkPreConfigStage();
                } else if (data.responseType === 'ERROR') {
                    this.sharedStatus = 'error';
                    this.sharedSuccess = false;
                    this.sharedFailMsg = data.msg;
                }
            } else {
                this.sharedStatus = 'error';
                this.sharedSuccess = false;
                this.sharedFailMsg = 'Shared_Service_Configuration: TKG Shared Services Cluster Configuration failed. Download Support Bundle for logs.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.sharedStatus = 'error';
                this.sharedSuccess = false;
                this.sharedFailMsg = error.msg;
            } else {
                this.sharedStatus = 'error';
                this.sharedSuccess = false;
                this.sharedFailMsg = 'Shared_Service_Configuration: TKG Shared Services Cluster Configuration failed. Download Support Bundle for logs.';
            }
        });
    }

    vmcSharedStage() {
        this.sharedStatus = 'running';
//         setTimeout(() => {
//             // Dumy Steps
//             this.sharedStatus = 'error';
//             this.sharedSuccess = false;
//             this.vsphereWrkPreConfigStage();
//         }, 1000);

        this.apiClient.triggerVmcShared(this.providerType.toLowerCase(), this.apiClient.vmcPayload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.sharedStatus = 'success';
                    this.sharedSuccess = true;
                    this.vmcWrkPreConfigStage();
                } else if (data.responseType === 'ERROR') {
                    this.sharedStatus = 'error';
                    this.sharedSuccess = false;
                    this.sharedFailMsg = data.msg;
                }
            } else {
                this.sharedStatus = 'error';
                this.sharedSuccess = false;
                this.sharedFailMsg = 'Shared_Service_Configuration: TKG Shared Services Cluster Configuration failed. Download Support Bundle for logs.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.sharedStatus = 'error';
                this.sharedSuccess = false;
                this.sharedFailMsg = error.msg;
            } else {
                this.sharedStatus = 'error';
                this.sharedSuccess = false;
                this.sharedFailMsg = 'Shared_Service_Configuration: TKG Shared Services Cluster Configuration failed. Download Support Bundle for logs.';
            }
        });
    }

    vsphereWrkPreConfigStage() {
        this.wrkPreConfigStatus = 'running';
//         setTimeout(() => {
//             // Dumy Steps
//             this.wrkPreConfigStatus = 'success';
//             this.wrkPreconfigSuccess = true;
//             this.vsphereWrkStage();
//         }, 1000);
       let payload;
       if(this.providerType === 'vSphere') {
            payload = this.apiClient.vspherePayload;
       } else if (this.providerType === 'VCF') {
            payload = this.apiClient.vsphereNsxtPayload;
       }
        this.apiClient.triggerWrkPreConfig(this.providerType.toLowerCase(), payload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.wrkPreConfigStatus = 'success';
                    this.wrkPreconfigSuccess = true;
                    this.vsphereWrkStage();
                } else if (data.responseType === 'ERROR') {
                    this.wrkPreConfigStatus = 'error';
                    this.wrkPreconfigSuccess = false;
                    this.wrkPreConfigFailMsg = data.msg;
                }
            } else {
                this.wrkPreConfigStatus = 'error';
                this.wrkPreconfigSuccess = false;
                this.wrkPreConfigFailMsg = 'Workload_Preconfig: AVI objects Configuration for TKG Workload Cluster failed. Download Support Bundle for logs.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.wrkPreConfigStatus = 'error';
                this.wrkPreconfigSuccess = false;
                this.wrkPreConfigFailMsg = error.msg;
            } else {
                this.wrkPreConfigStatus = 'error';
                this.wrkPreconfigSuccess = false;
                this.wrkPreConfigFailMsg = 'Workload_Preconfig: AVI objects Configuration for TKG Workload Cluster failed. Download Support Bundle for logs.';
            }
        });
    }

    vmcWrkPreConfigStage() {
        this.wrkPreConfigStatus = 'running';
//         setTimeout(() => {
//             // Dumy Steps
//             this.wrkPreConfigStatus = 'success';
//             this.wrkPreconfigSuccess = true;
//             this.vsphereWrkStage();
//         }, 1000);

        this.apiClient.triggerVmcWrkPreConfig(this.providerType.toLowerCase(), this.apiClient.vmcPayload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.wrkPreConfigStatus = 'success';
                    this.wrkPreconfigSuccess = true;
                    this.vmcWrkStage();
                } else if (data.responseType === 'ERROR') {
                    this.wrkPreConfigStatus = 'error';
                    this.wrkPreconfigSuccess = false;
                    this.wrkPreConfigFailMsg = data.msg;
                }
            } else {
                this.wrkPreConfigStatus = 'error';
                this.wrkPreconfigSuccess = false;
                this.wrkPreConfigFailMsg = 'Workload_Preconfig: AVI objects Configuration for TKG Workload Cluster failed. Download Support Bundle for logs.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.wrkPreConfigStatus = 'error';
                this.wrkPreconfigSuccess = false;
                this.wrkPreConfigFailMsg = error.msg;
            } else {
                this.wrkPreConfigStatus = 'error';
                this.wrkPreconfigSuccess = false;
                this.wrkPreConfigFailMsg = 'Workload_Preconfig: AVI objects Configuration for TKG Workload Cluster failed. Download Support Bundle for logs.';
            }
        });
    }


    vsphereWrkStage() {
        this.wrkStatus = 'running';
//         setTimeout(() => {
//             //Dumy Steps
//             this.wrkStatus = 'success';
//             this.wrkSuccess = true;
//             this.vsphereExtensionStage();
//         }, 1000);
       let payload;
       if(this.providerType === 'vSphere') {
            payload = this.apiClient.vspherePayload;
       } else if (this.providerType === 'VCF') {
            payload = this.apiClient.vsphereNsxtPayload;
       }
        this.apiClient.triggerWrk(this.providerType.toLowerCase(), payload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.wrkStatus = 'success';
                    this.wrkSuccess = true;
                    this.extensionStage();
                } else if (data.responseType === 'ERROR') {
                    this.wrkStatus = 'error';
                    this.wrkSuccess = false;
                    this.wrkConfigFailMsg = data.msg;
                }
            } else {
                this.wrkStatus = 'error';
                this.wrkSuccess = false;
                this.wrkConfigFailMsg = 'Workload_Deploy: TKG Workload Cluster Configuration failed. Download Support Bundle for logs.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.wrkStatus = 'error';
                this.wrkSuccess = false;
                this.wrkConfigFailMsg = error.msg;
            } else {
                this.wrkStatus = 'error';
                this.wrkSuccess = false;
                this.wrkConfigFailMsg = 'Workload_Deploy: TKG Workload Cluster Configuration failed. Download Support Bundle for logs.';
            }
        });
    }

    vmcWrkStage() {
        this.wrkStatus = 'running';
//         setTimeout(() => {
//             //Dumy Steps
//             this.wrkStatus = 'success';
//             this.wrkSuccess = true;
//             this.vsphereExtensionStage();
//         }, 1000);

        this.apiClient.triggerVmcWrk(this.providerType.toLowerCase(), this.apiClient.vmcPayload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.wrkStatus = 'success';
                    this.wrkSuccess = true;
                    this.extensionStage();
                } else if (data.responseType === 'ERROR') {
                    this.wrkStatus = 'error';
                    this.wrkSuccess = false;
                    this.wrkConfigFailMsg = data.msg;
                }
            } else {
                this.wrkStatus = 'error';
                this.wrkSuccess = false;
                this.wrkConfigFailMsg = 'Workload_Deploy: TKG Workload Cluster Configuration failed. Download Support Bundle for logs.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.wrkStatus = 'error';
                this.wrkSuccess = false;
                this.wrkConfigFailMsg = error.msg;
            } else {
                this.wrkStatus = 'error';
                this.wrkSuccess = false;
                this.wrkConfigFailMsg = 'Workload_Deploy: TKG Workload Cluster Configuration failed. Download Support Bundle for logs.';
            }
        });
    }

    extensionStage() {
        this.extensionStatus = 'running';
//         setTimeout(() => {
//             //Dumy Steps
//             this.extensionStatus = 'success';
//         }, 1000);
        let env;
        let payload;
        if (this.providerType === 'vSphere') {
            env = 'vsphere';
            payload = this.apiClient.vspherePayload;
        } else if (this.providerType === 'VMC') {
            env = 'vmc';
            payload = this.apiClient.vmcPayload;
        } else if (this.providerType === 'VCF') {
            env = 'vcf';
            payload = this.apiClient.vsphereNsxtPayload;
        }
        this.apiClient.triggerExtensions(env, payload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.extensionStatus = 'success';
                } else if (data.responseType === 'ERROR') {
                    this.extensionStatus = 'error';
                    this.extensionFailMsg = data.msg;
                }
            } else {
                this.extensionStatus = 'error';
                this.extensionFailMsg = 'Deploy_Extentions: Deployment of extensions failed. Download Support Bundle for logs.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.extensionStatus = 'error';
                this.extensionFailMsg = error.msg;
            } else {
                this.extensionStatus = 'error';
                this.extensionFailMsg = 'Deploy_Extentions: Deployment of extensions failed. Download Support Bundle for logs.';
            }
        });
    }

    streamLogs() {

    }

    initWebSocket() {
        this.websocketService.connect()
            .subscribe(evt => {
                const processed = this.processData(JSON.parse(evt.data));
                if (processed) {
                    this.msgs$.next(processed as NgxLogMessage);
                    this.messages.push(processed);
                }
            });

        setTimeout(_ => {
            this.websocketService.sendMessage('logs');
        }, 100);

        this.websocketService.setOnClose(_ => {
            if (this.curStatus.status !== 'successful' && this.curStatus.status !== 'failed') {
                setTimeout(() => {
                    this.initWebSocket();
                }, 5000);
            }
        });
    }

    /**
     * @method convert log type
     * @param {string} logType
     * @return string
     * 'ERROR' -> 'ERR'
     * 'FATAL' -> 'ERR'
     * 'INFO' -> 'INFO'
     * 'WARN' -> 'WARN'
     * 'UNKNOWN' -> null
     */
    convertLogType(logType: string): string {
        if (logType === 'ERROR') {
            return 'ERR';
        } else if (logType === 'FATAL') {
            return 'ERR';
        } else if (logType === 'UNKNOWN') {
            return null;
        } else {
            return logType;
        }
    }

    /**
     * @method process websocket data
     *  if data is a line of log, push to logs array
     *  if data is status update, update deployment status
     * @param {object} data websocket entry from backend
     */
    processData(data) {
        if (data.type === 'log') {
            this.curStatus.curPhase = data.data.currentPhase || this.curStatus.curPhase;
            return {
                message: data.data.message.slice(21),
                type: this.convertLogType(data.data.logType),
                timestamp: data.data.message.slice(1, 20)
            };
        } else {
            this.curStatus.msg = data.data.message;
            this.curStatus.status = data.data.status;

            this.phases = data.data.totalPhases || [];
            if (data.data.currentPhase && this.phases.length) {
                this.curStatus.curPhase = data.data.currentPhase;
                this.currentPhaseIdx = this.phases.indexOf(this.curStatus.curPhase);
            }

            if (this.curStatus.status === 'successful') {
                this.curStatus.finishedCount = this.curStatus.totalCount;
                this.currentPhaseIdx = this.phases.length;
                FormMetaDataStore.deleteAllSavedData();
            } else if (this.curStatus.status !== 'failed') {
                this.curStatus.finishedCount = Math.max(0, data.data.totalPhases.indexOf(this.curStatus.curPhase));
            }

            this.curStatus.totalCount = data.data.totalPhases ? data.data.totalPhases.length : 0;
            return null;
        }
    }

    disableRunButton() {
        console.log(this.errorNotification);
        if (this.selectedStep.length === 0 || this.errorNotification!=='') {
            return true;
        }
        else {
            return false;
        }
    }

    runDeployment() {

    }
    getEnvType() {
        if (this.providerType === 'vSphere') {
            return 'vsphere';
        } else if (this.providerType === 'VMC') {
            return 'vmc';
        } else if (this.providerType === 'VCF') {
            return 'vcf';
        } else {
            return 'invalid';
        }
    }

    downloadSupportBundle() {
        const env = this.getEnvType();
        if (env === 'invalid') {
            this.errorNotification = 'Invalid Environment type provided.';
        } else {
            this.apiClient.downloadSupportBundle(env)
                .subscribe(fileData => {
                        const  b: any = new Blob([fileData], { type: 'application/zip' });
                        const url = URL.createObjectURL(b);
                        window.open(url);
                    }
                );
        }
    }

    checkSelectedSteps() {
        console.log('Inside step check');
        console.log(this.selectedStep);
        for (const step in this.selectedStep) {
            if (this.selectedStep[step] === 'Precheck') {

            }
            if (this.selectedStep[step] === 'AVI Configuration') {
                console.log('Avi-config');
                if (this.selectedStep.indexOf('Precheck') === -1) {
                    this.errorNotification = 'Please ensure that the previous steps are selected.';
                } else {
                    this.errorNotification = '';
                }
            }
        }
    }

    /**
     * @method getStepCurrentState
     * @param idx - the index of each step in the ngFor expression
     * helper method determines which state should be displayed for each
     * step of the timeline component
     */
    getStepCurrentState(idx) {
        if (idx === this.currentPhaseIdx && this.curStatus.status === 'failed') {
            return 'error';
        } else if (idx < this.currentPhaseIdx || this.curStatus.status === 'successful') {
            return 'success';
        } else if (idx === this.currentPhaseIdx) {
            return 'current';
        } else {
            return 'not-started';
        }
    }

    /**
     * @method getStatusDescription
     * generates page description text depending on edition and status
     * @return {string}
     */
    getStatusDescription(): string {
        if (this.curStatus.status === 'running') {
            return `Deployment of the ${this.pageTitle} ${this.clusterType} cluster to ${this.providerType} is in progress.`;
        } else if (this.curStatus.status === 'successful') {
            return `Deployment of the ${this.pageTitle} ${this.clusterType} cluster to ${this.providerType} is successful.`;
        } else if (this.curStatus.status === 'failed') {
            return `Deployment of the ${this.pageTitle} ${this.clusterType} cluster to ${this.providerType} has failed.`;
        }
    }

    streamLogsFromPythonServer() {
        const ws = new WebSocket('ws://' + window.location.hostname + ':5001/stream/?tail=1', 'echo-protocol');
        ws.onmessage = (event) => {
            console.log(event.data);
        };
        ws.onopen = () => {
            ws.send('hello');
        };
    }
}
