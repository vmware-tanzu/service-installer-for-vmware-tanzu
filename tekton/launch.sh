#!/bin/bash
function usage() {
  echo "Usage: launch.sh [--create-cluster] [--deploy-dashboard] [<pipeline.yaml>,...]"
  echo ""
  echo "  Deploys Tekton and a pipeline onto a Kubernetes cluster (which this script can create as well)"
  echo ""
  echo "    --build_docker_image             Create docker tar image as per desired_state.yml version"
  echo "    --create-cluster [--airgapped]   Create a cluster, using kind. Pass --airgapped for airgapped environment"
  echo "    --deploy-dashboard  [--airgapped] Deploy the Tekton dashboard as well. Pass --airgapped for airgapped environment"
  echo "    --exec-day0         To trigger day0 pipline, bringup of TKGM"
  echo "    --exec-tkgs-day0    To trigger day0 pipline, bringup of TKGS"
  echo "    --load-upgrade-imgs To load images onto kind cluster, for upgrade pipeline"
  echo "    --exec-upgrade-mgmt To trigger upgrade of mgmt cluster"
  echo "    --exec-upgrade-all  To trigger upgrade of all clusters"
  echo "    <pipeline.yaml,...> The paths to Tekton pipeline files (can be a local files or URLs)"
  echo "    <pipeline.yaml,...> The paths to Tekton pipeline files (can be a local files or URLs)"
}
# USED ONLY FOR TEKTON AIRGAPPED ENVIRONMENT
AIRGAPPED="false"
TEKTON_DEPENDENCIES_DIR=$HOME"/tkn_utils_v0.40.2"
HARBOR_URL=$(cat values.yaml | grep harbor_url | awk '{print $2}')
HARBOR_REPO_PATH=$HARBOR_URL"/tekton_dep"
HARBOR_DIND_IMAGE_PATH=$HARBOR_REPO_PATH"/docker:dind"
HARBOR_KIND_IMAGE=$HARBOR_REPO_PATH"/kindest/node:v1.22.0"
AIRGAPPED_TEKTON_PIPELINE_FILE=$TEKTON_DEPENDENCIES_DIR"/release.yaml"                        # Fill absolute path of release.yaml file
AIRGAPPED_TEKTON_PIPELINE_DASHBOARD_FILE=$TEKTON_DEPENDENCIES_DIR"/release_dashboard.yaml"    # Fill absolute path of release_dashboard.yaml file
AIRGAPPED_TEKTON_PIPELINE_TRIGGERS_FILE=$TEKTON_DEPENDENCIES_DIR"/release_trigger.yaml"    # Fill absolute path of release_trigger.yaml file
AIRGAPPED_NGINX_INGRESS_FILE=$TEKTON_DEPENDENCIES_DIR"/nginx_deploy.yaml"
AIRGAPPED_TEKTON_POLLING_OPERATOR_FILE=$TEKTON_DEPENDENCIES_DIR"/release_polling_operator.yaml"
HARBOR_CERT_FILE="/etc/docker/certs.d/$HARBOR_URL/$HARBOR_URL.cert"
CA_CERT_FILE="/etc/docker/certs.d/$HARBOR_URL/ca.crt"
#### AIRGAPPED PARAMS ENDS ########

SIVT_DEFAULT_IMAGES="sivt_tekton:v"$(cat desired-state/desired-state.yml| grep tkg | head -1|awk '{print $2}'| sed 's/\.//g')
DEFAULT_IMAGES="docker:dind"
CLUSTER_IMAGE="kindest/node:v1.21.1"
UPGRADE_IMAGES="sivt_tekton:v"$(cat desired-state/desired-state.yml| grep tkg | head -1|awk '{print $2}'| sed 's/\.//g')

TARBALL_FILE_PATH=""
UPGRADE_TARBALL_FILE_PATH=""

CLUSTER_INIT_CONFIG_FILE="${CLUSTER_INIT_CONFIG_FILE:=./cluster_resources/kind-init-config.yaml}"
NGINX_INGRESS_FILE="${NGINX_INGRESS_FILE:=https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml}"

