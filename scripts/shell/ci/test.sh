#!/bin/bash
# color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

spec_file=$(ls specs/gitlab/${CI_PROJECT_NAMESPACE}.* | head -1)
if [ -f $spec_file ] || [ -s $spec_file ]; then
    CMD="java -jar iris-ci-root/iris-ci-cli/target/iris-ci-cli-0.0.1-SNAPSHOT-spring-boot.jar deploy-all -s=${spec_file} \
    -u=$(./buildweb/get_abs_url.py service-installer-for-VMware-Tanzu build-info.json ova) \
    -t=specs/all_tests.json -j"
    echo -e "${GREEN}Command: ${CMD}${NC}"
    $CMD
else
    echo "${RED}SPEC FILE ABSENT.${NC} Refer https://confluence.eng.vmware.com/display/IRISDEV/CI"
    exit 1
fi
