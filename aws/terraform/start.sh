#! /bin/bash
set -o errexit
set -o allexport
if [[ "$base_os_family" == "air-gapped-amazon-linux-2" ]]; then
  bash /home/startup-airgapped-amazon-linux2.sh
elif [[ "$base_os_family" == "non-airgapped-ubuntu" ]]; then
  bash /home/startup-non-airgap-ubuntu-bootstrap.sh
else
  bash /home/startup-airgapped-ubuntu.sh
fi