CLUSTER_NAME="${CLUSTER_NAME:=arcas-ci-cd-cluster}"   # The name of the cluster to create with Kind
CLUSTER_CONFIG_PATH="${CLUSTER_CONFIG_PATH:=./${CLUSTER_NAME}.yaml}"

TEKTON_DASHBOARD_VERSION="${TEKTON_DASHBOARD_VERSION:=v0.24.1}"
TEKTON_DASHBOARD_FILE="${TEKTON_DASHBOARD_FILE:=https://storage.googleapis.com/tekton-releases/dashboard/previous/${TEKTON_DASHBOARD_VERSION}/tekton-dashboard-release.yaml}"
TEKTON_PIPELINE_VERSION="${TEKTON_PIPELINE_VERSION:=v0.33.0}"
TEKTON_PIPELINE_FILE="${TEKTON_PIPELINE_FILE:=https://storage.googleapis.com/tekton-releases/pipeline/previous/${TEKTON_PIPELINE_VERSION}/release.yaml}"
TEKTON_TRIGGERS_VERSION="${TEKTON_TRIGGERS_VERSION:=v0.18.0}"
TEKTON_TRIGGERS_FILE="${TEKTON_TRIGGERS_FILE:=https://storage.googleapis.com/tekton-releases/triggers/previous/${TEKTON_TRIGGERS_VERSION}/release.yaml}"
TEKTON_DASHBOARD_ING_FILE="${TEKTON_DASHBOARD_ING_FILE:=./cluster_resources/tkn-dashboard-ing.yaml}"

function check_for_kind() {
  echo "Checking for kind..."
  if ! command -v kind &> /dev/null; then
    echo "kind not installed. Please install kind and try again." >&2
    return 1
  fi

  kind --version
  printf "Done\n\n"
}

function check_for_kubectl() {
  echo "Checking for kubectl..."
  if ! command -v kubectl &> /dev/null; then
    echo "kubectl not installed. Please install kubectl and try again." >&2
    return 1
  fi

  kubectl version --client
  printf "Done\n\n"
}

function check_for_tkn() {
  echo "Checking for tkn..."
  if ! command -v tkn &> /dev/null; then
    echo "tkn not installed. Please install the Tekton CLI and try again." >&2
    return 1
  fi

  tkn version
  printf "Done\n\n"
}


function docker_pull_imgs() {

  local img_list="$@"

  if ! docker login; then
    echo "Failed to login to dockerhub" >&2
    exit 1
    #return 1
  fi

  for i in $img_list
    do
      if ! docker pull $i; then
        echo "Failed to pull image:- $i" >&2
        exit 1
        #return 1
      fi
  done
}

function docker_pull_imgs_from_harbor() {

  local img_list="$@"

  if ! docker login ${HARBOR_URL}; then
    echo "Failed to login to harbor" >&2
    exit 1
    #return 1
  fi

  for i in $img_list
    do
      if ! docker pull $i; then
        echo "Failed to pull image:- $i" >&2
        exit 1
        #return 1
      fi
  done
}

function kind_load_tar_imgs() {

  local tar_list="$@"
    for i in $tar_list
      do
        if [ -f $i ]; then
          echo "Loading tarball image file:- $i...."
          if ! kind load image-archive $i --name $CLUSTER_NAME; then
            echo "failed to load tarball image file:- $i" >&2
          else
            echo "Successfully loaded tarball image file:- $i"
          fi
        else
            echo "Mentioned Tarball file ${TARBALL_FILE_PATH} is not found "
            exit 1
         fi
      done

}

function kind_load_docker_imgs() {

  local image_names="$@"

  for i in $image_names
    do
      if ! docker images $i; then
        echo "$i image is not present locally.." >&2
      fi

      echo "$i image is present locally..loading it to kind cluster"
      if ! kind load docker-image $i --name $CLUSTER_NAME; then
        echo "failed to load docker image :- $i" >&2
      else
         echo "Successfully loaded docker image :- $i"
      fi
    done
}

