# Terraform Variables for Splunk MCP Integration Platform
# Production Infrastructure Configuration

# Project Configuration
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "splunk-mcp"
}

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
  default     = "production"
  
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be production, staging, or development."
  }
}

variable "project_owner" {
  description = "Owner of the project"
  type        = string
  default     = "platform-team"
}

variable "cost_center" {
  description = "Cost center for billing"
  type        = string
  default     = "engineering"
}

# AWS Configuration
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}

variable "terraform_state_bucket" {
  description = "S3 bucket for Terraform state"
  type        = string
}

variable "terraform_lock_table" {
  description = "DynamoDB table for Terraform locking"
  type        = string
}

# Networking Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
  
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid IPv4 CIDR block."
  }
}

# EKS Configuration
variable "kubernetes_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.28"
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "List of CIDR blocks that can access the EKS cluster endpoint"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# EKS Node Group Configuration
variable "node_instance_types" {
  description = "EC2 instance types for EKS worker nodes"
  type        = list(string)
  default     = ["t3.large", "t3.xlarge"]
}

variable "node_disk_size" {
  description = "Disk size for EKS worker nodes (GB)"
  type        = number
  default     = 50
  
  validation {
    condition     = var.node_disk_size >= 20 && var.node_disk_size <= 1000
    error_message = "Node disk size must be between 20 and 1000 GB."
  }
}

variable "node_desired_size" {
  description = "Desired number of EKS worker nodes"
  type        = number
  default     = 3
  
  validation {
    condition     = var.node_desired_size >= 1 && var.node_desired_size <= 20
    error_message = "Node desired size must be between 1 and 20."
  }
}

variable "node_min_size" {
  description = "Minimum number of EKS worker nodes"
  type        = number
  default     = 1
  
  validation {
    condition     = var.node_min_size >= 1 && var.node_min_size <= 10
    error_message = "Node minimum size must be between 1 and 10."
  }
}

variable "node_max_size" {
  description = "Maximum number of EKS worker nodes"
  type        = number
  default     = 10
  
  validation {
    condition     = var.node_max_size >= 1 && var.node_max_size <= 50
    error_message = "Node maximum size must be between 1 and 50."
  }
}

# PostgreSQL RDS Configuration
variable "postgresql_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "15.4"
}

variable "postgresql_instance_class" {
  description = "RDS instance class for PostgreSQL"
  type        = string
  default     = "db.r6g.large"
  
  validation {
    condition = can(regex("^db\\.", var.postgresql_instance_class))
    error_message = "PostgreSQL instance class must be a valid RDS instance type."
  }
}

variable "postgresql_allocated_storage" {
  description = "Initial allocated storage for PostgreSQL (GB)"
  type        = number
  default     = 100
  
  validation {
    condition     = var.postgresql_allocated_storage >= 20 && var.postgresql_allocated_storage <= 10000
    error_message = "PostgreSQL allocated storage must be between 20 and 10000 GB."
  }
}

variable "postgresql_max_allocated_storage" {
  description = "Maximum allocated storage for PostgreSQL autoscaling (GB)"
  type        = number
  default     = 1000
  
  validation {
    condition     = var.postgresql_max_allocated_storage >= 100 && var.postgresql_max_allocated_storage <= 10000
    error_message = "PostgreSQL maximum allocated storage must be between 100 and 10000 GB."
  }
}

variable "postgresql_username" {
  description = "Master username for PostgreSQL"
  type        = string
  default     = "splunk_mcp_admin"
  
  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]{0,62}$", var.postgresql_username))
    error_message = "PostgreSQL username must start with a letter and contain only alphanumeric characters and underscores."
  }
}

variable "postgresql_backup_retention_period" {
  description = "Backup retention period for PostgreSQL (days)"
  type        = number
  default     = 7
  
  validation {
    condition     = var.postgresql_backup_retention_period >= 1 && var.postgresql_backup_retention_period <= 35
    error_message = "PostgreSQL backup retention period must be between 1 and 35 days."
  }
}

variable "postgresql_backup_window" {
  description = "Backup window for PostgreSQL (UTC)"
  type        = string
  default     = "03:00-04:00"
  
  validation {
    condition     = can(regex("^([01]?[0-9]|2[0-3]):[0-5][0-9]-([01]?[0-9]|2[0-3]):[0-5][0-9]$", var.postgresql_backup_window))
    error_message = "PostgreSQL backup window must be in HH:MM-HH:MM format."
  }
}

variable "postgresql_maintenance_window" {
  description = "Maintenance window for PostgreSQL (UTC)"
  type        = string
  default     = "sun:04:00-sun:05:00"
  
  validation {
    condition     = can(regex("^(mon|tue|wed|thu|fri|sat|sun):[0-2][0-9]:[0-5][0-9]-(mon|tue|wed|thu|fri|sat|sun):[0-2][0-9]:[0-5][0-9]$", var.postgresql_maintenance_window))
    error_message = "PostgreSQL maintenance window must be in day:HH:MM-day:HH:MM format."
  }
}

# Redis ElastiCache Configuration
variable "redis_node_type" {
  description = "ElastiCache node type for Redis"
  type        = string
  default     = "cache.r6g.large"
  
  validation {
    condition = can(regex("^cache\\.", var.redis_node_type))
    error_message = "Redis node type must be a valid ElastiCache instance type."
  }
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes for Redis cluster"
  type        = number
  default     = 2
  
  validation {
    condition     = var.redis_num_cache_nodes >= 1 && var.redis_num_cache_nodes <= 6
    error_message = "Redis number of cache nodes must be between 1 and 6."
  }
}

