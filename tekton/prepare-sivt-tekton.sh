#!/bin/bash
function usage() {
  echo "*********************************************************************************************************************"
  echo "Usage: ./prepare-sivt-tekton.sh --setup"
  echo ""
  echo "  Prepares Tekton infrastructure ready for SIVT CI/CD execution"
  echo ""
  echo "*    Individual infrastrucure setup can be executed by the following order"
  echo "*    1. --build_docker_image             Create docker tar image as per desired_state.yml version"
  echo "*    2. --create-cluster [--airgapped]   Create a cluster, using kind. Pass --airgapped for airgapped environment"
  echo "*    3. --deploy-dashboard  [--airgapped] Deploy the Tekton dashboard as well. Pass --airgapped for airgapped environment"
  echo "*    4. --load-pipelines  Load Tekton pipelines, tasks, secrets, triggers and resources."  
  echo "*    --exec-day0, --exec-day2-upgrade --exec-day2-resize --exec-day2-scale options are supported"
  echo "*********************************************************************************************************************"
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

SIVT_DEFAULT_IMAGES="sivt_tekton:v210"
DEFAULT_IMAGES="docker:dind"
CLUSTER_IMAGE="kindest/node:v1.21.1"
WORKER_IMAGE="tekton_worker"

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
TEKTON_POLLING_RESOURCES="https://github.com/bigkevmcd/tekton-polling-operator/releases/download/v0.4.0/release-v0.4.0.yaml"

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
  local image_name=$1
  if ! docker images image_name; then
    echo "$image_name image is not present locally.." >&2
    exit 1
  fi
  if ! kind load docker-image $image_name --name $CLUSTER_NAME; then
        echo "failed to load docker image :- $image_name" >&2
        exit 1
  else
         echo "Successfully loaded docker image :- $image_name"
    fi
  
}

function load_cluster_images() {
  echo "Preparing loading of images..."
  LOAD_DEFAULT_IMG=false
  LOAD_TARBALL=false
  if [ -n "${DEFAULT_IMAGES}" ]; then
    echo -e "Loading $DEFAULT_IMAGES"
    kind_load_docker_imgs $DEFAULT_IMAGES 
    echo -e "Loading $SIVT_DEFAULT_IMAGES"
    kind_load_docker_imgs $SIVT_DEFAULT_IMAGES
    echo -e "Loading $DEFAULT_IMAGES"
    kind_load_docker_imgs $WORKER_IMAGE
  else
      echo "DEFAULT_IMAGES variable is empty"
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

#  if [ "${AIRGAPPED}" == "true" ]; then
#    copy_harbor_certificates_in_cluster
#    load_cluster_images_airgapped
#  else
#    load_cluster_images
#  fi

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
  echo "Wait for resources to be available..."
  sleep 5
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
  echo "To access the Tekton Dashboard through Nginx-INgress, open:"
  echo " http://<vm-ip>:8085/"
}

function load_tekton_pipelines(){
  DIRECTORY="tekton-infra"
  if [ ! -d "$DIRECTORY" ]; then
    echo "Unable to locate resource directory. Please execute script from tekton root directory"
    exit 1
  kubectl apply -f $(TEKTON_POLLING_RESOURCES)

  else
    ytt -f tekton-infra/templates/git-user-pass-template.yaml -f values.yaml -f values-schema.yaml > tekton-infra/resources/secret.yaml

    echo -e "\nApplying polling resources"

    ytt -f tekton-infra/templates/tekton-pipeline-bringup-res-template.yaml -f values.yaml -f values-schema.yaml > tekton-infra/pipeline-resources/tekton-bringup-res-pipeline.yml
    ytt -f tekton-infra/templates/tekton-pipeline-day2-ops-res-template.yaml -f values.yaml -f values-schema.yaml > tekton-infra/pipeline-resources/tekton-day2-ops-res-pipeline.yml
    
    echo -e "\nLoading bringup pipelines..."
    ytt -f tekton-infra/templates/day0-pipeline-tkgm-run-template.yaml -f values.yaml -f values-schema.yaml > tekton-infra/run/day0-bringup-tkgm.yml
    ytt -f tekton-infra/templates/day0-pipeline-tkgs-run-template.yaml -f values.yaml -f values-schema.yaml > tekton-infra/run/day0-bringup-tkgs.yml

    echo -e "\nLoading day2 pipelines..."
    ytt -f tekton-infra/templates/day2-pipeline-run-upgrade-template.yaml -f values.yaml -f values-schema.yaml > tekton-infra/run/day2-upgrade-operation.yml
    ytt -f tekton-infra/templates/day2-pipeline-run-resize-template.yaml -f values.yaml -f values-schema.yaml > tekton-infra/run/day2-resize-operation.yml
    ytt -f tekton-infra/templates/day2-pipeline-run-scale-template.yaml -f values.yaml -f values-schema.yaml > tekton-infra/run/day2-scale-operation.yml

    echo -e "\nApplying resources"
    kubectl apply -f tekton-infra/resources/

    # uncomment below line to activate git ops trigger method
    # kubectl apply -f tekton-infra/pipeline-resources/

    echo -e "\nApplying tasks"
    kubectl apply -f tekton-infra/tasks/common_tasks/
    kubectl apply -f tekton-infra/tasks/tkgm_tasks_day0/
    kubectl apply -f tekton-infra/tasks/tkgm_tasks_day2/
    kubectl apply -f tekton-infra/tasks/tkgs_tasks_day0/

    echo -e "\nApplying Trigger events pipelines"
    kubectl apply -f tekton-infra/trigger-pipelines/
    echo -e "\nApplying E2E pipelines"
    kubectl apply -f tekton-infra/pipelines/
  fi
}

