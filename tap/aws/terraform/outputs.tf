# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

output "cluster_name-iterate" {
  value = aws_eks_cluster.iterate.name

}
output "cluster_name-build" {

  value = aws_eks_cluster.build.name

}

output "cluster_name-run" {

  value = aws_eks_cluster.run.name
 
}

output "cluster_name-view" {

  value = aws_eks_cluster.view.name
}

output "cluster_endpoint-iterate" {
  value = aws_eks_cluster.iterate.endpoint

}
output "cluster_endpoint-build" {

  value = aws_eks_cluster.build.endpoint

}
output "cluster_endpoint-run" {

 value = aws_eks_cluster.run.endpoint

}
output "cluster_endpoint-view" {

  value = aws_eks_cluster.view.endpoint
}

output "vpc_id" {
  value = aws_vpc.main.id
}