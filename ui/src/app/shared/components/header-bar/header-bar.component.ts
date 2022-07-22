// Angular imports
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import {saveAs as importedSaveAs} from "file-saver";
// App imports
// import { takeUntil } from "rxjs/operators";
import { APP_ROUTES } from '../../constants/routes.constants';
// import Broker from "../../service/broker";
// import { TkgEvent, TkgEventType } from "../../service/Messenger";
import { BasicSubscriber } from "../../abstracts/basic-subscriber";
// import { EditionData } from "../../service/branding.service";
import { APIClient } from 'src/app/swagger/api-client.service';

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
    constructor(private router: Router,
        public apiClient: APIClient ) {
        super();
    }

    ngOnInit() {
//         Broker.messenger.getSubject(TkgEventType.BRANDING_CHANGED)
//             .pipe(takeUntil(this.unsubscribe))
//             .subscribe((data: TkgEvent) => {
//                 const content: EditionData = data.payload;
//                 this.edition = content.edition;
//                 this.docsUrl = (this.edition === 'tkg') ? 'https://docs.vmware.com/en/VMware-Tanzu-Kubernetes-Grid/index.html' :
//                     'http://tanzucommunityedition.io/docs';
//             });
        this.docsUrl = 'https://github.com/vmware-tanzu/service-installer-for-vmware-tanzu/tree/main/docs/product';
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

    public downloadSupportBundle() {
        this.apiClient.downloadLogBundle('vsphere').subscribe(blob => {
            importedSaveAs(blob, this.logFileName);
        }, (error: any) => {
//             this.errorNotification = "Failed to download Support Bundle for Service Installer";
        });
    }
}