function exec_scale() {
  echo "Checking path for bringup.."
  DIRECTORY="tekton-infra"
  if [ ! -d "$DIRECTORY" ]; then
    echo "Unable to locate resource directory. Please execute script from tekton root directory"
    exit 1
  else
    echo -e "\nStarting the scale pipeline"
    kubectl create -f tekton-infra/run/day2-scale-operation.yml
  fi
}

function exec_resize() {
  echo "Checking path for bringup.."
  DIRECTORY="tekton-infra"
  if [ ! -d "$DIRECTORY" ]; then
    echo "Unable to locate resource directory. Please execute script from tekton root directory"
    exit 1
  else
    echo -e "\nStarting the resize pipeline"
    kubectl create -f tekton-infra/run/day2-resize-operation.yml
  fi
}

function exec_upgrade() {
  echo "Checking path for bringup.."
  DIRECTORY="tekton-infra"
  if [ ! -d "$DIRECTORY" ]; then
    echo "Unable to locate resource directory. Please execute script from tekton root directory"
    exit 1
  else
    echo -e "\nStarting the upgrade pipeline"
    kubectl create -f tekton-infra/run/day2-upgrade-operation.yml
  fi
}

function deploy_bringup() {
  echo "Checking path for bringup.."
  DIRECTORY="tekton-infra"
  if [ ! -d "$DIRECTORY" ]; then
    echo "Unable to locate resource directory. Please execute script from tekton root directory"
    exit 1
  else
    echo -e "\nStarting the pipeline"
    kubectl create -f tekton-infra/run/day0-bringup-tkgm.yml
  fi
}

function deploy_tkgs_bringup() {
  echo "Checking path for bringup.."
  DIRECTORY="tekton-infra"
  if [ ! -d "$DIRECTORY" ]; then
    echo "Unable to locate resource directory. Please execute script from tekton root directory"
    exit 1

  else
    
    echo -e "\nStarting the pipeline"
    kubectl create -f tekton-infra/run/day0-bringup-tkgs.yml
  fi

}
function exec_suite_env(){
  echo "********************************************************"
  docker login 
  echo "Building docker images..."
  build_docker_image
  echo "Creating cluster..."
  export KUBECONFIG="${CLUSTER_CONFIG_PATH}"
  check_for_kind
  create_cluster
  echo "Loading required images to kind cluster..."
  load_cluster_images
  echo "Preparing to configure Tekton..."
  sleep 10
  deploy_tekton
  export KUBECONFIG="${CLUSTER_CONFIG_PATH}"
  echo "Preparing to creating Tekton dashboard..."
  sleep 30
  deploy_tekton_dashboard
  echo "Preparing to loading the required pipelines..."
  sleep 10
  load_tekton_pipelines
  sleep 10
  echo "********************************************************"
  echo "To access the Tekton Dashboard through Nginx-INgress, open:"
  echo " http://<vm-ip>:8085/"
  echo "********************************************************"
  echo "Environment setup completed successfully..."  
  echo "********************************************************"
}

function build_docker_image(){
  echo "Starting to build required docker images."
  cp -rf tekton-infra/docker-comps/* .
  python scripts/pre_setup/tkn_docker_img.py > /dev/null

  ret=$?
  if [[ $ret -eq 0 ]]; then
     echo "Successfully created docker image"
     rm -rf sivt_tekton_dockerfile
     rm -rf worker_dockerfile
     return 0
  else
    echo "Failed to create docker image"
    rm -rf sivt_tekton_dockerfile
    rm -rf worker_dockerfile
    exit 1
  fi
}


function main() {
  needToCreateCluster=false
  needToDeployTektonDashboard=false
  executeUpgrade=false
  execResize=false
  execScale=false
  deploySuite=false

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
      --exec-day2-upgrade)
        executeUpgrade=true
        shift 1
        ;;
      --exec-day2-resize)
        executeResize=true
        shift 1
        ;;
      --exec-day2-scale)
        executeScale=true
        shift 1
        ;;
      --exec-day2-scale)
        executeScale=true
        shift 1
        ;;
      --setup)
        execSuite=true
        shift 1
        ;;
      --load-pipelines)
        loadPipelines=true
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
    exec_upgrade
  fi
  if [ "${executeResize}" == "true" ]; then
    exec_resize
  fi
  if [ "${executeScale}" == "true" ]; then
    exec_scale
  fi
  if [ "${loadPipelines}" == "true" ]; then
    load_tekton_pipelines
  fi
  if [ "${execSuite}" == "true" ]; then
    exec_suite_env
  fi
  if [ "${needToDeployTektonDashboard}" == "true" ]; then
    print_tekton_dashboard_help "${needToCreateCluster}"
  fi
}

if [ "$0" = "${BASH_SOURCE[0]}" ]; then
  main "$@"
fi