function load_cluster_images() {
  echo "Preparing loading of images..."
  LOAD_DEFAULT_IMG=false
  LOAD_TARBALL=false
  if [ -n "${TARBALL_FILE_PATH}" ]; then
    kind_load_tar_imgs $TARBALL_FILE_PATH
    LOAD_DEFAULT_IMG=true
  else
    echo "TARBALL_FILE_PATH variable is empty"
  fi
  if [ -n "${DEFAULT_IMAGES}" ]; then
      kind_load_docker_imgs $DEFAULT_IMAGES $SIVT_DEFAULT_IMAGES
      LOAD_TARBALL=true
  else
      echo "DEFAULT_IMAGES variable is empty"
  fi
  if [ "$LOAD_DEFAULT_IMG" == "false" ] && [ "$LOAD_TARBALL" == "false" ]; then
    echo "FAILED: Neither TARBALL_FILE_PATH NOR DEFAULT_IMAGES provided"
    exit 1
  fi
}

function load_cluster_images_airgapped() {
  echo "Preparing loading of images..."
  LOAD_DEFAULT_IMG=false
  LOAD_TARBALL=false
  if [ -n "${TARBALL_FILE_PATH}" ]; then
    kind_load_tar_imgs $TARBALL_FILE_PATH
    LOAD_TARBALL=true
  else
    echo "TARBALL_FILE_PATH variable is empty"
  fi
  if [ -n "${DEFAULT_IMAGES}" ]; then
      kind_load_docker_imgs $HARBOR_DIND_IMAGE_PATH $SIVT_DEFAULT_IMAGES
      LOAD_DEFAULT_IMG=true
  else
      echo "DEFAULT_IMAGES variable is empty"
  fi
  if [ "$LOAD_DEFAULT_IMG" == "false" ] && [ "$LOAD_TARBALL" == "false" ]; then
    echo "FAILED: Neither TARBALL_FILE_PATH NOR DEFAULT_IMAGES provided"
    exit 1
  fi
}

function copy_harbor_certificates_in_cluster() {
  echo "Copying Harbor certificates in cluster ${CLUSTER_NAME}..."

  cluster_container_id=$(docker inspect -f   '{{.Id}}' ${CLUSTER_NAME}'-control-plane')
  docker exec -it "${cluster_container_id}" mkdir -p /etc/config-registry-cert/
  docker cp ${HARBOR_CERT_FILE} $cluster_container_id:/etc/config-registry-cert/
  docker cp ${HARBOR_CERT_FILE} $cluster_container_id:/etc/ssl/certs

  docker cp ${CA_CERT_FILE} $cluster_container_id:/etc/config-registry-cert/
  docker cp ${CA_CERT_FILE} $cluster_container_id:/etc/ssl/certs
  docker exec -it ${cluster_container_id} "update-ca-certificates"
  systemctl restart docker
  sleep 60
  printf "Done\n\n"
}

