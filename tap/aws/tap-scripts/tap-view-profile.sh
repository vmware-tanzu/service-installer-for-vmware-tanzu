#!/bin/bash
# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
source var.conf

cat <<EOF | tee tap-gui-viewer-service-account-rbac.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tap-gui
---
apiVersion: v1
kind: ServiceAccount
metadata:
  namespace: tap-gui
  name: tap-gui-viewer
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: tap-gui-read-k8s
subjects:
- kind: ServiceAccount
  namespace: tap-gui
  name: tap-gui-viewer
roleRef:
  kind: ClusterRole
  name: k8s-reader
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: k8s-reader
rules:
- apiGroups: ['']
  resources: ['pods', 'services', 'configmaps']
  verbs: ['get', 'watch', 'list']
- apiGroups: ['apps']
  resources: ['deployments', 'replicasets']
  verbs: ['get', 'watch', 'list']
- apiGroups: ['autoscaling']
  resources: ['horizontalpodautoscalers']
  verbs: ['get', 'watch', 'list']
- apiGroups: ['networking.k8s.io']
  resources: ['ingresses']
  verbs: ['get', 'watch', 'list']
- apiGroups: ['networking.internal.knative.dev']
  resources: ['serverlessservices']
  verbs: ['get', 'watch', 'list']
- apiGroups: [ 'autoscaling.internal.knative.dev' ]
  resources: [ 'podautoscalers' ]
  verbs: [ 'get', 'watch', 'list' ]
- apiGroups: ['serving.knative.dev']
  resources:
  - configurations
  - revisions
  - routes
  - services
  verbs: ['get', 'watch', 'list']
- apiGroups: ['carto.run']
  resources:
  - clusterconfigtemplates
  - clusterdeliveries
  - clusterdeploymenttemplates
  - clusterimagetemplates
  - clusterruntemplates
  - clustersourcetemplates
  - clustersupplychains
  - clustertemplates
  - deliverables
  - runnables
  - workloads
  verbs: ['get', 'watch', 'list']
- apiGroups: ['source.toolkit.fluxcd.io']
  resources:
  - gitrepositories
  verbs: ['get', 'watch', 'list']
- apiGroups: ['source.apps.tanzu.vmware.com']
  resources:
  - imagerepositories
  verbs: ['get', 'watch', 'list']
- apiGroups: ['conventions.apps.tanzu.vmware.com']
  resources:
  - podintents
  verbs: ['get', 'watch', 'list']
- apiGroups: ['kpack.io']
  resources:
  - images
  - builds
  verbs: ['get', 'watch', 'list']
- apiGroups: ['scanning.apps.tanzu.vmware.com']
  resources:
  - sourcescans
  - imagescans
  - scanpolicies
  verbs: ['get', 'watch', 'list']
- apiGroups: ['tekton.dev']
  resources:
  - taskruns
  - pipelineruns
  verbs: ['get', 'watch', 'list']
- apiGroups: ['kappctrl.k14s.io']
  resources:
  - apps
  verbs: ['get', 'watch', 'list']

EOF

kubectl create -f tap-gui-viewer-service-account-rbac.yaml

CLUSTER_URL=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')

CLUSTER_TOKEN=$(kubectl -n tap-gui get secret $(kubectl -n tap-gui get sa tap-gui-viewer -o=json \
| jq -r '.secrets[0].name') -o=json \
| jq -r '.data["token"]' \
| base64 --decode)

echo CLUSTER_URL: $CLUSTER_URL
echo CLUSTER_TOKEN: $CLUSTER_TOKEN


# set the following variables
export TAP_REGISTRY_SERVER=$registry_url
export TAP_REGISTRY_USER=$registry_user
export TAP_REGISTRY_PASSWORD=$registry_password



cat <<EOF | tee tap-values-view.yaml
profile: view
ceip_policy_disclosed: true

shared:
  ingress_domain: "${tap_view_app_domain}"
  
contour:
  envoy:
    service:
      type: LoadBalancer

learningcenter:
  ingressDomain: "learning.${tap_view_app_domain}"
  ingressClass: contour

tap_gui:
  service_type: ClusterIP
  ingressEnabled: "true"
  ingressDomain: "${tap_view_app_domain}"
  app_config:
    app:
      baseUrl: "http://tap-gui.${tap_view_app_domain}"
    catalog:
      locations:
        - type: url
          target: ${tap_git_catalog_url}
    backend:
        baseUrl: "http://tap-gui.${tap_view_app_domain}"
        cors:
          origin: "http://tap-gui.${tap_view_app_domain}"

    kubernetes:
      serviceLocatorMethod:
        type: "multiTenant"
      clusterLocatorMethods:
        - type: "config"
          clusters:
            - url: ${CLUSTER_URL}
              name: ${TAP_RUN_CLUSTER_NAME}
              authProvider: "serviceAccount"
              skipTLSVerify: true
              skipMetricsLookup: true
              serviceAccountToken: "${CLUSTER_TOKEN}"


metadata_store:
  app_service_type: LoadBalancer


appliveview:
  ingressEnabled: true
  ingressDomain: "${alv_domain}" 

EOF

tanzu package install tap -p tap.tanzu.vmware.com -v $TAP_VERSION --values-file tap-values-view.yaml -n "${TAP_NAMESPACE}"
tanzu package installed get tap -n "${TAP_NAMESPACE}"


# ensure all build cluster packages are installed succesfully
tanzu package installed list -A

kubectl get svc -n tanzu-system-ingress

# pick an external ip from service output and configure DNS wildcard records
# example - *.ui.customer0.io ==> <ingress external ip/cname>