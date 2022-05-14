// Angular imports
import { Component, OnInit } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { Router } from '@angular/router';

// Third party imports
import { Observable } from 'rxjs';

// App imports
import {APIClient} from 'src/app/swagger/api-client.service';
import { BasicSubscriber } from 'src/app/shared/abstracts/basic-subscriber';
import { PROVIDERS, Providers } from '../../../shared/constants/app.constants';
import { APP_ROUTES, Routes } from '../../../shared/constants/routes.constants';
import { AppDataService } from '../../../shared/service/app-data.service';
import { BrandingObj } from '../../../shared/service/branding.service';

@Component({
    selector: 'tkg-kickstart-ui-start',
    templateUrl: './start.component.html',
    styleUrls: ['./start.component.scss'],
})
export class StartComponent extends BasicSubscriber implements OnInit {
    APP_ROUTES: Routes = APP_ROUTES;
    PROVIDERS: Providers = PROVIDERS;

    clusterType: string;
    provider: Observable<string>;
    infraType: Observable<string>;
    landingPageContent: BrandingObj;
    loading = false;
//     apiClient: APIClient;
    constructor(private router: Router,
                private appDataService: AppDataService,
                private titleService: Title,
                public apiClient: APIClient
                ) {
        super();
        this.provider = this.appDataService.getProviderType();
        this.infraType = this.appDataService.getInfraType();
    }

    ngOnInit() {
        /**
         * Load content in landing page
         */
        this.clusterType = 'management';
        this.landingPageContent = {
             logoClass: 'tanzu-logo',
             title: 'Service Installer for VMware Tanzu Setup',
            // tslint:disable-next-line:object-literal-sort-keys
             intro: 'VMware Tanzu Kubernetes Grid delivers the services that IT teams need to effectively support development ' +
                  'teams that develop and configure Kubernetes-based applications in a complex world. It balances the needs of ' +
                  'development teams to access resources and services, with the needs of centralized IT organizations to ' +
                  'maintain and control the development environments.<br\><br\>To begin using Tanzu Kubernetes Grid, you ' +
                  'first deploy a management cluster to your chosen infrastructure. The management cluster provides the entry ' +
                  'point for Tanzu Kubernetes Grid integration with your platform, and allows you to deploy multiple workload clusters.' +
                 // tslint:disable-next-line:max-line-length
                  '<br><br>Product documentation can be found <a href=\'https://docs.vmware.com/en/VMware-Tanzu-Kubernetes-Grid/index.html\' ' +
                  'target=\'_blank\'>here</a>.'
        };
        if (this.apiClient.redirectedToHome){
            console.log("Broswer Reload");
            this.apiClient.redirectedToHome = false;
            location.reload();
        }
    }

    navigateToUploadPanel(provider: string, infraType: string): void {
        this.loading = true;
        this.apiClient.tkgsStage = "";
        this.appDataService.setProviderType(provider);
        this.appDataService.setInfraType(infraType);
        const upload = APP_ROUTES.VSPHERE_UPLOAD_PANEL;
        this.router.navigate([upload]);
    }

    navigateToVsphereNsxtUploadPanel(provider: string): void {
        this.loading = true;
        this.apiClient.tkgsStage = "";
        console.log(provider);
        this.appDataService.setProviderType(provider);
        const upload = APP_ROUTES.VSPHERE_NSXT_UPLOAD_PANEL;
        this.router.navigate([upload]);
    }

    navigateToVmcUploadPanel(provider: string): void {
        this.loading = true;
        this.apiClient.tkgsStage = "";
        this.appDataService.setProviderType(provider);
        const upload = APP_ROUTES.VMC_UPLOAD_PANEL;
        this.router.navigate([upload]);
    }

    /**
     * @method navigateToWizard
     * @desc helper method to trigger router navigation to wizard
     * @param provider - the provider to load wizard for
     */
    navigateToWizard(provider: string): void {
        this.loading = true;
        this.appDataService.setProviderType(provider);
        let wizard;
        switch (provider) {
            case PROVIDERS.VSPHERE: {
                wizard = APP_ROUTES.WIZARD_MGMT_CLUSTER;
                break;
            }
            case PROVIDERS.AWS: {
                wizard = APP_ROUTES.AWS_WIZARD;
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
            case PROVIDERS.VMC: {
                wizard = APP_ROUTES.VMC_WIZARD;
            }
        }
        this.router.navigate([wizard]);
    }
}