function create_cluster() {

  if kind get clusters | grep "${CLUSTER_NAME}" &> /dev/null; then
    echo "Cluster ${CLUSTER_NAME} already created"

     if [ ! -f "${CLUSTER_CONFIG_PATH}" ]; then
      echo "Getting cluster config file..."
      if ! kind export kubeconfig --name "${CLUSTER_NAME}" --kubeconfig "${CLUSTER_CONFIG_PATH}"; then
        echo "Failed to get cluster config file" >&2
        exit 1
        #return 1
      fi
     fi
     printf "Done\n\n"
  elif ! kind get clusters | grep "${CLUSTER_NAME}" &> /dev/null; then

    echo "Creating cluster ${CLUSTER_NAME}..."

    CLUSTER_IMAGE_ARG=""
    CLUSTER_CONFIG_ARG=""
    if [ -n "${CLUSTER_INIT_CONFIG_FILE}" ]; then
        CLUSTER_CONFIG_ARG=${CLUSTER_INIT_CONFIG_FILE}
    fi

    if [ "${AIRGAPPED}" == "true" ]; then
        if [ -n "${HARBOR_KIND_IMAGE}" ]; then
           CLUSTER_IMAGE_ARG=${HARBOR_KIND_IMAGE}
        fi
        docker_pull_imgs_from_harbor $HARBOR_DIND_IMAGE_PATH $HARBOR_KIND_IMAGE
    else
        if [ -n "${CLUSTER_IMAGE}" ]; then
           CLUSTER_IMAGE_ARG=${CLUSTER_IMAGE}
        fi
        docker_pull_imgs $CLUSTER_IMAGE $DEFAULT_IMAGES
    fi

    if ! kind create cluster --config "${CLUSTER_CONFIG_ARG}" --image "${CLUSTER_IMAGE_ARG}" --name "${CLUSTER_NAME}" --kubeconfig "${CLUSTER_CONFIG_PATH}"; then
      echo "Failed to create cluster" >&2
      exit 1
      #return 1
    fi

  fi

  if [ "${AIRGAPPED}" == "true" ]; then
    copy_harbor_certificates_in_cluster
    load_cluster_images_airgapped
  else
    load_cluster_images
  fi

  if [ "${AIRGAPPED}" == "true" ]; then
    kubectl apply -f ${AIRGAPPED_NGINX_INGRESS_FILE}
  else
    kubectl apply -f ${NGINX_INGRESS_FILE}
  fi

  printf "Done\n\n"

}

function deploy_tekton() {

  #local files="${TEKTON_PIPELINE_FILE} ${TEKTON_TRIGGERS_FILE}"
  #local tkn_imgs=""
  echo "Deploying Tekton..."

  #for i in $files
  #do
    #tkn_imgs+=$(curl $i | grep image: | awk '{print $2}' | sed 's/"/ /g')
  #done

    #docker_pull_imgs $tkn_imgs
    #kind_load_docker_imgs $tkn_imgs

  if [ "${AIRGAPPED}" == "true" ]; then
    kubectl apply --filename "${AIRGAPPED_TEKTON_PIPELINE_FILE}"
    kubectl apply --filename "${AIRGAPPED_TEKTON_PIPELINE_TRIGGERS_FILE}"
    kubectl apply --filename "${AIRGAPPED_TEKTON_POLLING_OPERATOR_FILE}"
  else
    kubectl apply --filename "${TEKTON_PIPELINE_FILE}"
    kubectl apply --filename "${TEKTON_TRIGGERS_FILE}"
  fi
  printf "Done\n\n"
}

function deploy_tekton_dashboard() {

  #local files="${TEKTON_DASHBOARD_FILE}"
  #local tkn_dash_imgs=""
  echo "Deploying Tekton Dashboard..."

  #for i in $files
  #do
    #tkn_dash_imgs+=$(curl $i | grep image: | awk '{print $2}' | sed 's/"/ /g')
  #done

  #docker_pull_imgs $tkn_dash_imgs
  #kind_load_docker_imgs $tkn_dash_imgs
  if [ "${AIRGAPPED}" == "true" ]; then
    kubectl apply --filename "${AIRGAPPED_TEKTON_PIPELINE_DASHBOARD_FILE}"
    kubectl create -f "${TEKTON_DASHBOARD_ING_FILE}"
  else
    kubectl apply --filename "${TEKTON_DASHBOARD_FILE}"
    kubectl create -f "${TEKTON_DASHBOARD_ING_FILE}"
  fi
  printf "Done\n\n"
}

function print_tekton_dashboard_help() {
  printKubeconfig=$1
  #echo "To access the Tekton Dashboard, run:"
  #if [ "${printKubeconfig}" == "true" ]; then
    #echo "  kubectl proxy --kubeconfig ${KUBECONFIG} --port=8080"
  #else
    #echo "  kubectl proxy --port=8080"
  #fi
  #echo "  http://localhost:8080/api/v1/namespaces/tekton-pipelines/services/tekton-dashboard:http/proxy/"
  echo "To access the Tekton Dashboard through Nginx-INgress, open:"
  echo " http://<vm-ip>:<exposed-port>/"
}

