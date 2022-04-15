#!/bin/sh

source /opt/vmware/arcas/bin/common.sh import functions


main()
{
	buildnumber
	configure_ssh
	restart_and_enable_ssh
	open_ports
	start_services
	start_nginx
}

main
