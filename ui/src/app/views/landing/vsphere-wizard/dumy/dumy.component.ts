import { TkgEventType } from 'src/app/shared/service/Messenger';
/**
 * Angular Modules
 */
import { Component, OnInit, Input } from '@angular/core';
import {
    Validators,
    FormControl
} from '@angular/forms';
import { distinctUntilChanged, takeUntil } from 'rxjs/operators';
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';

/**
 * App imports
 */
import { AppEdition } from 'src/app/shared/constants/branding.constants';
// import { KUBE_VIP, NSX_ADVANCED_LOAD_BALANCER } from '../../wizard/shared/components/steps/load-balancer/load-balancer-step.component';
import Broker from 'src/app/shared/service/broker';
import {DataService} from 'src/app/shared/service/data.service';
import {APIClient} from 'src/app/swagger/api-client.service';
import { NodeType, vSphereNodeTypes } from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import { PROVIDERS, Providers } from '../../../../shared/constants/app.constants';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
import {Subscription} from 'rxjs';
import {WizardBaseDirective} from '../../wizard/shared/wizard-base/wizard-base';

@Component({
    selector: 'app-dumy-step',
    templateUrl: './dumy.component.html',
    styleUrls: ['./dumy.component.scss'],
})
export class DumyComponent extends StepFormDirective implements OnInit {
    @Input() providerType: string;

    nodeTypes: Array<NodeType> = [];
    PROVIDERS: Providers = PROVIDERS;
    vSphereNodeTypes: Array<NodeType> = vSphereNodeTypes;
    nodeType: string;

    displayForm = false;
    additionalNoProxyInfo: string;
    fullNoProxy: string;
    enableNetworkName = true;
    networks = [];

    private dnsServer;
    private ntpServer;
    private searchDomain;
    private uploadStatus;
    subscription: Subscription;

//     controlPlaneEndpointProviders = [KUBE_VIP, NSX_ADVANCED_LOAD_BALANCER];
//     currentControlPlaneEndpoingProvider = KUBE_VIP;
//     controlPlaneEndpointOptional = "";

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                private apiClient: APIClient,
                private dataService: DataService) {

        super();
    }

    ngOnInit() {
        super.ngOnInit();

        this.formGroup.addControl(
            'dnsServer',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIps(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('ntpServer',
            new FormControl('', [
                Validators.required,
                this.validationService.isCommaSeparatedIpsOrFqdn(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('searchDomain',
            new FormControl('', [
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        setTimeout(_ => {
            // this.displayForm = true;
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentDnsValue.subscribe(
                    (dnsServer) => this.dnsServer = dnsServer);
                this.formGroup.get('dnsServer').setValue(this.dnsServer);
                this.subscription = this.dataService.currentNtpValue.subscribe(
                    (ntpServer) => this.ntpServer = ntpServer);
                this.formGroup.get('ntpServer').setValue(this.ntpServer);
                this.subscription = this.dataService.currentSearchDomainValue.subscribe(
                    (searchDomain) => this.searchDomain = searchDomain);
                this.formGroup.get('searchDomain').setValue(this.searchDomain);
            }
        });
//         this.formGroup['canMoveToNext'] = () => {
//             return (this.formGroup.get('dnsServer').valid &&
//                 this.formGroup.get('ntpServer').valid);
//         };
    }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
        // don't fill password field with ****
        if (!this.uploadStatus) {
            this.formGroup.get('dnsServer').setValue('');
            this.formGroup.get('ntpServer').setValue('');
        }
    }
}

