#!/bin/bash
function usage() {
  echo "Usage: launch.sh [--create-cluster] [--deploy-dashboard] [<pipeline.yaml>,...]"
  echo ""
  echo "  Deploys Tekton and a pipeline onto a Kubernetes cluster (which this script can create as well)"
  echo ""
  echo "    --create-cluster    Create a cluster, using kind."
  echo "    --deploy-dashboard  Deploy the Tekton dashboard as well."
  echo "    --exec-day0         To trigger day0 pipline, bringup of TKGM"
  echo "    --exec-upgrade-mgmt To trigger upgrade of mgmt cluster"
  echo "    --exec-upgrade-all To trigger upgrade of all clusters"
  echo "    <pipeline.yaml,...> The paths to Tekton pipeline files (can be a local files or URLs)"
  echo "    <pipeline.yaml,...> The paths to Tekton pipeline files (can be a local files or URLs)"
}

DEFAULT_IMAGES="docker:dind"
CLUSTER_IMAGE="kindest/node:v1.21.1"
TARBALL_URL=""
TARBALL_FILE_PATH=""

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


function kind_load_tar_imgs() {

  local tar_url_list="$@"
  
  if [ -n "${TARBALL_FILE_PATH}" ]; then
     if [ -f $TARBALL_FILE_PATH ]; then
        if ! kind load image-archive $TARBALL_FILE_PATH --name $CLUSTER_NAME; then
           echo "failed to load tarball image file:- $i" >&2
        fi
     else
        echo "Mentioned Tarball file ${TARBALL_FILE_PATH} is not found "
        exit 1
     fi
  elif [ -n "${tar_url_list}" ]; then
    for i in $tar_url_list
      do
        if ! echo $i | grep -q "\.tar"; then
          echo "Invalid URL format:- $i" >&2
        fi

        tar_file=$(echo $i | rev | cut -d "." -f2 | cut -d "/" -f1 | rev)

        if [ -f $tar_file.tar ]; then
           echo "$tar_file.tar is present"
        else
           if ! wget $i; then
             echo "Failed to download tarball image:- $i" >&2
           fi
        fi
        
        echo "Loading tarball image file to kind cluster"
        if ! kind load image-archive $tar_file.tar --name $CLUSTER_NAME; then
           echo "failed to load tarball image file:- $i" >&2
        fi
    done
  else
      echo "Both TARBALL_FILE_PATH variable and TARBALL_URL is empty"
      exit 1
  fi

}

function kind_load_docker_imgs() {
  
  local image_names="$@"
  
  for i in $image_names
    do
      if ! kind load docker-image $i --name $CLUSTER_NAME; then
         echo "failed to load docker image :- $i" >&2
      fi
  done
}


function create_cluster() {
  echo "Creating cluster ${CLUSTER_NAME}..."
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
  

    CLUSTER_IMAGE_ARG=""
    if [ -n "${CLUSTER_IMAGE}" ]; then
      CLUSTER_IMAGE_ARG=${CLUSTER_IMAGE}
    fi

    CLUSTER_CONFIG_ARG=""
    if [ -n "${CLUSTER_INIT_CONFIG_FILE}" ]; then
      CLUSTER_CONFIG_ARG=${CLUSTER_INIT_CONFIG_FILE}
    fi

    docker_pull_imgs $CLUSTER_IMAGE $DEFAULT_IMAGES

    if ! kind create cluster --config "${CLUSTER_CONFIG_ARG}" --image "${CLUSTER_IMAGE_ARG}" --name "${CLUSTER_NAME}" --kubeconfig "${CLUSTER_CONFIG_PATH}"; then
      echo "Failed to create cluster" >&2
      exit 1
      #return 1
    fi
    echo "Preparing loading of images..."
    kind_load_tar_imgs $TARBALL_URL
    kind_load_docker_imgs $DEFAULT_IMAGES

    kubectl apply -f ${NGINX_INGRESS_FILE}
    printf "Done\n\n"

  fi

    kind_load_tar_imgs $TARBALL_URL
    kind_load_docker_imgs $DEFAULT_IMAGES

    kubectl apply -f ${NGINX_INGRESS_FILE}
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

    kubectl apply --filename "${TEKTON_PIPELINE_FILE}"
    kubectl apply --filename "${TEKTON_TRIGGERS_FILE}"

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

  kubectl apply --filename "${TEKTON_DASHBOARD_FILE}"
  kubectl create -f "${TEKTON_DASHBOARD_ING_FILE}"
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

function execute_mgmt_upgrade() {
  echo "Checking path for mgmt upgrade.."
  DIRECTORY="resources"
  if [ ! -d "$DIRECTORY" ]; then
    echo "Unable to locate resource directory. Please execute script from tekton root directory"
    exit 1
  else
    ytt -f templates/git-user-pass-template.yaml -f values.yaml > resources/secret.yaml
    ytt -f templates/day2-mgmt-pipeline-run-template.yaml -f values.yaml > run/day2-upgrade.yml
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
    ytt -f templates/git-user-pass-template.yaml -f values.yaml > resources/secret.yaml
    ytt -f templates/day2-all-pipeline-run-template.yaml -f values.yaml > run/day2-upgrade.yml
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
    ytt -f templates/git-user-pass-template.yaml -f values.yaml > resources/secret.yaml
    ytt -f templates/day0-pipeline-run-template.yaml -f values.yaml > run/day0-bringup.yml
    echo -e "\nApplying resources and pipelines"
    kubectl apply -f resources/ -f tasks/ -f pipelines/
    echo -e "\nStarting the pipeline"
    kubectl create -f run/day0-bringup.yml
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

function main() {
  needToCreateCluster=false
  needToDeployTektonDashboard=false
  executeMgmtUpgrade=false
  executeAllUpgrade=false
  declare -a pipelineFiles
  while (( "$#" )); do
    case "$1" in
      -h|--help)
        usage
        exit 0
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
      --exec-upgrade-mgmt)
        executeMgmtUpgrade=true
        shift 1
        ;;
      --exec-upgrade-all)
        executeAllUpgrade=true
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
  if [ "${executeUpgrade}" == "true" ]; then
    execute_upgrade
  fi
  if [ "${executeMgmtUpgrade}" == "true" ]; then
    execute_mgmt_upgrade
  fi
  if [ "${executeAllUpgrade}" == "true" ]; then
    execute_all_upgrade
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