variable "redis_snapshot_retention_limit" {
  description = "Number of days to retain Redis snapshots"
  type        = number
  default     = 5
  
  validation {
    condition     = var.redis_snapshot_retention_limit >= 0 && var.redis_snapshot_retention_limit <= 35
    error_message = "Redis snapshot retention limit must be between 0 and 35 days."
  }
}

variable "redis_snapshot_window" {
  description = "Daily time range for Redis snapshots (UTC)"
  type        = string
  default     = "03:00-05:00"
  
  validation {
    condition     = can(regex("^([01]?[0-9]|2[0-3]):[0-5][0-9]-([01]?[0-9]|2[0-3]):[0-5][0-9]$", var.redis_snapshot_window))
    error_message = "Redis snapshot window must be in HH:MM-HH:MM format."
  }
}

variable "redis_maintenance_window" {
  description = "Weekly time range for Redis maintenance (UTC)"
  type        = string
  default     = "sun:05:00-sun:06:00"
  
  validation {
    condition     = can(regex("^(mon|tue|wed|thu|fri|sat|sun):[0-2][0-9]:[0-5][0-9]-(mon|tue|wed|thu|fri|sat|sun):[0-2][0-9]:[0-5][0-9]$", var.redis_maintenance_window))
    error_message = "Redis maintenance window must be in day:HH:MM-day:HH:MM format."
  }
}

# Application Configuration
variable "enable_deletion_protection" {
  description = "Enable deletion protection for critical resources"
  type        = bool
  default     = true
}

variable "enable_enhanced_monitoring" {
  description = "Enable enhanced monitoring for RDS"
  type        = bool
  default     = true
}

variable "enable_performance_insights" {
  description = "Enable Performance Insights for RDS"
  type        = bool
  default     = true
}

# Monitoring and Logging Configuration
variable "log_retention_days" {
  description = "CloudWatch log retention period (days)"
  type        = number
  default     = 14
  
  validation {
    condition = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}

variable "enable_container_insights" {
  description = "Enable CloudWatch Container Insights for EKS"
  type        = bool
  default     = true
}

# Security Configuration
variable "enable_secrets_encryption" {
  description = "Enable encryption for Kubernetes secrets"
  type        = bool
  default     = true
}

variable "enable_network_policies" {
  description = "Enable Kubernetes network policies"
  type        = bool
  default     = true
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the cluster"
  type        = list(string)
  default     = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
}

# Backup and Disaster Recovery
variable "enable_automated_backups" {
  description = "Enable automated backups for all data stores"
  type        = bool
  default     = true
}

variable "cross_region_backup" {
  description = "Enable cross-region backup replication"
  type        = bool
  default     = false
}

variable "backup_retention_period" {
  description = "Global backup retention period (days)"
  type        = number
  default     = 30
  
  validation {
    condition     = var.backup_retention_period >= 1 && var.backup_retention_period <= 365
    error_message = "Backup retention period must be between 1 and 365 days."
  }
}

# Resource Tagging
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Feature Flags
variable "enable_spot_instances" {
  description = "Enable Spot instances for non-critical workloads"
  type        = bool
  default     = false
}

variable "enable_auto_scaling" {
  description = "Enable auto-scaling for EKS node groups"
  type        = bool
  default     = true
}

variable "enable_cluster_autoscaler" {
  description = "Enable Kubernetes cluster autoscaler"
  type        = bool
  default     = true
}

# Multi-AZ Configuration
variable "multi_az_enabled" {
  description = "Enable multi-AZ deployment for high availability"
  type        = bool
  default     = true
}

variable "availability_zones" {
  description = "List of availability zones to use (if empty, uses all available)"
  type        = list(string)
  default     = []
}

# Performance Configuration
variable "enable_enhanced_networking" {
  description = "Enable enhanced networking for EC2 instances"
  type        = bool
  default     = true
}

variable "enable_ebs_optimization" {
  description = "Enable EBS optimization for EC2 instances"
  type        = bool
  default     = true
}

# Cost Optimization
variable "enable_scheduled_scaling" {
  description = "Enable scheduled scaling based on usage patterns"
  type        = bool
  default     = false
}

variable "non_production_schedule" {
  description = "Schedule for non-production environments (stop/start times)"
  type = object({
    stop_time  = string
    start_time = string
    timezone   = string
  })
  default = {
    stop_time  = "19:00"
    start_time = "08:00"
    timezone   = "UTC"
  }
}

# Application-specific Configuration
variable "api_domain_name" {
  description = "Domain name for the API gateway"
  type        = string
  default     = ""
}

variable "frontend_domain_name" {
  description = "Domain name for the frontend application"
  type        = string
  default     = ""
}

variable "ssl_certificate_arn" {
  description = "ARN of the SSL certificate for HTTPS"
  type        = string
  default     = ""
}

# External Integration Configuration
variable "splunk_integration" {
  description = "Splunk integration configuration"
  type = object({
    enabled = bool
    host    = string
    port    = number
  })
  default = {
    enabled = false
    host    = ""
    port    = 8089
  }
}

variable "external_apis" {
  description = "External API configurations"
  type = map(object({
    enabled     = bool
    endpoint    = string
    timeout     = number
    retry_count = number
  }))
  default = {
    openai = {
      enabled     = false
      endpoint    = "https://api.openai.com"
      timeout     = 30
      retry_count = 3
    }
    anthropic = {
      enabled     = false
      endpoint    = "https://api.anthropic.com"
      timeout     = 30
      retry_count = 3
    }
  }
}