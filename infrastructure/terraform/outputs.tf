# Terraform Outputs for Splunk MCP Integration Platform
# Production Infrastructure Outputs

# VPC and Networking Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "database_subnet_ids" {
  description = "IDs of the database subnets"
  value       = aws_subnet.database[*].id
}

output "nat_gateway_ids" {
  description = "IDs of the NAT gateways"
  value       = aws_nat_gateway.main[*].id
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

# EKS Cluster Outputs
output "cluster_id" {
  description = "EKS cluster ID"
  value       = aws_eks_cluster.main.id
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = aws_eks_cluster.main.arn
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
}

output "cluster_iam_role_name" {
  description = "IAM role name associated with EKS cluster"
  value       = aws_iam_role.eks_cluster.name
}

output "cluster_iam_role_arn" {
  description = "IAM role ARN associated with EKS cluster"
  value       = aws_iam_role.eks_cluster.arn
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = aws_eks_cluster.main.certificate_authority[0].data
}

output "cluster_version" {
  description = "The Kubernetes version for the EKS cluster"
  value       = aws_eks_cluster.main.version
}

output "cluster_platform_version" {
  description = "Platform version for the EKS cluster"
  value       = aws_eks_cluster.main.platform_version
}

output "cluster_status" {
  description = "Status of the EKS cluster"
  value       = aws_eks_cluster.main.status
}

# EKS Node Group Outputs
output "node_group_arn" {
  description = "Amazon Resource Name (ARN) of the EKS Node Group"
  value       = aws_eks_node_group.main.arn
}

output "node_group_status" {
  description = "Status of the EKS Node Group"
  value       = aws_eks_node_group.main.status
}

output "node_group_capacity_type" {
  description = "Type of capacity associated with the EKS Node Group"
  value       = aws_eks_node_group.main.capacity_type
}

output "node_group_instance_types" {
  description = "Set of instance types associated with the EKS Node Group"
  value       = aws_eks_node_group.main.instance_types
}

output "node_group_ami_type" {
  description = "Type of Amazon Machine Image (AMI) associated with the EKS Node Group"
  value       = aws_eks_node_group.main.ami_type
}

output "node_group_disk_size" {
  description = "Disk size in GiB for worker nodes"
  value       = aws_eks_node_group.main.disk_size
}

output "node_group_iam_role_name" {
  description = "IAM role name associated with EKS node group"
  value       = aws_iam_role.eks_nodes.name
}

output "node_group_iam_role_arn" {
  description = "IAM role ARN associated with EKS node group"
  value       = aws_iam_role.eks_nodes.arn
}

# Database Outputs
output "rds_hostname" {
  description = "RDS instance hostname"
  value       = aws_db_instance.main.address
  sensitive   = true
}

output "rds_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "rds_username" {
  description = "RDS instance root username"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "rds_database_name" {
  description = "RDS instance database name"
  value       = aws_db_instance.main.db_name
}

output "rds_instance_id" {
  description = "RDS instance ID"
  value       = aws_db_instance.main.id
}

output "rds_instance_arn" {
  description = "RDS instance ARN"
  value       = aws_db_instance.main.arn
}

output "rds_engine_version" {
  description = "RDS instance engine version"
  value       = aws_db_instance.main.engine_version
}

output "rds_security_group_id" {
  description = "Security group ID for RDS instance"
  value       = aws_security_group.rds.id
}

# Redis Outputs
output "redis_primary_endpoint" {
  description = "Redis primary endpoint"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
  sensitive   = true
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.main.port
}

output "redis_security_group_id" {
  description = "Security group ID for Redis cluster"
  value       = aws_security_group.elasticache.id
}

output "redis_replication_group_id" {
  description = "Redis replication group identifier"
  value       = aws_elasticache_replication_group.main.id
}

output "redis_configuration_endpoint" {
  description = "Redis configuration endpoint"
  value       = aws_elasticache_replication_group.main.configuration_endpoint_address
  sensitive   = true
}

# Security Outputs
output "kms_key_id" {
  description = "The globally unique identifier for the KMS key"
  value       = aws_kms_key.splunk_mcp.key_id
}

output "kms_key_arn" {
  description = "The Amazon Resource Name (ARN) of the KMS key"
  value       = aws_kms_key.splunk_mcp.arn
}

output "kms_alias_name" {
  description = "The display name of the KMS key alias"
  value       = aws_kms_alias.splunk_mcp.name
}

# Secrets Manager Outputs
output "database_secret_arn" {
  description = "ARN of the database credentials secret"
  value       = aws_secretsmanager_secret.database.arn
  sensitive   = true
}

output "redis_secret_arn" {
  description = "ARN of the Redis credentials secret"
  value       = aws_secretsmanager_secret.redis.arn
  sensitive   = true
}

# ECR Outputs
output "ecr_repository_urls" {
  description = "URLs of the ECR repositories"
  value = {
    for k, v in aws_ecr_repository.repositories : k => v.repository_url
  }
}

output "ecr_repository_arns" {
  description = "ARNs of the ECR repositories"
  value = {
    for k, v in aws_ecr_repository.repositories : k => v.arn
  }
}

# S3 Outputs
output "s3_bucket_id" {
  description = "The name of the S3 bucket"
  value       = aws_s3_bucket.app_data.id
}

output "s3_bucket_arn" {
  description = "The ARN of the S3 bucket"
  value       = aws_s3_bucket.app_data.arn
}

output "s3_bucket_domain_name" {
  description = "The bucket domain name"
  value       = aws_s3_bucket.app_data.bucket_domain_name
}

output "s3_bucket_regional_domain_name" {
  description = "The bucket region-specific domain name"
  value       = aws_s3_bucket.app_data.bucket_regional_domain_name
}

# Security Group Outputs
output "eks_cluster_security_group_id" {
  description = "Security group ID for EKS cluster"
  value       = aws_security_group.eks_cluster.id
}

output "eks_nodes_security_group_id" {
  description = "Security group ID for EKS nodes"
  value       = aws_security_group.eks_nodes.id
}

# Region and Availability Zone Outputs
output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "availability_zones" {
  description = "List of availability zones used"
  value       = local.availability_zones
}

# Configuration for kubectl
output "kubectl_config" {
  description = "kubectl config as a string"
  value = templatefile("${path.module}/templates/kubeconfig.tpl", {
    cluster_name     = aws_eks_cluster.main.name
    cluster_endpoint = aws_eks_cluster.main.endpoint
    cluster_ca       = aws_eks_cluster.main.certificate_authority[0].data
    aws_region       = var.aws_region
  })
  sensitive = true
}

# Kubernetes connection information
output "kubernetes_host" {
  description = "Kubernetes API server endpoint"
  value       = aws_eks_cluster.main.endpoint
  sensitive   = true
}

output "kubernetes_cluster_ca_certificate" {
  description = "Kubernetes cluster CA certificate"
  value       = aws_eks_cluster.main.certificate_authority[0].data
  sensitive   = true
}

# Resource tags
output "common_tags" {
  description = "Common tags applied to all resources"
  value       = local.common_tags
}

# Environment information
output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "project_name" {
  description = "Project name"
  value       = var.project_name
}

# DNS and networking information for application configuration
output "vpc_dns_hostnames_enabled" {
  description = "Whether or not the VPC has DNS hostname support"
  value       = aws_vpc.main.enable_dns_hostnames
}

output "vpc_dns_support_enabled" {
  description = "Whether or not the VPC has DNS support"
  value       = aws_vpc.main.enable_dns_support
}

# Cost information
output "estimated_monthly_cost" {
  description = "Estimated monthly cost for the infrastructure (USD)"
  value = "Estimated cost: EKS Cluster ($72), RDS PostgreSQL ($200-400), ElastiCache Redis ($150-300), EC2 Nodes ($200-600), NAT Gateways ($135), Total: $750-1500/month"
}

# Backup information
output "rds_backup_retention_period" {
  description = "RDS backup retention period"
  value       = aws_db_instance.main.backup_retention_period
}

output "rds_backup_window" {
  description = "RDS backup window"
  value       = aws_db_instance.main.backup_window
}

output "redis_snapshot_retention_limit" {
  description = "Redis snapshot retention limit"
  value       = aws_elasticache_replication_group.main.snapshot_retention_limit
}

output "redis_snapshot_window" {
  description = "Redis snapshot window"
  value       = aws_elasticache_replication_group.main.snapshot_window
}

# Monitoring endpoints
output "cloudwatch_log_group_names" {
  description = "CloudWatch log group names"
  value = [
    aws_cloudwatch_log_group.eks_cluster.name
  ]
}

# Quick start commands
output "quick_start_commands" {
  description = "Quick start commands for accessing the infrastructure"
  value = {
    update_kubeconfig = "aws eks update-kubeconfig --region ${var.aws_region} --name ${aws_eks_cluster.main.name}"
    get_database_secret = "aws secretsmanager get-secret-value --secret-id ${aws_secretsmanager_secret.database.arn} --region ${var.aws_region}"
    get_redis_secret = "aws secretsmanager get-secret-value --secret-id ${aws_secretsmanager_secret.redis.arn} --region ${var.aws_region}"
    ecr_login = "aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${split("/", values(aws_ecr_repository.repositories)[0].repository_url)[0]}"
  }
}