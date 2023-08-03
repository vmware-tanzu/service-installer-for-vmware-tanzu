ARG IMAGEBUILDER_TAG=v0.1.11_vmware.3
ARG REGISTRY=projects.registry.vmware.com
FROM ${REGISTRY}/tkg/image-builder:${IMAGEBUILDER_TAG}

COPY --chown=imagebuilder:imagebuilder roles roles/
COPY --chown=imagebuilder:imagebuilder packer packer/
COPY --chown=imagebuilder:imagebuilder Makefile Makefile
COPY --chown=imagebuilder:imagebuilder playbook.yml playbook.yml
COPY --chown=imagebuilder:imagebuilder tkg-imagebuilder/tanzu.tar roles/bootstrap/files/packages/
COPY --chown=imagebuilder:imagebuilder tkg-imagebuilder/kind roles/bootstrap/files/bin
COPY --chown=imagebuilder:imagebuilder tkg-imagebuilder/yq roles/bootstrap/files/bin
COPY --chown=imagebuilder:imagebuilder tkg-imagebuilder/kubectl.gz roles/bootstrap/files/bin
RUN  gunzip -c roles/bootstrap/files/bin/kubectl.gz > roles/bootstrap/files/bin/kubectl && rm roles/bootstrap/files/bin/kubectl.gz

