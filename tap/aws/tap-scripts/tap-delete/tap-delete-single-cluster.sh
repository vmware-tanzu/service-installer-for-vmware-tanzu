# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

#delete all tap packages 
tanzu package installed delete tap -n tap-install --yes


#delete tap repo 
tanzu package repository delete tanzu-tap-repository  --namespace tap-install --yes

kubectl delete secret -n tap-install --all

#uninstall tanzu essentials
cd $HOME/tanzu-cluster-essentials
./uninstall.sh --yes

kubectl delete ns tap-install

# you can uncomment and execute below commands to delete tanzu cli from terminal
sudo rm -rf $HOME/tanzu/cli        # Remove previously downloaded cli files
sudo rm /usr/local/bin/tanzu  # Remove CLI binary (executable)
sudo rm -rf ~/.config/tanzu/       # current location # Remove config directory
sudo rm -rf ~/.tanzu/              # old location # Remove config directory
sudo rm -rf ~/.cache/tanzu         # remove cached catalog.yaml
sudo rm -rf ~/Library/Application\ Support/tanzu-cli/* # Remove plug-ins

echo "tanuz cli and tap packages deleted"