FROM photon:latest

RUN tdnf install wget -y
RUN tdnf install jq coreutils -y
RUN tdnf install git -y
RUN tdnf install openssh -y
RUN tdnf install docker -y
RUN tdnf install vim -y
RUN tdnf install unzip -y
RUN tdnf install sudo -y


RUN tdnf install python3-pip -y && pip3 install -U setuptools && pip3 install avisdk pydantic pyVmomi pyVim PyYAML paramiko jinja2 click retry iptools tqdm ruamel.yaml
RUN curl -L -o - "https://github.com/vmware/govmomi/releases/latest/download/govc_$(uname -s)_$(uname -m).tar.gz" | tar -C /usr/local/bin -xvzf - govc


ENV LOG_PATH=/tmp/deploy.log
ENV LOG_LEVEL=DEBUG


RUN mkdir /tanzu
WORKDIR /tanzu

# install yq
COPY tanzu_pkg/yq_linux_amd64.tar.gz /tanzu
RUN tar -xvf /tanzu/yq_linux_amd64.tar.gz /usr/local/bin/yq

# install tanzu cli
COPY tanzu_pkg/tanzu-cli-bundle-linux-amd64.tar.gz /tanzu
RUN tar -xvf /tanzu/tanzu-cli-bundle-linux-amd64.tar.gz && \
     install cli/core/v0.11.6/tanzu-core-linux_amd64 /usr/local/bin/tanzu


# install kubectl cli
COPY tanzu_pkg/kubectl-linux-v*-vmware.1.gz /tanzu
RUN gunzip kubectl-linux-v*vmware.1.gz && \
     install kubectl-linux-v*vmware.1  /usr/local/bin/kubectl


# install plugins
RUN tanzu plugin clean && \
    tanzu plugin sync && \
    tanzu plugin list

# install ytt
RUN gunzip cli/ytt-linux-amd64-v0.37.0+vmware.1.gz && \
    sudo chmod ugo+x cli/ytt-linux-amd64-v0.37.0+vmware.1 && \
    sudo mv cli/ytt-linux-amd64-v0.37.0+vmware.1 /usr/local/bin/ytt

# install kapp
RUN gunzip cli/kapp-linux-amd64-v0.42.0+vmware.2.gz && \
    sudo chmod ugo+x cli/kapp-linux-amd64-v0.42.0+vmware.2 && \
    sudo mv cli/kapp-linux-amd64-v0.42.0+vmware.2 /usr/local/bin/kapp

# install kbld
RUN gunzip cli/kbld-linux-amd64-v0.31.0+vmware.1.gz && \
    sudo chmod ugo+x cli/kbld-linux-amd64-v0.31.0+vmware.1 && \
    sudo mv cli/kbld-linux-amd64-v0.31.0+vmware.1 /usr/local/bin/kbld

# install imgpkg
RUN gunzip cli/imgpkg-linux-amd64-v0.22.0+vmware.1.gz && \
    sudo chmod ugo+x cli/imgpkg-linux-amd64-v0.22.0+vmware.1 && \
    sudo mv cli/imgpkg-linux-amd64-v0.22.0+vmware.1 /usr/local/bin/imgpkg

# remove unwanted packages
RUN rm -f tanzu-cli-bundle-linux-amd64.tar && \
    rm -rf cli && \
    rm -f kubectl-linux-v1.22.9+vmware.1 && \
    rm -f tkg-standard-repo-v1.5.4.tar.gz

