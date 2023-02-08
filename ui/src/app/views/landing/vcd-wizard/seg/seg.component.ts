/*
* Copyright 2021 VMware, Inc
* SPDX-License-Identifier: BSD-2-Clause
*/
/**
 * Angular Modules
 */
import { Component, Input, OnInit } from '@angular/core';
import { Validators, FormControl } from '@angular/forms';
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';
/**
 * App imports
 */
import { VCDDataService } from 'src/app/shared/service/vcd-data.service';
import { APIClient } from 'src/app/swagger/api-client.service';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
import { Subscription } from 'rxjs';


@Component({
    selector: 'app-seg-step',
    templateUrl: './seg.component.html',
    styleUrls: ['./seg.component.scss'],
})
 export class ServiceEngineGroupComponent extends StepFormDirective implements OnInit {
    
     private createSeGroup = false;
     @Input() InputCreateSeGroup: boolean;
     @Input() InputVcenterDatacenter: [];
     @Input() InputVcenterCluster: [];
     @Input() InputVcenterDatastore: [];
     @Input() InputVcenterContentSeLibrary: [];
     @Input() InputServiceEngineGroupName: [];
     @Input() InputServiceEngineGroupVcdDisplayName: [];

     private serviceEngineGroupName;
     private serviceEngineGroupVcdDisplayName;
     public reservationTypes = ['SHARED', 'DEDICATED'];
     private reservationType;

     private vcenterDatacenter;
     private vcenterCluster
     private vcenterContentSeLibrary;
     private vcenterDatastore;
      // =========================== COMMON PROPERTIES ========================================
     private uploadStatus;
     subscription: Subscription;
   
     constructor(private validationService: ValidationService,
                 private wizardFormService: VSphereWizardFormService,
                 private apiClient: APIClient,
                 public dataService: VCDDataService) {
  
         super();
     }
   
     ngOnInit() {
         super.ngOnInit();
          
         this.formGroup.addControl('createSeGroup', new FormControl(false));

         this.formGroup.addControl('serviceEngineGroupName', new FormControl('', [Validators.required]));
         this.formGroup.addControl('serviceEngineGroupVcdDisplayName', new FormControl('', [Validators.required]));
         this.formGroup.addControl('serviceEngineGroupVcdDisplayNameInput', new FormControl('', []));
         this.formGroup.addControl('reservationType', new FormControl('SHARED', []));

         this.formGroup.addControl('vcenterDatacenter', new FormControl('', []));
         this.formGroup.addControl('vcenterCluster', new FormControl('', []));
         this.formGroup.addControl('vcenterDatastore', new FormControl('', []));
         this.formGroup.addControl('vcenterContentSeLibrary', new FormControl('', []));
         this.formGroup.addControl('newVcenterContentSeLibrary', new FormControl('', []));

        this.formGroup['canMoveToNext'] = () => {
            this.formGroup.get('createSeGroup').setValue(this.dataService.createSeGroup);
            this.toggleImportSEG();
            return this.formGroup.valid;
        };
   
         setTimeout(_ => {
             this.subscription = this.dataService.currentInputFileStatus.subscribe(
                 (uploadStatus) => this.uploadStatus = uploadStatus);
             if (this.uploadStatus) {
                this.subscription = this.dataService.currentImportSEG.subscribe((segImport) => this.dataService.createSeGroup = segImport);
                this.formGroup.get('createSeGroup').setValue(this.dataService.createSeGroup);

                if(this.dataService.createSeGroup) {
                    this.subscription = this.dataService.currentVcenterDatacenterCloud.subscribe(
                        (datacenter) => this.vcenterDatacenter = datacenter);
                    if(this.dataService.vc2Datacenters.indexOf(this.vcenterDatacenter) !== -1) {
                        this.formGroup.get('vcenterDatacenter').setValue(this.vcenterDatacenter);
                    }

                    this.subscription = this.dataService.currentVcenterClusterCloud.subscribe(
                        (cluster) => this.vcenterCluster = cluster);
                    if(this.dataService.vc2Clusters.indexOf(this.vcenterCluster) !== -1) {
                        this.formGroup.get('vcenterCluster').setValue(this.vcenterCluster);
                    }

                    this.subscription = this.dataService.currentVcenterDatastoreCloud.subscribe(
                        (datastore) => this.vcenterDatastore = datastore);
                    if(this.dataService.vc2Datastores.indexOf(this.vcenterDatastore) !== -1) {
                        this.formGroup.get('vcenterDatastore').setValue(this.vcenterDatastore);
                    }

                    this.subscription = this.dataService.currentVcenterContentSeLibrary.subscribe(
                    (lib)=> this.vcenterContentSeLibrary = lib);
                    if(this.dataService.vc2ContentLibs.indexOf(this.vcenterContentSeLibrary) !== -1) {
                        this.formGroup.get('vcenterContentSeLibrary').setValue(this.vcenterContentSeLibrary);
                    } else {
                        this.formGroup.get('vcenterContentSeLibrary').setValue('CREATE NEW');
                        this.onContentLibraryChange();
                        this.formGroup.get('newVcenterContentSeLibrary').setValue(this.vcenterContentSeLibrary);
                    }

                    this.subscription = this.dataService.currentServiceEngineGroupname.subscribe((se) => this.serviceEngineGroupName = se);
                    this.formGroup.get('serviceEngineGroupName').setValue(this.serviceEngineGroupName);
                    this.subscription = this.dataService.currentServiceEngineGroupVcdDisplayName.subscribe((vcdname) => this.serviceEngineGroupVcdDisplayName = vcdname);
                    this.formGroup.get('serviceEngineGroupVcdDisplayName').setValue(this.serviceEngineGroupVcdDisplayName);
                    this.subscription = this.dataService.currentReservationType.subscribe((reser) => this.reservationType = reser);
                    if(this.reservationTypes.indexOf(this.reservationType) !== -1) this.formGroup.get('reservationType').setValue(this.reservationType);
                } else {
                    this.subscription = this.dataService.currentServiceEngineGroupname.subscribe((se) => this.serviceEngineGroupName = se);
                    // console.log("SERVICE ENGINE GROUP");
                    // console.log(this.serviceEngineGroupName);
                    if(this.dataService.serviceEngineGroupnamesAlb.indexOf(this.serviceEngineGroupName) !== -1) {
                        this.formGroup.get('serviceEngineGroupName').setValue(this.serviceEngineGroupName);
                    }
                    this.subscription = this.dataService.currentServiceEngineGroupVcdDisplayName.subscribe((vcdname) => this.serviceEngineGroupVcdDisplayName = vcdname);
                    if(this.dataService.serviceEngineGroupVcdDisplayNames.indexOf(this.serviceEngineGroupVcdDisplayName) !== -1) {
                        this.formGroup.get('serviceEngineGroupVcdDisplayName').setValue(this.serviceEngineGroupVcdDisplayName);
                    } else {
                        this.formGroup.get('serviceEngineGroupVcdDisplayName').setValue("IMPORT TO VCD");
                        this.onServiceEngineGroupVcdDisplayNameChange();
                        this.formGroup.get('serviceEngineGroupVcdDisplayNameInput').setValue(this.serviceEngineGroupVcdDisplayName);
                        this.subscription = this.dataService.currentReservationType.subscribe((reser) => this.reservationType = reser);
                        if(this.reservationTypes.indexOf(this.reservationType) !== -1) this.formGroup.get('reservationType').setValue(this.reservationType);                        
                    }
                }
            }

        });
    }


    ngOnChanges() {
        if(this.formGroup.get('createSeGroup')){
            if(this.formGroup.get('createSeGroup')) this.formGroup.get('createSeGroup').setValue(this.dataService.createSeGroup);
            // this.toggleImportSEG(); 
        }
        if(this.dataService.vc2Datacenters.length !== 0 && this.dataService.vc2Datacenters.indexOf(this.vcenterDatacenter) !== -1) {
            if(this.formGroup.get('vcenterDatacenter')) this.formGroup.get('vcenterDatacenter').setValue(this.vcenterDatacenter);
        }
        if(this.dataService.vc2Clusters.length !== 0 && this.dataService.vc2Clusters.indexOf(this.vcenterCluster) !== -1) {
            if(this.formGroup.get('vcenterCluster')) this.formGroup.get('vcenterCluster').setValue(this.vcenterCluster);
        }
        if(this.dataService.vc2Datastores.length !== 0 && this.dataService.vc2Datastores.indexOf(this.vcenterDatastore) !== -1) {
            if(this.formGroup.get('vcenterDatastore')) this.formGroup.get('vcenterDatastore').setValue(this.vcenterDatastore);
        }
        if(this.dataService.vc2ContentLibs.length !== 0 && this.dataService.vc2ContentLibs.indexOf(this.vcenterContentSeLibrary) !== -1) {
            if(this.formGroup.get('vcenterContentSeLibrary')) this.formGroup.get('vcenterContentSeLibrary').setValue(this.vcenterContentSeLibrary);
        }
        else {
            if(this.formGroup.get('vcenterContentSeLibrary')) this.formGroup.get('vcenterContentSeLibrary').setValue('CREATE NEW');
            if(this.formGroup.get('newVcenterContentSeLibrary')) this.formGroup.get('newVcenterContentSeLibrary').setValue(this.vcenterContentSeLibrary);
        }
        if(!this.dataService.createSeGroup){
            if(this.dataService.serviceEngineGroupnamesAlb.length !== 0 && this.dataService.serviceEngineGroupnamesAlb.indexOf(this.serviceEngineGroupName) !== -1) {
                if(this.formGroup.get('serviceEngineGroupName')) this.formGroup.get('serviceEngineGroupName').setValue(this.serviceEngineGroupName);
            }
            if(this.dataService.serviceEngineGroupVcdDisplayNames.length !== 0 && this.dataService.serviceEngineGroupVcdDisplayNames.indexOf(this.serviceEngineGroupVcdDisplayName) !== -1) {
                if(this.formGroup.get('serviceEngineGroupVcdDisplayName')) this.formGroup.get('serviceEngineGroupVcdDisplayName').setValue(this.serviceEngineGroupVcdDisplayName);
            } else {
                if(this.formGroup.get('serviceEngineGroupVcdDisplayName')) this.formGroup.get('serviceEngineGroupVcdDisplayName').setValue('IMPORT TO VCD');
                if(this.formGroup.get('serviceEngineGroupVcdDisplayNameInput')) this.formGroup.get('serviceEngineGroupVcdDisplayNameInput').setValue(this.serviceEngineGroupVcdDisplayName);
            }
        }
    }


     setSavedDataAfterLoad() {
         super.setSavedDataAfterLoad();
     }

     getVsphereData() {
        let vCenterData = {
            "vcenterAddress": "",
            "vcenterSsoUser": "",
            "vcenterSsoPasswordBase64": ""
        };

        this.dataService.currentVcenterAddressCloud.subscribe((address) => vCenterData['vcenterAddress'] = address);
        this.dataService.currentVcenterSsoUserCloud.subscribe((user) => vCenterData['vcenterSsoUser'] = user);
        this.dataService.currentVcenterSsoPasswordBase64Cloud.subscribe((password) => vCenterData['vcenterSsoPasswordBase64'] = password);

        this.apiClient.getVsphere1Data('vcd', vCenterData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.vc2Datacenters = data.DATACENTERS;
                    this.dataService.vc2ContentLibs = data.CONTENTLIBRARY_NAMES;
                    if (this.uploadStatus){
                        if (this.dataService.vc2Datacenters.indexOf(this.vcenterDatacenter) === -1) {
                        } else {
                            this.formGroup.get('vcenterDatacenter').setValue(this.vcenterDatacenter);
                            this.getClustersUnderDatacenter(this.vcenterDatacenter);
                        }
                        if (this.dataService.vc2ContentLibs.indexOf(this.vcenterContentSeLibrary) === -1) {
                        } else {
                            this.formGroup.get('vcenterContentSeLibrary').setValue(this.vcenterContentSeLibrary);
                            if(this.vcenterContentSeLibrary === 'CREATE NEW') this.onContentLibraryChange();
                        }
                    }
                } else if (data.responseType === 'ERROR') {
                    this.errorNotification = 'Fetch Resources: ' + data.msg;
                }
            } else {
            this.errorNotification = 'Fetch Resources: Some Error Occurred while Fetching Resources.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
            this.errorNotification = 'Fetch Resources: ' + error.msg;
            } else {
            this.errorNotification = 'Fetch Resources: Some Error Occurred while Fetching Resources. Please verify vCenter credentials.';
            }
        });
    }

    /**
     * @method onDatacenterChange
     * @desc This method is called anytime the Datacenter value is modified from the UI template
     * @desc It will update the list of clusters and datastores in case a new datacenter is selected
     */
     onDatacenterChange() {
        if (this.formGroup.get('vcenterDatacenter').valid && this.formGroup.get('vcenterDatacenter').value !== '') {
            this.getClustersUnderDatacenter(this.formGroup.get('vcenterDatacenter').value);
        }
    }

    getClustersUnderDatacenter(datacenter: string) {
        let vCenterData = {
            "vcenterAddress": "",
            "vcenterSsoUser": "",
            "vcenterSsoPasswordBase64": "",
            "vcenterDatacenter": datacenter,
        };

        this.dataService.currentVcenterAddressCloud.subscribe((address) => vCenterData['vcenterAddress'] = address);
        this.dataService.currentVcenterSsoUserCloud.subscribe((user) => vCenterData['vcenterSsoUser'] = user);
        this.dataService.currentVcenterSsoPasswordBase64Cloud.subscribe((password) => vCenterData['vcenterSsoPasswordBase64'] = password);

        this.apiClient.getClustersUnderDatacenterVsphere1('vcd', vCenterData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.vc2Clusters = data.CLUSTERS;
                    if (this.uploadStatus) {
                        if (this.vcenterCluster !== '') {
                            if (this.dataService.vc2Clusters.indexOf(this.vcenterCluster) !== -1) {
                                this.formGroup.get('vcenterCluster').setValue(this.vcenterCluster);
                            }
                        }
                    }
                    this.getDatastoresUnderDatacenter(datacenter);
                    this.errorNotification = null;
                } else if (data.responseType === 'ERROR') {
                    this.errorNotification = 'Fetch Clusters: ' + data.msg;
                }
            } else {
                this.errorNotification = 'Fetch Clusters: Some error occurred while listing Clusters under datacenter - ' + datacenter;
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.errorNotification = 'Fetch Clusters: ' + error.msg;
            } else {
                this.errorNotification = 'Fetch Clusters: Some error occurred while listing Clusters under datacenter - ' + datacenter;
            }
        });
    }

    getDatastoresUnderDatacenter(datacenter: string) {
        //####### REMOVE_ME ##########
        // this.datastores = ['datastore-1', 'datastore-2'];
        // this.formGroup.get('vcenterDatastore').enable();
        // this.fetchDatastore = true;
        // if (this.uploadStatus) {
        //     if (this.vcenterDatastore !== '') {
        //         if (this.datastores.indexOf(this.vcenterDatastore) !== -1) {
        //             this.formGroup.get('vcenterDatastore').setValue(this.vcenterDatastore);
        //         }
        //     }
        // }        
        // return;
        //####### REMOVE_ME ##########
        let vCenterData = {
            "vcenterAddress": "",
            "vcenterSsoUser": "",
            "vcenterSsoPasswordBase64": "",
            "vcenterDatacenter": datacenter,
        };

        this.dataService.currentVcenterAddressCloud.subscribe((address) => vCenterData['vcenterAddress'] = address);
        this.dataService.currentVcenterSsoUserCloud.subscribe((user) => vCenterData['vcenterSsoUser'] = user);
        this.dataService.currentVcenterSsoPasswordBase64Cloud.subscribe((password) => vCenterData['vcenterSsoPasswordBase64'] = password);

        this.apiClient.getDatastoresUnderDatacenterVsphere1('vcd', vCenterData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.vc2Datastores = data.DATASTORES;
                    if (this.uploadStatus) {
                        if (this.vcenterDatastore !== '') {
                            if (this.dataService.vc2Datastores.indexOf(this.vcenterDatastore) !== -1) {
                                this.formGroup.get('vcenterDatastore').setValue(this.vcenterDatastore);
                            }
                        }
                    }
                    this.errorNotification = null;
                } else if (data.responseType === 'ERROR') {
                    this.errorNotification = 'Fetch Datastores: ' + data.msg;
                }
            } else {
                this.errorNotification = 'Fetch Datastores: Some error occurred while listing Datastores under datacenter - ' + datacenter;
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.errorNotification = 'Fetch Datastores: ' + error.msg;
            } else {
                this.errorNotification = 'Fetch Datastores: Some error occurred while listing Datastores under datacenter - ' + datacenter;
            }
        });
    }


    public onContentLibraryChange() {
        if(this.formGroup.get('vcenterContentSeLibrary').valid) {
            if(this.formGroup.get('vcenterContentSeLibrary').value !== '') {
                if(this.formGroup.get('vcenterContentSeLibrary').value === 'CREATE NEW') {
                    this.resurrectField('newVcenterContentSeLibrary', [
                        Validators.required, this.validationService.noWhitespaceOnEnds(),
                    ], this.formGroup.get('newVcenterContentSeLibrary').value);
                } else {
                    ['newVcenterContentSeLibrary'].forEach((field) => {
                        this.disarmField(field, true);
                    });
                }
            }
        }
    }

    public onServiceEngineGroupVcdDisplayNameChange() {
        if(!this.formGroup.get('createSeGroup').value) {
            if(this.formGroup.get('serviceEngineGroupVcdDisplayName').value === 'IMPORT TO VCD') {
                this.resurrectField('serviceEngineGroupVcdDisplayNameInput', [
                    Validators.required, this.validationService.noWhitespaceOnEnds(),
                ], this.formGroup.value['serviceEngineGroupVcdDisplayNameInput']);
                this.resurrectField('reservationType', [
                    Validators.required
                ], this.formGroup.get('reservationType').value)
            } else {
                ['serviceEngineGroupVcdDisplayNameInput', 'reservationType'].forEach((field) => this.disarmField(field, true));
            }
        }
    }

    public fetchServiceEngineGroupNamesFromALB() {
        let segData = {
            'deployAvi': this.dataService.aviGreenfield.toString(),
            'aviController01Ip': '',
            'aviClusterIp': '',
            'aviUsername': '',
            'aviPasswordBase64': '',
            'aviNsxCloudName': ''
        };

        if(this.dataService.aviGreenfield) {
            this.dataService.currentAviController01Ip.subscribe((ip1) => segData['aviController01Ip'] = ip1);
        } else {
            this.dataService.currentAviClusterIp.subscribe((ip) => segData['aviClusterIp'] = ip);
        }
        this.dataService.currentAviUsername.subscribe((user) => segData['aviUsername'] = user);
        this.dataService.currentAviPasswordBase64.subscribe((pass) => segData['aviPasswordBase64'] = pass);
        this.dataService.currentAviNsxCloudName.subscribe((cloudname) => segData['aviNsxCloudName'] = cloudname)

        this.apiClient.fetchServiceEngineGroupNamesFromALB('vcd', segData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.serviceEngineGroupnamesAlb = data.SEG_LIST_AVI;
                    this.dataService.serviceEngineGroupnameAlbErrorMessage = null;
                } else if (data.responseType === 'ERROR') {
                    this.dataService.serviceEngineGroupnameAlbErrorMessage = data.msg;
                }
            } else {
                this.dataService.serviceEngineGroupnameAlbErrorMessage = "Some error occurred while fetching Service Engine groups for the provided NSXT cloud";
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.serviceEngineGroupnameAlbErrorMessage = err.msg;
            } else {
                this.dataService.serviceEngineGroupnameAlbErrorMessage = "Some error occurred while fetching Service Engine groups for the provided NSXT cloud";
            }
        });
    }

    public fetchServiceEngineGroupNamesFromVCD() {
        let vcdData = {
            'vcdAddress': "",
            'vcdSysAdminUserName': "",
            'vcdSysAdminPasswordBase64': "",
        };
        this.dataService.currentVcdAddress.subscribe((address) => vcdData['vcdAddress'] = address);
        this.dataService.currentVcdUsername.subscribe((username) => vcdData['vcdSysAdminUserName'] = username);
        this.dataService.currentVcdPassword.subscribe((password) => vcdData['vcdSysAdminPasswordBase64'] = password);

        this.apiClient.fetchServiceEngineGroupNamesFromVCD('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.serviceEngineGroupVcdDisplayNames = data.SEG_VDC_LIST;
                    this.dataService.serviceEngineGroupVcdDisplayNameErrorMessage = null;

                } else if (data.responseType === 'ERROR') {
                    if (data.hasOwnProperty('msg')) {
                        this.dataService.serviceEngineGroupVcdDisplayNameErrorMessage = data.msg;
                    } else {
                        this.dataService.serviceEngineGroupVcdDisplayNameErrorMessage = 'Failed to fetch list service engine groups from VCD';
                    }
                }
            } else {
                this.dataService.serviceEngineGroupVcdDisplayNameErrorMessage = 'Failed to fetch list of service engine groups from VCD';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                // tslint:disable-next-line:max-line-length
                this.dataService.serviceEngineGroupVcdDisplayNameErrorMessage = err.msg;
            } else {
                this.dataService.serviceEngineGroupVcdDisplayNameErrorMessage = 'Failed to fetch list of service engine groups from VCD';
            }
        });
    }


    toggleImportSEG() {
        const importSegFields = [
            'vcenterDatacenter',
            'vcenterDatastore',
            'vcenterCluster',
            'vcenterContentSeLibrary',
        ];

        if(this.formGroup.get('createSeGroup').value) {
            this.dataService.createSeGroup = true;

            this.resurrectField('vcenterDatacenter', [
                Validators.required,
            ], this.formGroup.value['vcenterDatacenter']);

            this.resurrectField('vcenterCluster', [
                Validators.required,
            ], this.formGroup.value['vcenterCluster']);

            this.resurrectField('vcenterDatastore', [
                Validators.required,
            ], this.formGroup.value['vcenterDatastore']);

            this.resurrectField('vcenterContentSeLibrary', [
                Validators.required,
            ], this.formGroup.value['vcenterContentSeLibrary']);

            this.resurrectField('serviceEngineGroupName', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
            ], this.formGroup.value['serviceEngineGroupName']);

            this.resurrectField('serviceEngineGroupVcdDisplayName', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
            ], this.formGroup.value['serviceEngineGroupVcdDisplayName']);

            this.resurrectField('reservationType', [
                Validators.required,
            ], this.formGroup.value['reservationType']);
        } else {
            this.dataService.createSeGroup = false;
            this.resurrectField('serviceEngineGroupName', [
                Validators.required,
            ], this.formGroup.value['serviceEngineGroupName']);

            this.resurrectField('serviceEngineGroupVcdDisplayName', [
                Validators.required
            ], this.formGroup.value['serviceEngineGroupVcdDisplayName']);

            importSegFields.forEach((field) => this.disarmField(field, true));
        }
    }
}
   