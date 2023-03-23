#!/bin/bash

export vCenterAddress=$(cat /opt/vmware/arcas/src/vsphere-dvs-tkgs-wcp.json|jq -r '.envSpec.vcenterDetails.vcenterAddress')
export vcenterSsoUser=$(cat /opt/vmware/arcas/src/vsphere-dvs-tkgs-wcp.json|jq -r '.envSpec.vcenterDetails.vcenterSsoUser')
export vcenterSsoPassword=$(cat /opt/vmware/arcas/src/vsphere-dvs-tkgs-wcp.json|jq -r '.envSpec.vcenterDetails.vcenterSsoPasswordBase64'|base64 -d)
export vcenterDatastore=$(cat /opt/vmware/arcas/src/vsphere-dvs-tkgs-wcp.json|jq -r '.envSpec.vcenterDetails.vcenterDatastore')
export GOVC_URL=$(echo ${vcenterSsoUser}:${vcenterSsoPassword}@${vCenterAddress})
export PROXY_URL=$(cat /opt/vmware/arcas/src/vsphere-dvs-tkgs-wcp.json|jq -r '.tkgsComponentSpec.tkgServiceConfig.proxySpec.httpProxy')
export GOVC_INSECURE=1
# choose specific k8s version if needed
#declare -a k8svers=(v1.20 v1.21)

if ! command -v govc >/dev/null 2>&1 ; then
  echo "govc not installed. Exiting...."
  exit 1
fi
if ! command -v jq >/dev/null 2>&1 ; then
  echo "JQ not installed. Exiting...."
  exit 1
fi
if ! command -v wget >/dev/null 2>&1 ; then
  echo "wget not installed. Exiting...."
  exit 1
fi
echo "--------------------Begin Downloading------------------"
if [[ ${#k8svers[@]} == 0 ]]; then
    echo "NO specified k8s version"
    echo "will download everything."
    echo ""
fi
if [[ ${#k8svers[@]} > 0 ]]; then
    echo "Specific k8s version"
    echo "will download : " "${k8svers[@]}"
    echo ""
fi

wget -e http_proxy=${PROXY_URL} -e https_proxy=${PROXY_URL} --no-check-certificate -q --show-progress --no-parent -r -nH --cut-dirs=2 --reject="index.html*" https://wp-content.vmware.com/v2/latest/items.json
tkgrimages=$(cat ./items.json |jq -r '.items[].name')
for tkgrimage in $tkgrimages
do
    if [[ ${#k8svers[@]} == 0 ]]; then
        echo "Downloading..." $tkgrimage
        wget -e http_proxy=${PROXY_URL} -e https_proxy=${PROXY_URL} --no-check-certificate -q --show-progress --no-parent -r -nH --cut-dirs=2 --reject="index.html*" https://wp-content.vmware.com/v2/latest/${tkgrimage}/
        echo "Compressing files..."
        tar -cvzf ${tkgrimage}.tar.gz ${tkgrimage}
        echo "Compress finished..."
        echo "Cleaning up..."    
        [ -d "${tkgrimage}" ] && rm -rf ${tkgrimage}
        echo " "
        echo " "
    fi
    if [[ ${#k8svers[@]} > 0 ]]; then
        for k8sver in "${k8svers[@]}"
        do
            if [[ $tkgrimage =~ "${k8sver}" ]]; then
                echo "Downloading..." $tkgrimage
                wget -e http_proxy=${PROXY_URL} -e https_proxy=${PROXY_URL} --no-check-certificate -q --show-progress --no-parent -r -nH --cut-dirs=2 --reject="index.html*" https://wp-content.vmware.com/v2/latest/${tkgrimage}/
                echo "Compressing files..."
                tar -cvzf ${tkgrimage}.tar.gz ${tkgrimage}
                echo "Compress finished..."
                echo "Cleaning up..."    
                [ -d "${tkgrimage}" ] && rm -rf ${tkgrimage}
                echo " "
                echo " "
            fi
        done
    fi

done

echo "--------------------Done Downloading------------------"
echo ""
echo "--------------------Checking Content Library------------------"
echo ""
contentlibraries=( $(govc library.ls) )
if [[ "${contentlibraries[*]}" =~ "SubscribedAutomation-Lib" ]]; then
    echo "Content Library called 'SubscribedAutomation-Lib' is already created."
    echo "will not create it again."
fi

if [[ ! "${contentlibraries[*]}" =~ "SubscribedAutomation-Lib" ]]; then
    echo "Content Library called 'SubscribedAutomation-Lib' is NOT created."
    echo "Need to create it with datastore."
    govc library.create -ds=$vcenterDatastore SubscribedAutomation-Lib
    echo "Library created..."
fi
echo "--------------------Checking Content Library------------------"
echo ""

echo ""
echo "--------------------Begin Importing------------------"

for dltkgrimage in $(ls|grep tar.gz)
do
    echo "Extracting ..." $dltkgrimage
    tar -xvf ${dltkgrimage}
    tkr=${dltkgrimage%".tar.gz"}
    echo "Uploading... " $tkr
    cd $tkr
    ovaname=photon-ova.ovf
    if [[ $tkr == *"ubuntu"* ]]; then
    ovaname=ubuntu-ova.ovf
    fi
    govc library.import -k=true -m=true -n ${tkr} SubscribedAutomation-Lib $ovaname
    echo "Upload finished."
    cd ..
    [ -d "${tkr}" ] && rm -rf ${tkr}
    echo ""
done
echo "--------------------Done Importing------------------"