
FROM vdm-bitnami-docker-local.artifactory.eng.vmware.com/photon3:20200710
ADD . /arcas
ARG arcas_version
WORKDIR /arcas


RUN tdnf install python3 python3-pip -y && pip3 install -U setuptools==65.7.0
RUN pip3 install pythonping
RUN pip3 install dig
RUN tdnf install tar -y
RUN tdnf  install gzip -y
RUN tdnf  install docker -y
RUN tdnf  install coreutils -y
RUN curl -L -o - "https://github.com/vmware/govmomi/releases/latest/download/govc_$(uname -s)_$(uname -m).tar.gz" | tar -C /usr/local/bin -xvzf - govc
RUN yum install sudo -y
RUN yum install ssh* -y
RUN yum install unzip -y


RUN mv /arcas/photon/rpm/tools/docker-config/services /etc/
RUN mv /arcas/photon/rpm/tools/kind /usr/local/bin/kind && chmod +x /usr/local/bin/kind

RUN mv /arcas/photon/rpm/tools/terraform /usr/local/bin/terraform && chmod +x /usr/local/bin/terraform

RUN gunzip /arcas/photon/rpm/tools/k9s*.tar.gz && tar -xvf /arcas/photon/rpm/tools/k9s*.tar --directory /root && cd /root && mv /root/k9s /usr/local/bin/k9s && chmod +x /usr/local/bin/k9s
RUN rm /arcas/photon/rpm/tools/k9s*.tar

RUN gunzip /arcas/photon/rpm/tools/kubectx*.tar.gz && tar -xvf /arcas/photon/rpm/tools/kubectx*.tar --directory /root && cd /root && mv /root/kubectx /usr/local/bin/kubectx && chmod +x /usr/local/bin/kubectx
RUN rm /arcas/photon/rpm/tools/kubectx*.tar


RUN gunzip /arcas/photon/rpm/tools/fzf*.tar.gz && tar -xvf /arcas/photon/rpm/tools/fzf*.tar --directory /root && cd /root && mv /root/fzf /usr/local/bin/fzf && chmod +x /usr/local/bin/fzf
RUN rm /arcas/photon/rpm/tools/fzf*.tar

RUN gunzip /arcas/photon/rpm/tools/helm*.tar.gz && tar -xvf /arcas/photon/rpm/tools/helm*.tar --directory /root && cd /root && mv /root/linux-amd64/helm /usr/local/bin/helm && chmod +x /usr/local/bin/helm
RUN rm /arcas/photon/rpm/tools/helm*.tar

RUN gunzip /arcas/photon/rpm/tools/velero*.tar.gz && tar -xvf /arcas/photon/rpm/tools/velero*.tar --directory /root && cd /root && mv /root/velero-*-linux-amd64/velero /usr/local/bin/velero && chmod +x /usr/local/bin/velero
RUN rm /arcas/photon/rpm/tools/velero*.tar


RUN gunzip /arcas/photon/rpm/tools/octant*.tar.gz && tar -xvf /arcas/photon/rpm/tools/octant*.tar --directory /root && cd /root && mv /root/octant_*_Linux-64bit/octant /usr/local/bin/octant && chmod +x /usr/local/bin/octant
RUN rm /arcas/photon/rpm/tools/octant*.tar

RUN mv /arcas/photon/rpm/tools/stern_linux_amd64 /usr/local/bin/stern && sudo chmod +x /usr/local/bin/stern


RUN cp /arcas/photon/rpm/tools/docker-compose-Linux-x86_64 /usr/local/bin/docker-compose && sudo chmod ugo+x /usr/local/bin/docker-compose
RUN rm  /arcas/photon/rpm/tools/docker-compose-Linux-x86_64

RUN cp /arcas/photon/rpm/tools/pinniped-cli-linux-amd64 /usr/local/bin/pinniped && sudo chmod +x /usr/local/bin/pinniped
RUN rm /arcas/photon/rpm/tools/pinniped-cli-linux-amd64

RUN cp /arcas/photon/rpm/tools/jq-linux64 /usr/local/bin/jq && sudo chmod +x /usr/local/bin/jq
RUN rm /arcas/photon/rpm/tools/jq-linux64








RUN tar -xvzf /arcas/photon/rpm/tools/tanzu-cli-bundle-linux-amd64.tar.gz --directory /root && cd /root && install /root/cli/core/*/tanzu-core-linux_amd64 /usr/local/bin/tanzu && gunzip -f /root/cli/ytt-linux-amd64-*.gz && chmod ugo+x /root/cli/ytt-linux-amd64-* && mv /root/cli/ytt-linux-amd64-* /usr/local/bin/ytt && gunzip -f /root/cli/kapp-linux-amd64-*.gz  && chmod ugo+x /root/cli/kapp-linux-amd64-* && mv /root/cli/kapp-linux-amd64-* /usr/local/bin/kapp  && gunzip -f /root/cli/kbld-linux-amd64-*.gz  && chmod ugo+x /root/cli/kbld-linux-amd64-* && mv /root/cli/kbld-linux-amd64-* /usr/local/bin/kbld && gunzip -f /root/cli/imgpkg-linux-amd64-*.gz  && chmod ugo+x /root/cli/imgpkg-linux-amd64-* && mv /root/cli/imgpkg-linux-amd64-* /usr/local/bin/imgpkg
RUN tar -xvzf /arcas/photon/rpm/tools/yq_linux_amd64.tar.gz && chmod ugo+x ./yq_linux_amd64  && mv ./yq_linux_amd64 /usr/local/bin/yq && chmod +x /arcas/photon/rpm/tools/export_env.sh && source /arcas/photon/rpm/tools/export_env.sh && cd /root
RUN rm /arcas/photon/rpm/tools/tanzu-cli-bundle-linux-amd64.tar.gz  && rm /arcas/photon/rpm/tools/yq_linux_amd64.tar.gz
RUN /usr/local/bin/tanzu plugin install  all && cp /arcas/photon/rpm/tools/config/tanzu/tkg/compatibility/tkg-compatibility.yaml /root/.config/tanzu/tkg/compatibility/ && cp -r /arcas/photon/rpm/tools/config/tanzu/tkg/bom /root/.config/tanzu/tkg/

RUN cp /arcas/photon/rpm/tools/tmc /usr/local/bin/tmc && sudo chmod ugo+x /usr/local/bin/tmc


RUN gunzip -f /arcas/photon/rpm/tools/kubectl-linux-v*.gz && mv /arcas/photon/rpm/tools/kubectl-linux-v* /usr/local/bin/kubectl && chmod +x /usr/local/bin/kubectl



RUN gunzip /arcas/photon/rpm/tools/kube-ps1-*.tar.gz && tar -xvf /arcas/photon/rpm/tools/kube-ps1-*.tar --directory /root

RUN rm /arcas/photon/rpm/tools/kube-ps1-*.tar



RUN pip3 install -r requirements.txt
RUN pip3 install -e .
WORKDIR /arcas/src
CMD [ "python3", "/arcas/src/python_server.py" ]
EXPOSE 5000
ENV AM_I_IN_A_DOCKER_CONTAINER Yes
