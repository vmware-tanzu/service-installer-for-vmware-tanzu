#!/bin/bash

source /opt/vmware/arcas/bin/common.sh import functions
source /etc/environment

main()
{
  create_firstboot_file
  save_sensitive_ovf_properties_in_file
  configure_password
  clear_sensitive_ovf_properties
	buildnumber
	configure_ntp
	link_resolve_conf_file
	start_docker
	update_docker_dir
	install_python_packages
	configure_ssh
	restart_and_enable_ssh
	open_ports
	start_services
	start_nginx
	build_arcas
	install_k_alias
	add_welcome_message
}

main
