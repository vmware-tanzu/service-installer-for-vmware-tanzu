
export interface NodeType {
    id: string;
    name: string;
}

export const vSphereNodeTypes: Array<NodeType> = [
    {
        id: 'custom',
        name: 'custom'
    },
    {
        id: 'medium',
        name: 'medium (CPU: 2, RAM: 8 GB, Disk: 40 GB)'
    },
    {
        id: 'large',
        name: 'large (CPU: 4, ram: 16 GB, Disk: 40 GB)'
    },
    {
        id: 'extra-large',
        name: 'extra-large (CPU: 8, ram: 32 GB, Disk: 80 GB)'
    },
];

export const toNodeTypes: Array<NodeType> = [
    {
        id: 'custom',
        name: 'custom'
    },
    {
        id: 'large',
        name: 'large (CPU: 4, RAM: 16 GB, Disk: 40 GB)'
    },
    {
        id: 'extra-large',
        name: 'extra-large (CPU: 8, RAM: 32 GB, Disk: 80 GB)'
    },
];

export const tkgsControlPlaneNodes: Array<NodeType> = [
    {
        id: 'TINY',
        name: 'TINY (CPU: 2, RAM: 8 GB, Disk: 32 GB)'
    },
    {
        id: 'SMALL',
        name: 'SMALL (CPU: 4, RAM: 16 GB, Disk: 32 GB)'
    },
    {
        id: 'MEDIUM',
        name: 'MEDIUM (CPU: 8, RAM: 24 GB, Disk: 32 GB)'
    },
    {
        id: 'LARGE',
        name: 'LARGE (CPU: 16, RAM: 32 GB, Disk: 32 GB)'
    },
];

export const sharedServiceNodeTypes: Array<NodeType> = [
    {
        id: 'custom',
        name: 'custom'
    },
    {
        id: 'medium',
        name: 'medium (CPU: 2, RAM: 8 GB, Disk: 40 GB)'
    },
    {
        id: 'large',
        name: 'large (CPU: 4, RAM: 16 GB, Disk: 40 GB)'
    },
    {
        id: 'extra-large',
        name: 'extra-large (CPU: 8, RAM: 32 GB, Disk: 80 GB)'
    },
];

export const kubernetesOvas: Array<NodeType> = [
    {
        id: 'photon',
        name: 'Photon v3 Kubernetes v1.21.2 OVA'
    },
    {
        id: 'ubuntu',
        name: 'Ubuntu 2004 Kubernetes v1.21.2 OVA'
    }
];

export const aviSize: Array<NodeType> = [
    {
        id: 'essentials',
        name: 'ESSENTIALS (CPU: 4, RAM: 12GB)'
    },
    {
        id: 'small',
        name: 'SMALL (CPU: 8, RAM: 24GB)'
    },
    {
        id: 'medium',
        name: 'MEDIUM (CPU: 16, RAM: 32GB)'
    },
    {
        id: 'large',
        name: 'LARGE (CPU: 24, RAM: 48GB)'
    },
];
