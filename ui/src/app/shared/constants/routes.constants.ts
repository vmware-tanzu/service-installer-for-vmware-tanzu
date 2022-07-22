export interface Routes {
    [key: string]: string;
}

export interface Fragment {
    [key: string]: string;
}

export const APP_ROUTES: Routes = {
    LANDING: '/ui',
    VSPHERE_WITH_KUBERNETES: '/ui/vsphere-with-kubernetes',
    INCOMPATIBLE: '/ui/incompatible',
    WIZARD_MGMT_CLUSTER: '/ui/wizard',
    AWS_WIZARD: '/ui/aws/wizard',
    AZURE_WIZARD: '/ui/azure/wizard',
    DOCKER_WIZARD: '/ui/docker/wizard',
    WIZARD_PROGRESS: '/ui/deploy-progress',
    VSPHERE_UPLOAD_PANEL: '/ui/upload',
    VMC_UPLOAD_PANEL: '/ui/vmc-upload',
    VMC_WIZARD: '/ui/vmc-wizard',
    VSPHERE_NSXT_UPLOAD_PANEL: '/ui/vsphere-nsxt-upload',
    VSPHERE_NSXT_WIZARD: '/ui/vsphere-nsxt',
    TKGS_VSPHERE_WIZARD: '/ui/vsphere-tkgs',
};
