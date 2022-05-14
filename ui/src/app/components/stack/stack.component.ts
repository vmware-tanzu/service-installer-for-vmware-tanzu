import {Component, ViewChild, ElementRef, QueryList, Output} from '@angular/core';
import { FormGroup, Validators, FormBuilder, NgForm } from '@angular/forms';

import {ClrStepperPanel, ClrLoadingState, ClrStepButton, ClrWizard} from '@clr/angular';
import {EventEmitter} from '@cds/core/internal';
import {AnsibleService} from '../../shared/services/ansible.service';

@Component({
  selector: 'app-stack',
  templateUrl: './stack.component.html',
  styleUrls: [ './stack.component.scss' ]
})
export class AngularStepperReactiveStepperComponent {
  submitBtnState = ClrLoadingState.DEFAULT;
  @ViewChild('wizardlg') wizardLarge!: ClrWizard;
  public homeForm: FormGroup;
  public homeErrorMessage!: boolean;
  public isClicked!: boolean;
  public showMessage!: boolean;
  public refreshToken: any;
  public ipaddress: any;
  public responseDisplay!: string;
  public homeValidationErrorMessage!: string;
  public validationMap!: [];
  public showHomeValidationMessage!: boolean;
  public showLoginLoader = false;
  public executeButtonClicked = false;

  @ViewChild(ClrStepButton, { static: false }) submitButton!: ClrStepButton;

  constructor(private formBuilder: FormBuilder, public ansibleService: AnsibleService) {
    this.homeForm = this.formBuilder.group({
      login: this.formBuilder.group({
        refreshToken: ['', Validators.required],
      }),
      aviManagementSegment: this.formBuilder.group({
        aviManagementName: ['', Validators.required],
        aviGatewayAddress: ['', Validators.required],
        aviDhcpStartRange: ['', Validators.required],
        aviDhcpEndRange: ['', Validators.required],
        aviDnsServers: ['', Validators.required],
      }),
      tkgManagementSegment: this.formBuilder.group({
        tkgManagementName: ['', Validators.required],
        tkgGatewayAddress: ['', Validators.required],
        tkgDhcpStartRange: ['', Validators.required],
        tkgDhcpEndRange: ['', Validators.required],
        tkgDnsServers: ['', Validators.required],
      }),
      tkgWorkloadSegment: this.formBuilder.group({
        tkgWorkloadName: ['', Validators.required],
        tkgWorkloadGatewayAddress: ['', Validators.required],
        tkgWorkloadDhcpStartRange: ['', Validators.required],
        tkgWorkloadDhcpEndRange: ['', Validators.required],
        tkgWorkloadDnsServers: ['', Validators.required],
      }),
      tkgAviDataSegment: this.formBuilder.group({
        tkgAviDataName: ['', Validators.required],
        tkgAviDataGatewayAddress: ['', Validators.required],
        tkgAviDataDhcpStartRange: ['', Validators.required],
        tkgAviDataDhcpEndRange: ['', Validators.required],
        tkgAviDataDnsServers: ['', Validators.required],
      }),
      inventoryGroupsCgw: this.formBuilder.group({
        inventoryGroupsCgwAviName: ['', Validators.required],
        inventoryGroupsCgwTkgName: ['', Validators.required],
        inventoryGroupsTKGWorkloadName: ['', Validators.required],
        inventoryGroupsDnsIps: ['', Validators.required],
        inventoryGroupsNtpIPs: ['', Validators.required],
        inventoryGroupsCgwTkgManagementControlPlaneIP: ['', Validators.required],
        inventoryGroupsCgwTkgWorkloadControlPlaneIP: ['', Validators.required],
        inventoryGroupsCgwVcenterIP: ['', Validators.required],
      }),
      inventoryGroupsMgw:  this.formBuilder.group({
        inventoryGroupsMgwTkgManagementNetworkGroupName: ['', Validators.required],
        inventoryGroupsMgwTkgWorkloadNetworkGroupName: ['', Validators.required],
        inventoryGroupsMgwAviManagementNetworkGroupName: ['', Validators.required],
      }),
      firewallRuleCgw: this.formBuilder.group({
        tkgAndAviDnsNameCgw: ['', Validators.required],
        tkgAndAviNtpNameCgw: ['', Validators.required],
        tkgAndAviVcenterNameCgw: ['', Validators.required],
        tkgAndAviInternetNameCgw: ['', Validators.required],
        tkgAndAviMgmtNameCgw: ['', Validators.required],
        tkgMgmtToTkgWorkloadVipNameCgw: ['', Validators.required],
        tkgWorkloadToTkgMgmtVipNameCgw: ['', Validators.required],
      }),
      firewallRuleMgw: this.formBuilder.group({
        tkgAndAviVcenterNameMgw: ['', Validators.required],
      }),
      aviControllerConfig: this.formBuilder.group({
        csfrUserName: ['', Validators.required],
        csfrUserPassword: ['', Validators.required],
        setAdminPassword: ['', Validators.required],
        setServerListIpAndType: ['', Validators.required],
        ntpServerListAndType: ['', Validators.required],
        setBackupPassPhrase: ['', Validators.required],
      }),
    });
  }
  onClose(): any {

  }

  lastNextClicked(event: any): any{
    if (event.target.click) {
      this.isClicked = true;
    }
    if (!event.target.click) {
      this.isClicked = false;
    }
  }

  getShapeClass(data: string): any {
    if (data.includes('Success')) {
      return 'is-success';
    } else if (data.includes('Failed')) {
      return 'is-error';
    } else if (data.includes('Warning')) {
      return 'is-warning';
    }  else {
      return 'is-info';
    }
  }

  getShape(data: any): any {
    if (data.includes('Success')) {
      return 'success-standard';
    } else if (data.includes('Failed')) {
      return 'error-standard';
    } else if (data.includes('Warning')) {
      return 'warning-standard';
    }  else {
      return 'error-standard';
    }
  }


  submit(): any {
    console.log('Saving...');


    setTimeout(() => {

      console.log('Saved!');
    }, 2000);
  }

  executeAnsible(): any {
    this.submitBtnState = ClrLoadingState.LOADING;
    const userData = this.homeForm.value;
    this.showLoginLoader = true;
    this.showHomeValidationMessage = false;
    this.homeErrorMessage = false;
    this.executeButtonClicked = true;
    this.ansibleService.homePage(userData).subscribe((data: any) => {
      this.showLoginLoader = false;
      if (data && data !== null) {
        if (data.responseType === 'ERROR') {
          this.submitBtnState = ClrLoadingState.ERROR;
          this.validationMap =  data.msg;
          this.showHomeValidationMessage = true;
          this.showMessage = false;
          this.executeButtonClicked = false;
          console.log(data.msg);
        } else {
          this.submitBtnState = ClrLoadingState.SUCCESS;
          this.submitButton.navigateToNextPanel();
          this.refreshToken = userData.homeKeyId;
          this.ipaddress = userData.ipaddress;
          this.homeErrorMessage = false;
          this.showMessage = true;
          console.log(data.msg);
          this.validationMap =  data.msg;
        }
      } else {
        this.homeErrorMessage = true;
        this.executeButtonClicked = false;
      }
    }, (error: any) => {
      if (error.responseType === 'ERROR') {
        this.submitBtnState = ClrLoadingState.ERROR;
        this.homeValidationErrorMessage = error.errorMessage;
        this.showHomeValidationMessage = true;
        this.showMessage = false;
      } else {
        this.homeErrorMessage = true;
        this.showMessage = false;
      }
      this.showLoginLoader = false;
      this.executeButtonClicked = false;
    });
  }
}
