#!/bin/bash

export STATUS_FILE=/opt/vmware/arcas/boot/firstboot_status_flags.cfg

create_firstboot_file() {
	if [[ -f "/opt/vmware/arcas/boot/firstboot_status_flags.cfg" ]]; then return; fi
	mkdir -p /opt/vmware/arcas/boot
	install -m 600 -g arcas -o root /dev/null /opt/vmware/arcas/boot/firstboot_status_flags.cfg
}


buildnumber()
{
    echo "`date`*********** Build Version Storing in /root/buildnumber.cfg file ***********"
    rpm -qa | grep 'arcas' > /root/buildnumber.cfg
}

link_resolve_conf_file()
{
	echo "`date`*********** INIT link_resolve_conf_file ***********"
	sudo ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf
	cat /etc/resolv.conf | grep nameserver
	echo "`date`*********** DONE link_resolve_conf_file ***********"
}

start_docker()
{
	echo "`date`*********** Starting Docker Service ***********"
	systemctl enable docker
	systemctl start docker
	systemctl status docker
	echo "`date`*********** Docker started successfully. See 'journalctl -f -u docker' for logs ***********"
}

save_sensitive_ovf_properties_in_file() {
	if grep -Fxq "generate.secrets=true" $STATUS_FILE; then return; fi
	# It should run only once as part of firstboot script.
	echo "$(date)*********** Saving ovf properties in a safe location ***********"
	if [[ ! -f "/etc/.secrets/encryption_password" ]]; then
		install -g arcas -o root -m 500 -d /etc/.secrets
		echo "$(/opt/vmware/bin/ovfenv --key sivt.password)" >/etc/.secrets/root_password
		chmod -R 400 /etc/.secrets/*
		chown -R admin:sudo /etc/.secrets/*
		# clear_sensitive_ovf_properties
		echo "generate.secrets=true" >>/opt/vmware/arcas/boot/firstboot_status_flags.cfg
	fi
	echo "$(date)*********** Properties Saved ***********"
}

clear_sensitive_ovf_properties() {
	if grep -Fxq "mask_secrets=true" $STATUS_FILE; then return; fi
	# WARNING: It should run only as part of firstboot script.
	echo "$(date)*********** Clearing sensitive properties ***********"
	/opt/vmware/bin/ovfenv -q --key sivt.password --value '' || true
	echo "mask_secrets=true" >>/opt/vmware/arcas/boot/firstboot_status_flags.cfg
	echo "$(date)*********** Cleared sensitive properties ***********"
}


configure_password() {
	echo "$(date)**********Starting Changing root Password**********"
	chage -l root
	echo 'Temporarily disabling password strength checks...'
	cp -a /etc/pam.d/system-password /etc/pam.d/system-password.bak

	echo "$(date)*********** Starting create password for Service installer root users ***********"
	echo root:$(cat /etc/.secrets/root_password) | /usr/sbin/chpasswd
	echo "$(date)*********** Completed password creation for Service installer root user ***********"

	echo 'Re-enabling password strength checks...'
	cp -f -a /etc/pam.d/system-password.bak /etc/pam.d/system-password
	rm -f /etc/pam.d/system-password.bak
	chage -l root
	chage -d $(date -I) root
	chage -M 180 root
	chage -l root
}


configure_ntp()
{
    echo "`date`********** Configuring NTP **********"
    ntpsrv=`/opt/vmware/bin/ovfenv --key appliance.ntp`
    if [[ "$?" -eq 0 ]]
    then
       if [[ -n $ntpsrv ]]
       then
          echo "Setting NTP to "$ntpsrv""
          configFile=/etc/systemd/timesyncd.conf
          sed -i "/#NTP=/d"  $configFile
          echo "NTP=$ntpsrv" >> $configFile
          systemctl restart systemd-timesyncd
       fi
    fi
    echo "`date`********** Finished NTP Configuration **********"
}

restart_and_enable_ssh()
{
	echo "`date`*********** Enabling SSH ***********"
	systemctl restart sshd && echo 'Started sshd service'
	systemctl enable sshd && echo 'Enabled sshd service'
	echo "`date`*********** Successfully Enabled SSH ***********"
}

start_services()
{
  cp /opt/vmware/arcas/tools/arcas.service  /etc/systemd/system
	echo "`date`*********** Start Services ***********"
	systemctl daemon-reload
	systemctl enable arcas.service
	systemctl start arcas.service
	echo "`date`*********** Status of Services ***********"
	systemctl status arcas.service
}

add_initial_banner()
{
	echo "`date`*********** Setting SSH Banner in /etc/ssh/sshd-banner ***********"
	echo "###############################################################
#           THIS SYSTEM IS FOR AUTHORIZED USE ONLY!           #
#=============================================================#
#========================= WARNING ===========================#
#=============================================================#
#                   Authorized Access Only!                   #
#  Disconnect IMMEDIATELY if you are not an authorized user!  #
#         All actions will be monitored and recorded!         #
# Unauthorized use of this system is prohibited and Violators #
#   may also be subject to civil and/or criminal penalties.   #
###############################################################" > /etc/ssh/sshd-banner
	echo "Banner /etc/ssh/sshd-banner" >> /etc/ssh/sshd_config
}

add_ssh_banner_and_welcome_message()
{
	echo "`date`*********** Setting SSH Banner in /etc/issue ***********"
	# Update login message
    mv -f /etc/issue /etc/issue.orig
    echo "###############################################################
#           THIS SYSTEM IS FOR AUTHORIZED USE ONLY!           #
#=============================================================#
#========================= WARNING ===========================#
#=============================================================#
#                   Authorized Access Only!                   #
#  Disconnect IMMEDIATELY if you are not an authorized user!  #
#         All actions will be monitored and recorded!         #
# Unauthorized use of this system is prohibited and Violators #
#   may also be subject to civil and/or criminal penalties.   #
###############################################################" > /etc/issue
	systemctl restart sshd
	echo "Updating Welcome message in /etc/motd file"
	echo "###############################################################
#                 Welcome to Project ARCAS                     #
###############################################################
#                                                             #
#                   Think before you type!                    #
#  Remember That With Great Power Comes Great Responsibility  #
#                                                             #
###############################################################" > /etc/motd
	echo "`date`*********** Add SSH Banner and Welcome Message Done ***********"
}

add_welcome_message()
{
	echo "Updating Welcome message in /etc/motd file"
	echo "########################################################################
#   Welcome to Service Installer for VMware Tanzu  `arcas --version` #
########################################################################
       Installed packages are:
       Packages                      Version
       --------------------------------------
       Tanzu                           `tanzu version | grep version | awk '{split($0,a,":");print FS a[2]}'`
       tmc                             `tmc version | awk '{split($0,a,":");print FS a[2]}'`
       docker                `docker version | grep Version -m 1 | awk '{split($0,a,":");print FS a[2]}'`
       docker-compose                   `docker-compose version | grep version -m 1 | awk '{split($0,a," ");print FS a[3]}' | sed 's/,//g'`
       fzf                               `fzf --version`
       govc                             `govc version | sed 's/govc//g'`
       helm                             `helm version | awk '{split($1,a,":");print FS a[2]}' | sed 's/",//g' | sed 's/"//g'`
       jq                                `jq --version`
       k9s                          `k9s version | grep Version | awk '{split($0,a,":");print FS a[2]}'`
       kind                             `kind version | awk '{split($0,a," ");print FS a[2]}'`
       kube-ps1                          0.7.0
       kubectl                          `kubectl version | awk '{split($0,a,":");print FS a[5]}' | sed 's/+vmware.1", GitCommit//g' | sed 's/"//g'`
       kubectx                           `kubectx --version`
       octant                         `octant version |  grep Version | awk '{split($0,a,":");print FS a[2]}'`
       pinniped                          v0.15.0
       tekton                          `tkn version  | grep 'Client version' | awk '{split($0,a,":");print FS a[2]}'`
       velero                            1.7.2
       yq                               `yq --version | grep yq | awk '{split($0,a," ");print FS a[4]}'`

###############################################################" > /etc/motd
	echo "`date`*********** Add  Welcome Message Done ***********"
}

configure_ssh()
{
	echo "`date`*********** Configuring SSH ***********"
	usermod -G wheel -a root
	# Enable ssh root login
	sed -e 's|^PermitRootLogin.*|PermitRootLogin yes|g' /etc/ssh/sshd_config --in-place
	sed -i 's|^PermitRootLogin no|PermitRootLogin yes|g' /etc/ssh/sshd_config
	/usr/bin/ssh-keygen -A
	echo "`date`*********** Succcessfully Configured SSH ***********"
}

open_ports()
{
	echo "`date`*********** Opening Port in iptables ***********"
	# Open Ports in iptables
	iptables -A OUTPUT -p icmp -j ACCEPT
	iptables -A INPUT -p icmp -j ACCEPT
	iptables -A INPUT -p tcp --dport 22 -j ACCEPT
	iptables -A INPUT -p tcp --dport 8888 -j ACCEPT
	iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
	iptables -A INPUT -p tcp --dport 443 -j ACCEPT
	echo "`date`*********** Succcessfully Opended Ports in iptables ***********"
}

start_nginx()
{
	echo "`date`starting nginx"
	mkdir -p /log/arcas/nginx
	mkdir -p /data/logs/nginx
	tar -xvf /opt/vmware/arcas-ui.tar --directory /opt/vmware
	rm -rf /opt/vmware/arcas-ui.tar
	cp /opt/vmware/arcas/tools/arcas-ui.service  /etc/systemd/system
	cp /opt/vmware/arcas/tools/arcas-ui-service.conf  /etc/systemd/system
	systemctl daemon-reload
	systemctl start nginx.service
	systemctl enable nginx.service
	systemctl status nginx.service
	systemctl enable arcas-ui.service
	systemctl start arcas-ui.service
	systemctl status arcas-ui.service
	echo "`date`nginx started successfully. See 'journalctl -f -u nginx' for logs"
}

restart_nginx() {
	echo "`date` restarting nginx"
	mkdir -p /log/arcas/nginx
	cp -r /opt/vmware/arcas/arcas-ui-service/nginx/* /etc/nginx/
	systemctl restart nginx.service
	systemctl status nginx.service
	echo "nginx restarted successfully. See journalctl -f -u nginx for logs"
}


add_psql_in_path()
{
	echo "`date`*********** Add /opt/vmware/vpostgres/12/bin to $Path ***********"
	sudo echo "PATH=$PATH:/opt/vmware/vpostgres/12/bin" >> /etc/profile 
	source /etc/profile 
	echo "`date`*********** Updated Path is $PATH ***********"
}

start_and_enable_vpostgresql()
{
	echo "`date`*********** Starting vpostgresql ***********"
	/usr/bin/systemctl start vpostgresql.service
	/usr/bin/systemctl enable vpostgresql.service
	/usr/bin/systemctl status vpostgresql.service
	echo "`date`*********** vpostgresql started successfully. See journalctl -f -u vpostgresql for logs ***********"
}

enable_harbor()
{
	echo "`date`*********** Restart and Enable Harbor ***********"
	/usr/bin/systemctl restart harbor.service
	/usr/bin/systemctl enable harbor.service
	/usr/bin/systemctl status harbor.service
}

generate_self_signed_certificate_if_not_exists()
{
	mkdir -p /etc/ssl/
	if [[ ! -f "/etc/ssl/app.pem" ]]; then
	    echo "`date`**********Generating self signed certificate**********"

	    app_ip="$(ifconfig | grep -A 1 '^eth0' | tail -1 | cut -d ':' -f 2 | cut -d ' ' -f 1)"
        hostName="$(hostname)"
        printf "%s\n\n[SAN]\nsubjectAltName='DNS:${hostName},IP:${app_ip}'" "$(cat /etc/ssl/openssl.cnf)" > /tmp/arcasssl.cnf
		openssl req -newkey rsa:2048 -days 3650 -nodes -x509 -subj "/C=US/ST=California/L=Palo Alto/O=VMware/OU=VMware ARCAS" \
		    -extensions SAN -config /tmp/arcasssl.cnf -keyout /etc/ssl/app.key -out /etc/ssl/app.crt
        cat /etc/ssl/app.key /etc/ssl/app.crt > /etc/ssl/app.pem
        chmod 600 /etc/ssl/app.pem
        chmod 600 /etc/ssl/app.key
        chmod 600 /etc/ssl/app.crt

		echo "`date`**********Finished generating self signed certificate**********"
	fi

	echo "`date`**********dhparam**********"
	if [[ ! -f "/etc/ssl/dhparam.pem" ]]; then
		openssl dhparam -out /etc/ssl/dhparam.pem 2048
		chmod 600 /etc/ssl/dhparam.pem
	fi
}

replace_nginx_certificate()
{
	echo "`date` - replace_nginx_certificate"
	sed -i "s/ssl_certificate \/etc\/ssl\/app.pem/ssl_certificate \/opt\/vmware\/arcas\/cert\/provider-api-cert.pem/g" /etc/nginx/snippets/ssl-cert.conf
	sed -i "s/ssl_certificate_key \/etc\/ssl\/app.pem/ssl_certificate_key \/opt\/vmware\/arcas\/cert\/provider-api-key.pem/g" /etc/nginx/snippets/ssl-cert.conf
	echo "replace_nginx_certificate done."

	echo "`date` **********dhparam**********"
	mkdir -p /etc/ssl/
	if [[ ! -f "/etc/ssl/dhparam.pem" ]]; then
		openssl dhparam -out /etc/ssl/dhparam.pem 2048
		chmod 600 /etc/ssl/dhparam.pem
	fi
}
build_arcas()
{
  echo "`date`*********** Start Arcas cli build ***************"
    cd /opt/vmware/arcas && pip3 install -e .
  echo "`date`*********** Successfully built Arcas cli ***************"
}

install_python_packages()
{
  echo "`date`*********** Start install python packages ***************"
    cd /opt/vmware/arcas/tools/flask && pip3 install Flask-2.0.1-py3-none-any.whl -f ./ --no-index
    cd /opt/vmware/arcas/tools/flaskCross && pip3 install Flask_Cors-3.0.10-py2.py3-none-any.whl -f ./ --no-index
    cd /opt/vmware/arcas/tools/flaskRest && pip3 install Flask_RESTful-0.3.9-py2.py3-none-any.whl -f ./ --no-index
    cd /opt/vmware/arcas/tools/raumel && pip3 install ruamel.yaml-0.17.16-py3-none-any.whl -f ./ --no-index
    cd /opt/vmware/arcas/tools/tqdm && pip3 install tqdm-4.62.3-py2.py3-none-any.whl -f ./ --no-index
    cd /opt/vmware/arcas/tools/waitress && pip3 install waitress-2.0.0-py3-none-any.whl -f ./ --no-index
    cd /opt/vmware/arcas/tools/pydentic && pip3 install pydantic-1.9.0-cp37-cp37m-manylinux_2_17_x86_64.manylinux2014_x86_64.whl -f ./ --no-index
    cd /opt/vmware/arcas/tools/pydentic && pip3 install typing_extensions-4.0.1-py3-none-any.whl -f ./ --no-index
    cd /opt/vmware/arcas/tools/ntplib && pip3 install ntplib-0.4.0-py2.py3-none-any.whl -f ./ --no-index
  echo "`date`*********** Successfully install python packages ***************"
}

install_k_alias()
{
  echo "`date`*********** Start k alias ***************"
    echo "alias k='kubectl'" >> /etc/bash.bashrc
    source /etc/bash.bashrc
  echo "`date`*********** Successfully install  k alias ***************"
}

update_docker_dir()
{
	echo "`date`*********** Update docker dir to /docker_storage ***********"
	echo '{
  "data-root": "/docker_storage"
  }' > /etc/docker/daemon.json
	systemctl restart docker
	echo "`date`*********** Restarted docker as /etc/docker/daemon.json got created ***********"
}
