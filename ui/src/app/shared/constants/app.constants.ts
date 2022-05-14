export interface Providers {
    [key: string]: string;
}

export const PROVIDERS: Providers = {
    VSPHERE: 'vsphere',
    AWS: 'aws',
    AZURE: 'azure',
    DOCKER: 'docker',
    VMC: 'vmc',
    VSPHERE_NSXT: 'vsphere-nsxt',
    TKGM: 'tkgm',
    TKGS: 'tkgs',
    TKGS_WCP: 'wcp',
    TKGS_NAMESPACE: 'namespace',
};

export const IAAS_DEFAULT_CIDRS = {
    CLUSTER_SVC_CIDR: '100.64.0.0/13',
    CLUSTER_POD_CIDR: '100.96.0.0/11'
};