function load_upgrade_imgs() {
  echo "Preparing loading of images..."
  if [ -n "${UPGRADE_TARBALL_FILE_PATH}" ]; then
    kind_load_tar_imgs $UPGRADE_TARBALL_FILE_PATH
  else
    echo "UPGRADE_TARBALL_FILE_PATH variable is empty"
  fi
  if [ -n "${UPGRADE_IMAGES}" ]; then
    kind_load_docker_imgs $UPGRADE_IMAGES
  else
    echo "UPGRADE_IMAGES variable is empty"
  fi

}

function execute_mgmt_upgrade() {
  echo "Checking path for mgmt upgrade.."
  DIRECTORY="resources"
  if [ ! -d "$DIRECTORY" ]; then
    echo "Unable to locate resource directory. Please execute script from tekton root directory"
    exit 1
  else
    ytt -f templates/git-user-pass-template.yaml -f values.yaml -f values-schema.yaml  > resources/secret.yaml
    ytt -f templates/day2-mgmt-pipeline-run-template.yaml -f values.yaml -f values-schema.yaml  > run/day2-upgrade.yml
    echo -e "\nApplying resources and pipelines"
    kubectl apply -f resources/ -f tasks/ -f pipelines/
    echo -e "\nStarting the pipeline"
    kubectl create -f run/day2-upgrade.yml
  fi
}

function execute_all_upgrade() {
  echo "Checking path for all upgrade.."
  DIRECTORY="resources"
  if [ ! -d "$DIRECTORY" ]; then
    echo "Unable to locate resource directory. Please execute script from tekton root directory"
    exit 1
  else
    ytt -f templates/git-user-pass-template.yaml -f values.yaml -f values-schema.yaml > resources/secret.yaml
    ytt -f templates/day2-all-pipeline-run-template.yaml -f values.yaml -f values-schema.yaml > run/day2-upgrade.yml
    echo -e "\nApplying resources and pipelines"
    kubectl apply -f resources/ -f tasks/ -f pipelines/
    echo -e "\nStarting the pipeline"
    kubectl create -f run/day2-upgrade.yml
  fi
}

function deploy_bringup() {
  echo "Checking path for bringup.."
  DIRECTORY="resources"
  if [ ! -d "$DIRECTORY" ]; then
    echo "Unable to locate resource directory. Please execute script from tekton root directory"
    exit 1

  else
    ytt -f templates/git-user-pass-template.yaml -f values.yaml -f values-schema.yaml > resources/secret.yaml
    ytt -f templates/day0-pipeline-run-template.yaml -f values.yaml -f values-schema.yaml > run/day0-bringup.yml
    echo -e "\nApplying resources and pipelines"
    kubectl apply -f resources/ -f tasks/ -f pipelines/
    echo -e "\nStarting the pipeline"
    kubectl create -f run/day0-bringup.yml
  fi
}

