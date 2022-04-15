#!/bin/bash

export VMWARE_ROOT=content/opt/vmware
export ARCAS_ROOT=${VMWARE_ROOT}/arcas
export ARCAS_TEKTON=${VMWARE_ROOT}/arcas_tekton
export ARCAS_ROOT_TOOLS=${ARCAS_ROOT}/tools
export ARCAS_ROOT_IMAGES=${ARCAS_ROOT}/images
export ARCAS_ROOT_WEBLOGIC=${ARCAS_ROOT_TOOLS}/weblogic
export ARCAS_ROOT_CSA=${ARCAS_ROOT_TOOLS}/csa
export ARCAS_WL_PATCHES=${ARCAS_ROOT_TOOLS}/patches
export ARCAS_ROOT_JDK=${ARCAS_ROOT_TOOLS}/jdk
export SERVICE_DIR=content/etc/systemd/system
export NGINX_CONFIG_DIR=content/opt/vmware/arcas/arcas-ui-service/nginx

mkdir -p ${VMWARE_ROOT}/
mkdir -p ${ARCAS_ROOT}/
mkdir -p ${ARCAS_TEKTON}/
mkdir -p ${SERVICE_DIR}/
mkdir -p ${ARCAS_ROOT_WEBLOGIC}/
mkdir -p ${ARCAS_ROOT_CSA}/
mkdir -p ${ARCAS_ROOT_JDK}/
mkdir -p ${ARCAS_WL_PATCHES}/
mkdir -p ${NGINX_CONFIG_DIR}/

echo "Running command: cp -rf ../bin ${ARCAS_ROOT}/"
cp -rf ../bin ${ARCAS_ROOT}/

echo "Running command: cp -rf ../../ui/dist/arcas-ui ${VMWARE_ROOT}/"
cp -rf ../../ui/dist/arcas-ui ${VMWARE_ROOT}

echo "Running command: cp tools/docker-compose-Linux-x86_64 ${ARCAS_ROOT_TOOLS}/"
cp tools/docker-compose-Linux-x86_64 ${ARCAS_ROOT_TOOLS}/

mv arcas-ui.tar ${VMWARE_ROOT}

echo "Running command: cp tools/kind ${ARCAS_ROOT_TOOLS}/"
cp tools/kind ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/tmc ${ARCAS_ROOT_TOOLS}/"
cp tools/tmc ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/kube-ps1-0.7.0.tar.gz ${ARCAS_ROOT_TOOLS}/"
cp tools/kube-ps1-0.7.0.tar.gz ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/pinniped-cli-linux-amd64 ${ARCAS_ROOT_TOOLS}/"
cp tools/pinniped-cli-linux-amd64 ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/k9s_Linux_x86_64.tar.gz ${ARCAS_ROOT_TOOLS}/"
cp tools/k9s_Linux_x86_64.tar.gz ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/helm-v3.8.1-linux-amd64.tar.gz ${ARCAS_ROOT_TOOLS}/"
cp tools/helm-v3.8.1-linux-amd64.tar.gz ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/velero-v1.7.2-linux-amd64.tar.gz ${ARCAS_ROOT_TOOLS}/"
cp tools/velero-v1.7.2-linux-amd64.tar.gz ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/octant_0.25.1_Linux-64bit.tar.gz ${ARCAS_ROOT_TOOLS}/"
cp tools/octant_0.25.1_Linux-64bit.tar.gz ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/kubectx_v0.9.4_linux_x86_64.tar.gz ${ARCAS_ROOT_TOOLS}/"
cp tools/kubectx_v0.9.4_linux_x86_64.tar.gz ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/fzf-0.29.0-linux_amd64.tar.gz ${ARCAS_ROOT_TOOLS}/"
cp tools/fzf-0.29.0-linux_amd64.tar.gz ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/jq-linux64 ${ARCAS_ROOT_TOOLS}/"
cp tools/jq-linux64 ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/flask ${ARCAS_ROOT_TOOLS}/"
cp -r tools/flask ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/flaskCross ${ARCAS_ROOT_TOOLS}/"
cp -r tools/flaskCross ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/flaskRest ${ARCAS_ROOT_TOOLS}/"
cp -r tools/flaskRest ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/ntplib ${ARCAS_ROOT_TOOLS}/"
cp -r tools/ntplib ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/raumel ${ARCAS_ROOT_TOOLS}/"
cp -r tools/raumel ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/tqdm ${ARCAS_ROOT_TOOLS}/"
cp -r tools/tqdm ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/waitress ${ARCAS_ROOT_TOOLS}/"
cp -r tools/waitress ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/pydenttic ${ARCAS_ROOT_TOOLS}/"
cp -r tools/pydentic ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/tanzu-cli-bundle-linux-amd64.tar.gz ${ARCAS_ROOT_TOOLS}/"
cp tools/tanzu-cli-bundle-linux-amd64.tar.gz ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/tkn_0.22.0_Linux_x86_64.tar.gz ${ARCAS_ROOT_TOOLS}/"
cp tools/tkn_0.22.0_Linux_x86_64.tar.gz ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/kubectl-linux-v1.22.5+vmware.1.gz ${ARCAS_ROOT_TOOLS}/"
cp tools/kubectl-linux-v1.22.5+vmware.1.gz ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/yq_linux_amd64.tar.gz ${ARCAS_ROOT_TOOLS}/"
cp tools/yq_linux_amd64.tar.gz ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/govc_linux_amd64.gz ${ARCAS_ROOT_TOOLS}/"
cp tools/govc_linux_amd64.gz ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/export_env.sh ${ARCAS_ROOT_TOOLS}/"
cp tools/export_env.sh ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/arcas.service ${ARCAS_ROOT_TOOLS}/"
cp tools/arcas.service ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/arcas-ui.service ${ARCAS_ROOT_TOOLS}/"
cp tools/arcas-ui.service ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/arcas-ui.service ${ARCAS_ROOT_TOOLS}/"
cp tools/arcas-ui.service ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/arcas-ui-service.conf ${ARCAS_ROOT_TOOLS}/"
cp tools/arcas-ui-service.conf ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp tools/config ${ARCAS_ROOT_TOOLS}/"
cp -r tools/config ${ARCAS_ROOT_TOOLS}/

echo "Running command: cp ../../src ${ARCAS_ROOT}/"
cp -r ../../src ${ARCAS_ROOT}/

echo "Running command: cp ../../tekton ${ARCAS_ROOT}/"
cp -r ../../tekton ${ARCAS_ROOT}/

echo "Running command: cp ../../azure ${ARCAS_ROOT}/"
cp -r ../../azure ${ARCAS_ROOT}/

echo "Running command: cp ../../aws ${ARCAS_ROOT}/"
cp -r ../../aws ${ARCAS_ROOT}/

echo "Running command: cp ../../ui/dist/arcas-ui.tar ${VMWARE_ROOT}/"
cp  ../../ui/dist/arcas-ui.tar ${VMWARE_ROOT}/

echo "Running command: cp ../../../arcas/setup.py ${ARCAS_ROOT}/"
cp ../../../arcas/setup.py ${ARCAS_ROOT}/

# Package RPM
chmod u+x mkpkg.sh

./mkpkg.sh -t rpm -c arcas-scripts-rpm.spec content
