/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular imports
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { saveAs as importedSaveAs } from "file-saver";
// App imports
import { APP_ROUTES } from '../../constants/routes.constants';
import { BasicSubscriber } from "../../abstracts/basic-subscriber";
import { APIClient } from 'src/app/swagger/api-client.service';
import { takeUntil } from 'rxjs/operators';
import { AppDataService } from '../../service/app-data.service';

/**
 * @class HeaderBarComponent
 * HeaderBarComponent is the Clarity header component for TKG Kickstart UI.
 */
@Component({
    selector: 'tkg-kickstart-ui-header-bar',
    templateUrl: './header-bar.component.html',
    styleUrls: ['./header-bar.component.scss']
})
export class HeaderBarComponent extends BasicSubscriber implements OnInit {

//     edition: string = '';
    docsUrl: string = '';
    public logFileName = 'service_installer_log_bundle';
    public status: boolean;
    constructor(private router: Router,
        public apiClient: APIClient,
        private appDataService: AppDataService ) {
        super();
    }

    ngOnInit() {
        this.docsUrl = 'https://github.com/vmware-tanzu/service-installer-for-vmware-tanzu/tree/main/docs/product';
        this.status = false;
        this.getDeploymentStatus();
        this.isDeploymentRunning();
    }

    /**
     * @method navigateHome
     * helper method to route user to application home route
     */
    navigateHome() {
        this.apiClient.redirectedToHome = true;
        this.router.navigate([APP_ROUTES.LANDING]);
    }

    navigateToDocs() {
        window.open(this.docsUrl, "_blank");
    }

    navigateToDeploymentTimeline(): void {
        this.router.navigate([APP_ROUTES.DEPLOY_TKGS])
    }

    isDeploymentRunning() {
        this.appDataService.getJobStatus()
            .pipe(takeUntil(this.unsubscribe))
            .subscribe((jobStatus) => {
                this.status=jobStatus;
            });
    }

    getDeploymentStatus(): void {
        this.apiClient.deployStatusOverview().pipe(takeUntil(this.unsubscribe)).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.appDataService.setJobStatus(true);
                }
                else {
                    this.appDataService.setJobStatus(false);
                }
            }
        }, (error: any) => {
            this.appDataService.setJobStatus(false);
        });
    }



    public downloadSupportBundle() {
        this.apiClient.downloadLogBundle('vsphere').subscribe(blob => {
            importedSaveAs(blob, this.logFileName);
        }, (error: any) => {
//             this.errorNotification = "Failed to download Support Bundle for Service Installer";
        });
    }

    public logoutSivt() {
        console.log("Logout of SIVT");
        this.apiClient.logoutOfSivt().subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.router.navigate([APP_ROUTES.LOGIN]);
                } else if (data.responseType === 'ERROR') {
                    this.router.navigate([APP_ROUTES.LOGIN]);
                }
            } else {
                console.log("Logged out forced");
                this.router.navigate([APP_ROUTES.LOGIN]);
            }
        }, (err: any) => {
            console.log("Logged out on ERROR");
            this.router.navigate([APP_ROUTES.LOGIN]);
        });
    }
}
