#!/bin/sh
source /opt/vmware/arcas/bin/common.sh import functions

#Enable IPv4 forwarding for docker
sysctl net.ipv4.conf.all.forwarding=1

configure_ssh
add_ssh_banner_and_welcome_message
restart_and_enable_ssh
open_ports
restart_nginx
