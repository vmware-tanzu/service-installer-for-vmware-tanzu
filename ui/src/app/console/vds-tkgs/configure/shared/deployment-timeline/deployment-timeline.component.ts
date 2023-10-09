import { Component, OnInit } from '@angular/core';
import {LogMessage as NgxLogMessage} from 'ngx-log-monitor';
import {Observable, Subject, Subscription, interval, timer } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { APIClient } from 'src/app/swagger/api-client.service';
import { ClrTimelineLayout, ClrTimelineStepState } from '@clr/angular';
import { AppDataService } from 'src/app/shared/service/app-data.service';
import { BasicSubscriber } from 'src/app/shared/abstracts/basic-subscriber';
import { saveAs as importedSaveAs } from "file-saver";
@Component({
  selector: 'app-deployment-timeline',
  templateUrl: './deployment-timeline.component.html',
  styleUrls: ['./deployment-timeline.component.scss']
})
export class DeploymentTimelineComponent extends BasicSubscriber implements OnInit {


    private stage : string;
    public startingLogs: NgxLogMessage[];
    public readonly ClrTimelineLayout = ClrTimelineLayout;
    public readonly ClrTimelineStepState = ClrTimelineStepState;
    public completedLogsStreaming: boolean = false;
    private providerType: string = '';
    private jsonPayload: any;
    private currentRequest :Subject<void>;
    private preCheckStatus: ClrTimelineStepState;
    private aviConfigStatus: ClrTimelineStepState;
    private aviWCPStatus: ClrTimelineStepState;
    private enableWCPStatus : ClrTimelineStepState;
    private supervisorNamespaceStatus: ClrTimelineStepState;
    private workloadClusterStatus: ClrTimelineStepState;
    private extensionDeploymentStatus: ClrTimelineStepState;
    public controller: AbortController;
    private startButtonDisable: boolean;
    private stopButtonDisable: boolean;
    public stopDeploymentModal: boolean;
    public stopDeploymentTriggered: boolean;
    viewStreamingLogs: Boolean;
    public logFileName = 'arcas_server.log';
    private deploymentStatusSubscription: Subscription;
    public logStream: Subject<NgxLogMessage>;
    public showErrorAlert: Boolean;
    public errorAlertMessage: String;

      // Expose an observable that will be bound to the log monitor
    public logStream$: Observable<NgxLogMessage>;

    constructor(private apiClient: APIClient,
                private appDataService: AppDataService) {
                super();
    }

    ngOnInit(): void {

        this.startingLogs = [{message: 'On Going Deployment'}]; // Intial Logs for Streaming Logs History
        this.logStream = new Subject<NgxLogMessage>(); // Logs streaming Subject and Observer
        this.logStream$ = this.logStream.asObservable();  // Logs streaming Subject and Observer
        /*
        provider type and stage WCP/namespace and either STOP deployment triggered needs to stored
        in local storage, so that when page is refreshed, default state can be maintained.
        */
        this.appDataService.getProviderType()
        .pipe(takeUntil(this.unsubscribe))
        .subscribe((provider) => {
            if (provider && provider.includes('vsphere')) {
                this.providerType = 'vSphere';
            } else if (provider && provider.includes('vcf')) {
                this.providerType = 'VCF';
            } else if (provider && provider.includes('vmc')) {
                this.providerType = 'VMC';
            }
        });
        this.stage = this.apiClient.tkgsStage
        this.stopDeploymentTriggered = false;
        // check provider is None, then take from local storage
        if (this.notValidValue(this.providerType)) {
            this.providerType = localStorage.getItem('providerType')
        }
        else {
            localStorage.setItem('providerType', this.providerType)
        }
        // check stage is None, then take from local storage
        if (this.notValidValue(this.stage)) {
            this.stage = localStorage.getItem('deploymentStage')
        }
        else {
            localStorage.setItem('deploymentStage', this.stage)
        }
        this.viewStreamingLogs = false; // check for opening the streaming logs pop-up
        /* load json  data for operation. */
        this.appDataService.getJsonPayload()
            .pipe(takeUntil(this.unsubscribe))
            .subscribe((payload) => {
            this.jsonPayload = payload
            });
        // Intial Icon's for the timelines.
        this.preCheckStatus = this.getIconShape('');
        this.aviConfigStatus = this.getIconShape('');
        this.aviWCPStatus = this.getIconShape('');
        this.enableWCPStatus = this.getIconShape('');
        this.supervisorNamespaceStatus = this.getIconShape('');
        this.workloadClusterStatus = this.getIconShape('');
        this.extensionDeploymentStatus = this.getIconShape('');
        // Intial button state for Deployment button
        this.startButtonDisable = false;
        this.stopButtonDisable = true;
        // Intial Pop-up Modal state
        this.stopDeploymentModal = false;
        // show Error Alert
        this.showErrorAlert = false;
        this.errorAlertMessage = '';

        // Intial fetch status of the timelines from ARCAS BE code and calls it every 5 secs.
        this.fetchDeploymentStatus();
        this.deploymentStatusSubscription = interval(5000).subscribe(() => {
            // Call the API every 5 seconds (to update timeline status on UI)
            this.fetchDeploymentStatus();
        });

    }
    public isStageIsWcp(): boolean {
        /* returns true for WCP stage */
        return this.stage === 'wcp';
    }

