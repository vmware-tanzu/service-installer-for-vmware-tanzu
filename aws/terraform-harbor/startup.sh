#!/bin/bash

set -eu
AWS_DEFAULT_REGION=${region}
DNS_NAME=$(hostname -f)
CERT_PATH=${cert_path}
CERT_KEY_PATH=${cert_key_path}
CACERT_PATH=${cert_ca_path}
CREATE_CERTS=${create_certs}
HARBOR_ADMIN_PWD=${harbor_pwd}
BUCKET_NAME=${bucket_name}
TKG_VERSION=${tkg_version}
TKR_VERSION=${tkr_version}
TKG_CUSTOM_IMAGE_REPOSITORY_CA_PATH="/etc/docker/certs.d/$DNS_NAME/ca.crt"
yum install docker -y
mkdir -p /var/log/harbor/
mkdir -p /data/cert
mkdir -p /etc/docker/certs.d/"$DNS_NAME"
mkdir -p /etc/harbor/tls/internal
pushd /root &> /dev/null
        mkdir image-builder
	aws s3 cp s3://"$BUCKET_NAME"/harbor/harbor.tar.gz .
	aws s3 cp s3://"$BUCKET_NAME"/harbor/docker-compose /usr/bin
	chmod +x /usr/bin/docker-compose
	aws s3 cp s3://"$BUCKET_NAME"/harbor image-builder --recursive --include "*.tar" --exclude "*.tar.gz"
	tar -xvf harbor.tar.gz

	if [ "$CREATE_CERTS" == "true" ]; then
		openssl genrsa -out ca.key 4096
        	openssl req -x509 -new -nodes -sha512 -days 3650 \
        		-subj "/C=CN/ST=${cert_st}/L=${cert_l}/O=${cert_o}/OU=${cert_ou}/CN=$DNS_NAME" \
        		-key ca.key \
        		-out ca.crt
        	openssl genrsa -out "$DNS_NAME".key 4096
        	openssl req -sha512 -new \
                	-subj "/C=CN/ST=${cert_st}/L=${cert_l}/O=${cert_o}/OU=${cert_ou}/CN=$DNS_NAME" \
    			-key "$DNS_NAME".key \
    			-out "$DNS_NAME".csr
        	cat > v3.ext <<-EOF
			authorityKeyIdentifier=keyid,issuer
			basicConstraints=CA:FALSE
			keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
			extendedKeyUsage = serverAuth
			subjectAltName = @alt_names

			[alt_names]
			DNS.1=$DNS_NAME
		EOF
        	openssl x509 -req -sha512 -days 3650 \
        		-extfile v3.ext \
        		-CA ca.crt -CAkey ca.key -CAcreateserial \
        		-in "$DNS_NAME".csr \
        		-out "$DNS_NAME".crt
        	cp "$DNS_NAME".crt /data/cert
        	cp "$DNS_NAME".key /data/cert
        	openssl x509 -inform PEM -in "$DNS_NAME".crt -out "$DNS_NAME".cert
        	cp "$DNS_NAME".cert /etc/docker/certs.d/"$DNS_NAME"/
		cp "$DNS_NAME".key /etc/docker/certs.d/"$DNS_NAME"/
		cp ca.crt /etc/docker/certs.d/"$DNS_NAME"/
	else
        	cp "$CERT_PATH" /data/cert
        	cp "$CERT_KEY_PATH" /data/cert
        	openssl x509 -inform PEM -in "$CERT_PATH" -out "$DNS_NAME".cert
        	cp "$CERT_PATH" /etc/docker/certs.d/"$DNS_NAME"/
        	cp "$CERT_KEY_PATH" /etc/docker/certs.d/"$DNS_NAME"/
        	cp "$CACERT_PATH" /etc/docker/certs.d/"$DNS_NAME"/
	fi
	systemctl restart docker
	pushd harbor
		sed -i.bak -e "s/DNS_NAME/$DNS_NAME/g" harbor.yml
		sed -i.bak -e "s/Harbor12345/$HARBOR_ADMIN_PWD/g" harbor.yml
		docker load -i harbor*.tar.gz
		HARBOR_VERSION=$(ls harbor*.tar.gz | cut -d '.' -f 2,3,4)
   		docker run -v /:/hostfs goharbor/prepare:"$HARBOR_VERSION" gencert -p /etc/harbor/tls/internal
   		bash install.sh --with-notary --with-trivy --with-chartmuseum
	popd
	echo "Waiting 30 seconds for harbor api to accept requests"
	sleep 30
	curl -XPOST -H 'Content-Type: application/json' -u admin:"$HARBOR_ADMIN_PWD" "https://$DNS_NAME/api/v2.0/projects" --cacert /etc/docker/certs.d/"$DNS_NAME"/ca.crt -d '{
  	"project_name": "tkg",
  	"public": true
	}'

	docker login -u admin -p "$HARBOR_ADMIN_PWD" "$DNS_NAME"
	mkdir images
	aws s3 cp --recursive "s3://$BUCKET_NAME/tkg/tkg-$TKG_VERSION/images" images
	aws s3 cp --recursive "s3://$BUCKET_NAME/tkr/tkr-$TKR_VERSION/images" images
	chmod u+x images/publish-tkg-images-fromtar.sh images/publish-tkr-images-fromtar.sh
	aws s3 cp "s3://$BUCKET_NAME/tkg/tkg-$TKG_VERSION/tanzu.tar" .
	tar -xvf tanzu.tar
	pushd cli
		gzip -d imgpkg*.gz
		chmod +x imgpkg*
		mv imgpkg* /usr/bin/imgpkg
	popd
	rm -rf cli
        rm -rf tanzu.tar
	pushd images
    		TKG_CUSTOM_IMAGE_REPOSITORY_CA_PATH="/etc/docker/certs.d/$DNS_NAME/ca.crt" TKG_CUSTOM_IMAGE_REPOSITORY="$DNS_NAME/tkg" ./publish-tkg-images-fromtar.sh
	    	TKG_CUSTOM_IMAGE_REPOSITORY_CA_PATH="/etc/docker/certs.d/$DNS_NAME/ca.crt" TKG_CUSTOM_IMAGE_REPOSITORY="$DNS_NAME/tkg" ./publish-tkr-images-fromtar.sh
	popd
	pushd image-builder
	        ls -l *.tar | awk '{print $9}'|xargs --replace  -n1 imgpkg copy  --tar {} --to-repo $DNS_NAME/tkg/image-builder --registry-ca-cert-path /etc/docker/certs.d/$DNS_NAME/ca.crt
	popd
	rm -rf image-builder
	rm -rf images
popd
aws s3 cp "$TKG_CUSTOM_IMAGE_REPOSITORY_CA_PATH" s3://"$BUCKET_NAME"/harbor/ca.crt
