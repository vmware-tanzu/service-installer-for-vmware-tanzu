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

CLUSTER_IMAGE=""
CLUSTER_NAME="${CLUSTER_NAME:=arcas-ci-cd-cluster}"   # The name of the cluster to create with Kind
CLUSTER_CONFIG_PATH="${CLUSTER_CONFIG_PATH:=./${CLUSTER_NAME}.yaml}"

TEKTON_DASHBOARD_VERSION="${TEKTON_DASHBOARD_VERSION:=v0.24.1}"
TEKTON_DASHBOARD_FILE="${TEKTON_DASHBOARD_FILE:=https://storage.googleapis.com/tekton-releases/dashboard/previous/${TEKTON_DASHBOARD_VERSION}/tekton-dashboard-release.yaml}"
TEKTON_PIPELINE_VERSION="${TEKTON_PIPELINE_VERSION:=v0.33.0}"
TEKTON_PIPELINE_FILE="${TEKTON_PIPELINE_FILE:=https://storage.googleapis.com/tekton-releases/pipeline/previous/${TEKTON_PIPELINE_VERSION}/release.yaml}"
TEKTON_TRIGGERS_VERSION="${TEKTON_TRIGGERS_VERSION:=v0.18.0}"
TEKTON_TRIGGERS_FILE="${TEKTON_TRIGGERS_FILE:=https://storage.googleapis.com/tekton-releases/triggers/previous/${TEKTON_TRIGGERS_VERSION}/release.yaml}"

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

function create_cluster() {
  echo "Creating cluster ${CLUSTER_NAME}..."
  if kind get clusters | grep "${CLUSTER_NAME}" &> /dev/null; then
    echo "Cluster ${CLUSTER_NAME} already created"

    if [ ! -f "${CLUSTER_CONFIG_PATH}" ]; then
      echo "Getting cluster config file..."
      if ! kind export kubeconfig --name "${CLUSTER_NAME}" --kubeconfig "${CLUSTER_CONFIG_PATH}"; then
        echo "Failed to get cluster config file" >&2
        return 1
      fi
    fi
    printf "Done\n\n"
    return
  fi

  CLUSTER_IMAGE_ARG=""
  if [ -n "${CLUSTER_IMAGE}" ]; then
    CLUSTER_IMAGE_ARG="--image ${CLUSTER_IMAGE} "
  fi

  if ! kind create cluster "${CLUSTER_IMAGE_ARG}"--name "${CLUSTER_NAME}" --kubeconfig "${CLUSTER_CONFIG_PATH}"; then
    echo "Failed to create cluster" >&2
    return 1
  fi
  printf "Done\n\n"
}

function deploy_tekton() {
  echo "Deploying Tekton..."
  kubectl apply --filename "${TEKTON_PIPELINE_FILE}"
  kubectl apply --filename "${TEKTON_TRIGGERS_FILE}"
  printf "Done\n\n"
}

function deploy_tekton_dashboard() {
  echo "Deploying Tekton Dashboard..."
  kubectl apply --filename "${TEKTON_DASHBOARD_FILE}"
  printf "Done\n\n"
}

function print_tekton_dashboard_help() {
  printKubeconfig=$1
  echo "To access the Tekton Dashboard, run:"
  if [ "${printKubeconfig}" == "true" ]; then
    echo "  kubectl proxy --kubeconfig ${KUBECONFIG} --port=8080"
  else
    echo "  kubectl proxy --port=8080"
  fi
  echo "and open:"
  echo "  http://localhost:8080/api/v1/namespaces/tekton-pipelines/services/tekton-dashboard:http/proxy/"
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

function execute_mgmt_upgrade() {
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
    check_for_kind
    create_cluster
    export KUBECONFIG="${CLUSTER_CONFIG_PATH}"
  fi

  deploy_tekton
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