    public isStageIsNamespace(): boolean {
        /* returns true for Namespace stage */
        return this.stage === 'namespace';
    }


    private notValidValue(keyCheck: any): boolean {
        /* check variable from not Null*/
        return ((keyCheck === 'undefined') || (keyCheck === null ) || (keyCheck === '' ) || (keyCheck === undefined ))

    }

    getIconShape(event: string): ClrTimelineStepState {
        /* Fetch Icon shape depends on the state */
        switch (event.toLowerCase()) {
            case 'success':
                return ClrTimelineStepState.SUCCESS;
            case 'passed':
                return ClrTimelineStepState.SUCCESS;
            case 'processing':
                return ClrTimelineStepState.PROCESSING;
            case 'in progress':
                return ClrTimelineStepState.PROCESSING;
            case 'error':
                return ClrTimelineStepState.ERROR;
            case 'failed':
                return ClrTimelineStepState.ERROR;
            case 'not started':
                return ClrTimelineStepState.CURRENT;
            default:
                return ClrTimelineStepState.CURRENT;
        }
    }


    fetchDeploymentStatus() {
        /* calls ARCAS BE and update timeline status accordingly */
        this.apiClient.deployStatusDetails().pipe(takeUntil(this.unsubscribe)).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.preCheckStatus = this.getIconShape(data['Prechecks']);
                    this.aviConfigStatus = this.getIconShape(data['NSX ALB Deployment']);
                    this.aviWCPStatus = this.getIconShape(data['WCP Pre-configurations']);
                    this.enableWCPStatus = this.getIconShape(data['Workload Control Plane Activation']);
                    this.supervisorNamespaceStatus =  this.getIconShape(data['Supervisor Namespace']);
                    this.workloadClusterStatus =  this.getIconShape(data['Workload Cluster']);
                    this.extensionDeploymentStatus =  this.getIconShape(data['User Managed Packages']);
                }
                else {
                    this.preCheckStatus = this.getIconShape('error');
                    this.aviConfigStatus = this.getIconShape('error');
                    this.aviWCPStatus = this.getIconShape('error');
                    this.enableWCPStatus = this.getIconShape('error');
                    this.supervisorNamespaceStatus =  this.getIconShape('error');
                    this.workloadClusterStatus =  this.getIconShape('error');
                    this.extensionDeploymentStatus =  this.getIconShape('error');
                }
            }
        }, (error: any) => {
            this.preCheckStatus = this.getIconShape('error');
            this.aviConfigStatus = this.getIconShape('error');
            this.aviWCPStatus = this.getIconShape('error');
            this.enableWCPStatus = this.getIconShape('error');
            this.supervisorNamespaceStatus =  this.getIconShape('error');
            this.workloadClusterStatus =  this.getIconShape('error');
            this.extensionDeploymentStatus =  this.getIconShape('error');
        });
    }

    anyDeploymentRunning(): boolean {
        /* returns the job deployment status if any is running or not */
        if (this.isStageIsWcp()) {
            return (this.preCheckStatus == ClrTimelineStepState.PROCESSING || this.aviConfigStatus == ClrTimelineStepState.PROCESSING
                || this.aviWCPStatus == ClrTimelineStepState.PROCESSING || this.enableWCPStatus == ClrTimelineStepState.PROCESSING)

        }
        else if (this.isStageIsNamespace()) {
            return (this.supervisorNamespaceStatus == ClrTimelineStepState.PROCESSING || this.workloadClusterStatus == ClrTimelineStepState.PROCESSING
                || this.extensionDeploymentStatus == ClrTimelineStepState.PROCESSING)

        }

    }

    anyDeploymentNOTStarted(): boolean {
        /* returns the job deployment status if any is running or not */
        if (this.isStageIsWcp()) {
            return (this.preCheckStatus == ClrTimelineStepState.CURRENT && this.aviConfigStatus == ClrTimelineStepState.CURRENT
                && this.aviWCPStatus == ClrTimelineStepState.CURRENT && this.enableWCPStatus == ClrTimelineStepState.CURRENT)

        }
        else if (this.isStageIsNamespace()) {
            return (this.supervisorNamespaceStatus == ClrTimelineStepState.CURRENT && this.workloadClusterStatus == ClrTimelineStepState.CURRENT
                && this.extensionDeploymentStatus == ClrTimelineStepState.CURRENT)

        }

    }

    allDeploymentPassed(): boolean {
        /* returns the job deployment status if all job passed or not */
        if (this.isStageIsWcp()) {
            return (this.preCheckStatus == ClrTimelineStepState.SUCCESS && this.aviConfigStatus == ClrTimelineStepState.SUCCESS
                && this.aviWCPStatus == ClrTimelineStepState.SUCCESS && this.enableWCPStatus == ClrTimelineStepState.SUCCESS)
        }
        else if (this.isStageIsNamespace()) {
            return (this.supervisorNamespaceStatus == ClrTimelineStepState.SUCCESS && this.workloadClusterStatus == ClrTimelineStepState.SUCCESS
                && this.extensionDeploymentStatus == ClrTimelineStepState.SUCCESS)
        }

    }

    getStopbuttonDisabled(): boolean {
        // only enable when any deployment is running.
        return ((this.stopButtonDisable) || (!this.anyDeploymentRunning()));
    }

    getStartbuttonDisabled(): boolean {
        // only enable when no deployment is running
        return ((this.startButtonDisable) ||( this.anyDeploymentRunning()) || (this.allDeploymentPassed()));
    }

    getLogsButtonDisabled(): boolean {
        /* stream logs button should be enable only when any deployment started, in the initial stage it should be
        disable and when pop-up is closed after 5 seconds button should be disabled.
        */
        return this.anyDeploymentNOTStarted() || this.completedLogsStreaming;
    }

    preCheckStageStatus(): string {
        /* pre-check deployment timeline status */
        return this.preCheckStatus;

    }
    aviConfigStageStatus(): string {
        /* avi deployment deployment timeline status */
        return this.aviConfigStatus;

    }
    aviWCPStageStatus(): string {
        /* avi WCP timeline status */
        return this.aviWCPStatus;

    }
    enableWCPStageStatus(): string {
        /* WCP enablement timeline status */
        return this.enableWCPStatus;

    }

    supervisorNamespaceStageStatus(): string {
        /* supervisor namespace deployment timeline status */
        return this.supervisorNamespaceStatus;

    }
    workloadClusterStageStatus(): string {
        /* workload cluster timeline status */
        return this.workloadClusterStatus;

    }
    extensionDeploymentStageStatus(): string {
        /* Extensions Deployment timeline status */
        return this.extensionDeploymentStatus;

    }

    showErrorAlertModal(errorMessage: String) {
        this.showErrorAlert = true;
        this.errorAlertMessage = errorMessage;

    }

    async deployFromUI(): Promise<void> {
        /* Initial method to start deployment from UI */
        try {
            this.showErrorAlert = false; // set existing error to alert to None

            // Perform your ongoing operation here
            this.startButtonDisable = true;  // start button should be disabled once deployment started
            // verify jsonPayload
            if (this.notValidValue(this.jsonPayload)) {
                this.showErrorAlertModal('The deployment configuration was lost. This could happen if the browser was reloaded or closed while the deployment was in progress. You must reconfigure and deploy the application again.')
                return
            }
            this.stopButtonDisable = false; // stop button should be enabled once deployment started
            this.stopDeploymentTriggered = false;
            this.appDataService.setJobStatus(true);
            // dump json also
            if (this.stage === "wcp") {
                this.dumpJson(this.apiClient.vdsWCPJSONFileName);
                await this.startWCPDeployment();
            } else if (this.stage === "namespace") {
                this.dumpJson(this.apiClient.vdsNameSpaceJSONFileName);
                await this.startNamespaceDeployment();
            }
        } catch (error) {
            this.showErrorAlertModal('Error in starting Deployment')
            console.error(error);
        } finally {
            this.startButtonDisable = false;
            this.stopButtonDisable = true;
            this.appDataService.setJobStatus(false);
        }
    }

    jobNeedsRun(currentJob: ClrTimelineStepState, lastJob: ClrTimelineStepState): Boolean {
        /* if jobs in ERROR/CURRENT state and last job in SUCCESS then only it will be true */
        return (!this.stopDeploymentTriggered) && (currentJob === ClrTimelineStepState.ERROR || currentJob === ClrTimelineStepState.CURRENT)
        && (lastJob === ClrTimelineStepState.SUCCESS)

    }
    async startWCPDeployment() {
        // sequential workflow for TKGs WCP enablement

        if (this.jobNeedsRun(this.preCheckStatus, ClrTimelineStepState.SUCCESS)) {

            await this.vspherePrechecks();
        }
        if (this.jobNeedsRun(this.aviConfigStatus, this.preCheckStatus) ) {

            await this.vsphereAviStage();
        }
        if (this.jobNeedsRun(this.aviWCPStatus, this.aviConfigStatus) ) {

            await this.vsphereAviWCP();
        }
        if (this.jobNeedsRun(this.enableWCPStatus, this.aviWCPStatus)) {

            await this.vsphereWCPEnablement();
        }

    }

    async vspherePrechecks() {
        // starts precheck stage for vsphere TKGs deployment, and update the timeline depends on the API response
        this.preCheckStatus = ClrTimelineStepState.PROCESSING;
        await this.apiClient.triggerPrecheck(this.providerType.toLowerCase(), this.jsonPayload).toPromise().then((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.preCheckStatus = ClrTimelineStepState.SUCCESS;

                } else if (data.responseType === 'ERROR') {
                    this.preCheckStatus = ClrTimelineStepState.ERROR;
                    this.showErrorAlertModal('Error in performing pre-checks')
                }
            } else {
                this.preCheckStatus = ClrTimelineStepState.ERROR;
                this.showErrorAlertModal('Error in performing pre-checks')
            }
        })
        .catch((error: any) => {
            this.preCheckStatus = ClrTimelineStepState.ERROR;
            this.showErrorAlertModal('Error in performing pre-checks "' + error.msg + '"')
        });
    }
    async vsphereAviStage() {
        // starts vsphere avi deployment stage for vsphere TKGs deployment, and update the timeline depends on the API response
        this.aviConfigStatus = ClrTimelineStepState.PROCESSING;
        await this.apiClient.triggerAvi(this.providerType.toLowerCase(), this.jsonPayload).toPromise().then((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.aviConfigStatus = ClrTimelineStepState.SUCCESS;
                } else if (data.responseType === 'ERROR') {
                    this.aviConfigStatus = ClrTimelineStepState.ERROR;
                    this.showErrorAlertModal('Error in AVI deployment')
                }
            } else {
                this.aviConfigStatus = ClrTimelineStepState.ERROR;
                this.showErrorAlertModal('Error in AVI deployment')
            }
        })
        .catch((error: any) => {
            this.aviConfigStatus = ClrTimelineStepState.ERROR;
            this.showErrorAlertModal('Error in AVI deployment "' + error.msg + '"')
        });

    }
    async vsphereAviWCP() {
        // starts vsphere avi WCP deployment stage for vsphere TKGs deployment, and update the timeline depends on the API response
        this.aviWCPStatus = ClrTimelineStepState.PROCESSING;
        await this.apiClient.triggerAviWCP(this.providerType.toLowerCase(), this.jsonPayload).toPromise().then((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.aviWCPStatus = ClrTimelineStepState.SUCCESS;
                } else if (data.responseType === 'ERROR') {
                    this.aviWCPStatus = ClrTimelineStepState.ERROR;
                    this.showErrorAlertModal('Error in WCP configuration on AVI cloud')
                }
            } else {
                this.aviWCPStatus = ClrTimelineStepState.ERROR;
                this.showErrorAlertModal('Error in WCP configuration on AVI cloud')
            }
        })
        .catch((error: any) => {
            this.aviWCPStatus = ClrTimelineStepState.ERROR;
            this.showErrorAlertModal('Error in WCP configuration on AVI cloud "' + error.msg + '"')
        });
    }

    async vsphereWCPEnablement() {
        // starts vsphere avi WCP enablement stage for vsphere TKGs deployment, and update the timeline depends on the API response
        this.enableWCPStatus = ClrTimelineStepState.PROCESSING;
        await this.apiClient.triggerWCPEnablement(this.providerType.toLowerCase(), this.jsonPayload).toPromise().then((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.enableWCPStatus = ClrTimelineStepState.SUCCESS;
                } else if (data.responseType === 'ERROR') {
                    this.enableWCPStatus = ClrTimelineStepState.ERROR;
                    this.showErrorAlertModal('Error in WCP enablement on vSphere Cluster')
                }
            } else {
                this.enableWCPStatus = ClrTimelineStepState.ERROR;
                this.showErrorAlertModal('Error in WCP enablement on vSphere Cluster')
            }
        })
        .catch((error: any) => {
            this.enableWCPStatus = ClrTimelineStepState.ERROR;
            this.showErrorAlertModal('Error in WCP enablement on vSphere Cluster "' + error.msg + '"')
        });

    }

    async startNamespaceDeployment() {
        // sequential workflow for TKGs Namespace enablement

        if (this.jobNeedsRun(this.supervisorNamespaceStatus, ClrTimelineStepState.SUCCESS)) {

            await this.createSuperVisorNameSpace();
        }
        if (this.jobNeedsRun(this.workloadClusterStatus, this.supervisorNamespaceStatus) ) {

            await this.createWorkloadCluster();
        }
        if (this.jobNeedsRun(this.extensionDeploymentStatus, this.workloadClusterStatus) ) {

            await this.deployTanzuExtensions();
        }

    }

    async createSuperVisorNameSpace() {
        // starts vspher create supervisor namespace creation stage for vsphere TKGs deployment, and update the timeline depends on the API response
        this.supervisorNamespaceStatus = ClrTimelineStepState.PROCESSING;
        await this.apiClient.triggerSupervisorNamespaceCreation(this.providerType.toLowerCase(), this.jsonPayload).toPromise().then((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.supervisorNamespaceStatus = ClrTimelineStepState.SUCCESS;
                } else if (data.responseType === 'ERROR') {
                    this.supervisorNamespaceStatus = ClrTimelineStepState.ERROR;
                    this.showErrorAlertModal('Error while creating namespace')
                }
            } else {
                this.supervisorNamespaceStatus = ClrTimelineStepState.ERROR;
                this.showErrorAlertModal('Error while creating namespace')
            }
        })
        .catch((error: any) => {
            this.supervisorNamespaceStatus = ClrTimelineStepState.ERROR;
            this.showErrorAlertModal('Error while creating namespace "' + error.msg + '"');
        });

    }

    async createWorkloadCluster() {
        // starts vsphere workload cluster creation stage for vsphere TKGs deployment, and update the timeline depends on the API response
        this.workloadClusterStatus = ClrTimelineStepState.PROCESSING;
        await this.apiClient.triggeWorkloadClusterCreation(this.providerType.toLowerCase(), this.jsonPayload).toPromise().then((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.workloadClusterStatus = ClrTimelineStepState.SUCCESS;
                } else if (data.responseType === 'ERROR') {
                    this.workloadClusterStatus = ClrTimelineStepState.ERROR;
                    this.showErrorAlertModal('Error while creating workload cluster')
                }
            } else {
                this.workloadClusterStatus = ClrTimelineStepState.ERROR;
                this.showErrorAlertModal('Error while creating workload cluster')
            }
        })
        .catch((error: any) => {
            this.workloadClusterStatus = ClrTimelineStepState.ERROR;
            this.showErrorAlertModal('Error while creating workload cluster "' + error.msg + '"')
        });

    }

    async deployTanzuExtensions() {
        // starts tanzu extensions deployment stage for vsphere TKGs deployment, and update the timeline depends on the API response
        this.extensionDeploymentStatus = ClrTimelineStepState.PROCESSING;
        await this.apiClient.triggerExtensions(this.providerType.toLowerCase(), this.jsonPayload).toPromise().then((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.extensionDeploymentStatus = ClrTimelineStepState.SUCCESS;
                } else if (data.responseType === 'ERROR') {
                    this.extensionDeploymentStatus = ClrTimelineStepState.ERROR;
                    this.showErrorAlertModal('Error while deploying the Tanzu extension packages')
                }
            } else {
                this.extensionDeploymentStatus = ClrTimelineStepState.ERROR;
                this.showErrorAlertModal('Error while deploying the Tanzu extension packages')
            }
        })
        .catch((error: any) => {
            this.extensionDeploymentStatus = ClrTimelineStepState.ERROR;
            this.showErrorAlertModal('Error while deploying the Tanzu extension packages "' + error.msg + '"')
        });

    }


    public downloadLogFile(): void {
        // Download entire log file from SIVT VM
        this.apiClient.downloadLogFile('vsphere').subscribe(blob => {
            importedSaveAs(blob, this.logFileName);
        });
    }

    private dumpJson(filename: string): void {
        // TODO: enhance this to consider variable names and move it to common function
        const payload = this.jsonPayload;
        // Call the Generate API
        this.apiClient.generateInputJSON(payload, filename, 'vsphere').subscribe((data: any) => {
        }, (error: any) => {
        });
    }

    public startStreamingLogs(): void {
        // start Streaming of logs once modal pop-up opens
        this.viewStreamingLogs = true;
        this.controller = new AbortController();
        this.fetchDataFromStreamingEndpoint()
        this.completedLogsStreaming = true;

    }

    public stopStreamingLogs(): void {
        // calls when user click close to stop Streaming of logs
        this.viewStreamingLogs = false;
        this.startingLogs = [{message: 'Ongoing Deployment'}]; // Clears old logs when pop-up is close by appending it to history
        this.controller.abort(); // abort async call for the streaming logs API endpoint
        /* wait for 5 secs, after the Streaming Logs button get disable
        its because flask(BE) streaming endpoint takes some time to detect that client has been connected and close the streaming service.
        */
        setTimeout(() =>
        {
            this.completedLogsStreaming = false;
        }, 5000);
    }

    private fetchDataFromStreamingEndpoint(): void {
    // fetch the logs from the streaming endpoint
    const logStream = this.logStream; // local variables for logstream
    this.apiClient.streamingService(this.controller)
        .then(response => {
            if (!response.ok) {
            throw new Error('Network response was not ok');
            }

            // Get the response body as a ReadableStream
            const body = response.body;

            // Create a reader to read chunks of data
            const reader = body.getReader();

            // Read and push chunks of data as they become available
            function read() {
                reader.read().then(({ done, value }) => {
                    if (done) {
                    // The stream has ended
                    logStream.complete();
                    return;
                    }
                    const textDecoder = new TextDecoder();
                    const stringValue = textDecoder.decode(value); //convert value to string
                    const stringArray = stringValue.split("\n") // split the lines of array into line
                    for (const logLine of stringArray) {
                        if (logLine !== '') {  // ignore blank lines to dump
                            setTimeout(() =>
                            {
                                // Push the chunk of data to subscribers
                                logStream.next({'message': logLine});
                            },10);
                        }

                    }

                    // Continue reading the next chunk
                    read();
                }).catch(error => {
                    // Handle errors
                    // console.error('Error reading stream:', error);
                    // logStream.error(error);
                });
            }

            // Start reading the stream
            read();
        })
        .catch(error => {
            // Handle fetch errors
            console.error('Fetch error:', error);
            this.logStream.error(error);
        });

    }

    stopModal(): void {
        // event for handling STOP deployment modal
        this.stopDeploymentModal = true
    }

    stopDeployment(): void {
        // event for handling STOP deployment process
        this.stopDeploymentTriggered = true; // once stop deployment triggered apart from currentother jobs should not run.
        this.stopDeploymentModal = false;
        this.stopButtonDisable = true;  // once deployment stopped button should be disable
        this.showErrorAlertModal('After the current stage of deployment finishes, the deployment process will be stopped.')
    }

    ngOnDestroy(): void {
        // do all unsubscription
        if (this.currentRequest) {
            this.currentRequest.unsubscribe()
        }
        this.deploymentStatusSubscription.unsubscribe()
        this.logStream.unsubscribe();
    }

}
