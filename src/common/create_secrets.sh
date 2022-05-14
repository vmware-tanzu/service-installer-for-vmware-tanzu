kubectl -n package-tanzu-system-registry create secret generic harbor-notary-singer-image-overlay -o yaml --dry-run=client --from-file=./harbor-overlay.yaml | kubectl apply -f -
