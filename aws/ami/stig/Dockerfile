ARG IMAGEBUILDER_TAG=v0.1.11_vmware.3
ARG REGISTRY=projects.registry.vmware.com
FROM ${REGISTRY}/tkg/image-builder:${IMAGEBUILDER_TAG}

COPY --chown=imagebuilder:imagebuilder patch/aws.yml ansible/roles/providers/tasks/aws.yml
COPY --chown=imagebuilder:imagebuilder patch/packer.json packer/ami/packer.json
COPY --chown=imagebuilder:imagebuilder patch/packer_azure.json packer/azure/packer.json
COPY --chown=imagebuilder:imagebuilder tkg-imagebuilder/tkg /home/imagebuilder/tkg
COPY --chown=imagebuilder:imagebuilder tkg-imagebuilder/tkg.json /home/imagebuilder/tkg.json
COPY --chown=imagebuilder:imagebuilder roles/canonical-ubuntu-18.04-lts-stig-hardening /home/imagebuilder/canonical-ubuntu-18.04-lts-stig-hardening
