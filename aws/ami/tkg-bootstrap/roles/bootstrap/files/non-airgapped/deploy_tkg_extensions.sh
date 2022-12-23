#!/bin/bash
set -o errexit
set -o allexport
source non-airgapped.env
if [ -n "$1" ]; then
  source $1
fi
source deploy_cert_manager.sh $CERT_MANGER_DEPLOYMENT
source deploy_contour.sh $CONTOUR_DEPLOYMENT
source deploy_fluent_bit.sh $FLUENT_BIT_DEPLOYMENT
source deploy_prometheus.sh $PROMETHEUS_DEPLOYMENT
source deploy_grafana.sh $GRAFANA_DEPLOYMENT
source deploy_harbor.sh $HARBOR_DEPLOYMENT