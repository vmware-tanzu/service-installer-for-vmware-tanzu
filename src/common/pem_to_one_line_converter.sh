# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

awk 'NF {sub(/\r/, ""); printf "%s\\n",$0;}' $1 >> $2