function deploy_tkgs_bringup() {
  echo "Checking path for bringup.."
  DIRECTORY="resources"
  if [ ! -d "$DIRECTORY" ]; then
    echo "Unable to locate resource directory. Please execute script from tekton root directory"
    exit 1

  else
    ytt -f templates/git-user-pass-template.yaml -f values.yaml -f values-schema.yaml > resources/secret.yaml
    ytt -f templates/day0-pipeline-tkgs-run-template.yaml -f values.yaml -f values-schema.yaml > run/day0-bringup-tkgs.yml
    echo -e "\nApplying resources and pipelines"
    kubectl apply -f resources/ -f tasks/ -f pipelines/
    echo -e "\nStarting the pipeline"
    kubectl create -f run/day0-bringup-tkgs.yml
  fi

}
function deploy_pipeline() {
  pipelineFiles=("${@}")
  echo "Deploying pipeline..."

  if [ ${#pipelineFiles[@]} == 0 ]; then
    echo "No pipeline files provided" >&2
    return 1
  fi

  args=("apply")
  for file in "${pipelineFiles[@]}"; do
    args+=("-f" "${file}")
  done

  if ! kubectl "${args[@]}"; then
    echo "Failed to deploy pipeline" >&2
    return 1
  fi

  printf "Done\n\n"
}

function build_docker_image(){
  echo "Going to build sivt default image:" $SIVT_DEFAULT_IMAGES
  python scripts/__main__.py --root-dir=. tkn-docker build
  ret=$?
  if [[ $ret -eq 0 ]]; then
     echo "Successfully created docker image"
     return 0
  else
    python scripts/__main__.py --root-dir=. tkn-docker build
    ret=$?
    if [[ $ret -eq 0 ]]; then
       echo "Successfully created docker image"
       return 0
    else
       echo "Failed to create docker image"
       return 1
    fi
  fi
}


function main() {
  needToCreateCluster=false
  needToDeployTektonDashboard=false
  executeMgmtUpgrade=false
  executeAllUpgrade=false
  declare -a pipelineFiles
  arg1="$1"
  arg2="$2"
  if [[ "$arg2" == "--airgapped" ]]; then
        AIRGAPPED="true"
  fi

  while (( "$#" )); do
    case "$arg1" in
      -h|--help)
        usage
        exit 0
        ;;
      --build_docker_image)
        needToCreateDockerImage=true
        shift 1
        ;;
      --create-cluster)
        needToCreateCluster=true
        shift 1
        ;;
      --deploy-dashboard)
        needToDeployTektonDashboard=true
        shift 1
        ;;
      --exec-day0)
        deployBringUp=true
        shift 1
        ;;
      --exec-tkgs-day0)
        deployTkgsBringUp=true
        shift 1
        ;;
      --exec-upgrade-mgmt)
        executeMgmtUpgrade=true
        shift 1
        ;;
      --exec-upgrade-all)
        executeAllUpgrade=true
        shift 1
        ;;
      --load-upgrade-imgs)
        loadUpgradeImgs=true
        shift 1
        ;;
      -*) # unsupported flags
        echo "Error: Unsupported flag $1" >&2
        exit 1
        ;;
      *)
        pipelineFiles+=("${1}")
        shift 1
        ;;
    esac
  done

  if [ "${needToCreateDockerImage}" == "true" ]; then
    build_docker_image
  fi

  check_for_kubectl

  if [ "${needToCreateCluster}" == "true" ]; then
    export KUBECONFIG="${CLUSTER_CONFIG_PATH}"
    check_for_kind
    create_cluster
    deploy_tekton
  fi

  export KUBECONFIG="${CLUSTER_CONFIG_PATH}"

  if [ "${needToDeployTektonDashboard}" == "true" ]; then
    deploy_tekton_dashboard
  fi
  if [ "${deployBringUp}" == "true" ]; then
    deploy_bringup
  fi
  if [ "${deployTkgsBringUp}" == "true" ]; then
    deploy_tkgs_bringup
  fi
  if [ "${executeUpgrade}" == "true" ]; then
    execute_upgrade
  fi
  if [ "${executeMgmtUpgrade}" == "true" ]; then
    execute_mgmt_upgrade
  fi
  if [ "${executeAllUpgrade}" == "true" ]; then
    execute_all_upgrade
  fi
  if [ "${loadUpgradeImgs}" == "true" ]; then
    load_upgrade_imgs
  fi

  if [ ${#pipelineFiles[@]} -gt 0 ]; then
    check_for_tkn
    deploy_pipeline "${pipelineFiles[@]}"
  fi

  if [ "${needToDeployTektonDashboard}" == "true" ]; then
    print_tekton_dashboard_help "${needToCreateCluster}"
  fi
}

if [ "$0" = "${BASH_SOURCE[0]}" ]; then
  main "$@"
fi


