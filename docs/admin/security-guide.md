# Security Administration Guide

This guide provides comprehensive security configuration, hardening, and management procedures for the Splunk MCP Integration Platform.

## Table of Contents

1. [Security Architecture](#security-architecture)
2. [Authentication Configuration](#authentication-configuration)
3. [Authorization & Access Control](#authorization--access-control)
4. [Network Security](#network-security)
5. [Data Protection](#data-protection)
6. [Security Monitoring](#security-monitoring)
7. [Compliance & Auditing](#compliance--auditing)
8. [Incident Response](#incident-response)
9. [Security Maintenance](#security-maintenance)

---

## Security Architecture

### Defense in Depth Strategy

The platform implements multiple layers of security controls:

```
┌─────────────────────────────────────────────────────┐
│                  External Access                    │
│  ┌─────────────────────────────────────────────┐   │
│  │             Network Security                │   │
│  │  ┌─────────────────────────────────────┐   │   │
│  │  │         Application Security        │   │   │
│  │  │  ┌─────────────────────────────┐   │   │   │
│  │  │  │      Data Security          │   │   │   │
│  │  │  │  ┌─────────────────────┐   │   │   │   │
│  │  │  │  │  Infrastructure     │   │   │   │   │
│  │  │  │  │    Security         │   │   │   │   │
│  │  │  │  └─────────────────────┘   │   │   │   │
│  │  │  └─────────────────────────────┘   │   │   │
│  │  └─────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Security Principles

1. **Zero Trust Architecture**: Verify every access request
2. **Principle of Least Privilege**: Minimal necessary permissions
3. **Defense in Depth**: Multiple security layers
4. **Fail Secure**: Secure defaults and failure modes
5. **Continuous Monitoring**: Real-time security visibility

### Threat Model

#### Identified Threats
- **External Attackers**: Unauthorized access attempts
- **Insider Threats**: Malicious internal users
- **Supply Chain Attacks**: Compromised dependencies
- **Data Breaches**: Unauthorized data access
- **Service Disruption**: Availability attacks

#### Mitigations
- Multi-factor authentication
- Network segmentation
- Encryption at rest and in transit
- Audit logging and monitoring
- Regular security assessments

---

## Authentication Configuration

### JWT Token Management

#### Token Configuration
```yaml
# jwt-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: jwt-config
  namespace: splunk-mcp-prod
data:
  JWT_ALGORITHM: "RS256"  # Use asymmetric encryption for production
  JWT_ACCESS_TOKEN_EXPIRE_MINUTES: "60"
  JWT_REFRESH_TOKEN_EXPIRE_DAYS: "7"
  JWT_ISSUER: "splunk-mcp-platform"
  JWT_AUDIENCE: "splunk-mcp-users"
  JWT_NOT_BEFORE_MINUTES: "0"
  JWT_LEEWAY_SECONDS: "10"
```

#### RSA Key Generation
```bash
# Generate RSA key pair for JWT signing
openssl genrsa -out jwt-private.pem 4096
openssl rsa -in jwt-private.pem -pubout -out jwt-public.pem

# Create Kubernetes secrets
kubectl create secret generic jwt-keys \
  --from-file=private-key=jwt-private.pem \
  --from-file=public-key=jwt-public.pem \
  -n splunk-mcp-prod

# Secure the key files
chmod 600 jwt-private.pem jwt-public.pem
rm jwt-private.pem jwt-public.pem  # Remove after creating secret
```

### LDAP/Active Directory Integration

#### LDAP Configuration
```yaml
# ldap-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ldap-config
  namespace: splunk-mcp-prod
data:
  LDAP_SERVER: "ldaps://ad.company.com:636"
  LDAP_BIND_DN: "CN=splunk-mcp-service,OU=Service Accounts,DC=company,DC=com"
  LDAP_SEARCH_BASE: "OU=Users,DC=company,DC=com"
  LDAP_USER_FILTER: "(sAMAccountName={username})"
  LDAP_GROUP_FILTER: "(member={user_dn})"
  LDAP_GROUP_SEARCH_BASE: "OU=Groups,DC=company,DC=com"
  LDAP_ATTRIBUTES_MAP: |
    {
      "email": "mail",
      "first_name": "givenName",
      "last_name": "sn",
      "display_name": "displayName",
      "department": "department",
      "title": "title"
    }
  LDAP_GROUP_TYPE: "ActiveDirectoryGroupType"
  LDAP_REQUIRE_GROUP: "CN=SplunkMCP-Users,OU=Groups,DC=company,DC=com"
  LDAP_CACHE_TIMEOUT: "3600"
  LDAP_CONNECTION_TIMEOUT: "10"
  LDAP_SEARCH_TIMEOUT: "30"
```

```yaml
# ldap-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: ldap-secret
  namespace: splunk-mcp-prod
type: Opaque
data:
  password: <base64-encoded-service-account-password>
```

#### LDAP Security Best Practices
```bash
# Test LDAP connectivity securely
kubectl create job ldap-test --image=alpine/openldap-utils -n splunk-mcp-prod -- \
  ldapsearch -x -H ldaps://ad.company.com:636 \
  -D "CN=splunk-mcp-service,OU=Service Accounts,DC=company,DC=com" \
  -w "$(kubectl get secret ldap-secret -n splunk-mcp-prod -o jsonpath='{.data.password}' | base64 -d)" \
  -b "OU=Users,DC=company,DC=com" \
  "(sAMAccountName=testuser)" cn mail

# Verify SSL certificate
echo | openssl s_client -connect ad.company.com:636 -verify_return_error
```

### SAML 2.0 Configuration

#### SAML Identity Provider Setup
```yaml
# saml-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: saml-config
  namespace: splunk-mcp-prod
data:
  SAML_ENABLED: "true"
  SAML_IDP_ENTITY_ID: "https://identity.company.com/saml/metadata"
  SAML_IDP_SSO_URL: "https://identity.company.com/saml/sso"
  SAML_IDP_SLO_URL: "https://identity.company.com/saml/slo"
  SAML_SP_ENTITY_ID: "https://splunk-mcp.company.com/saml/metadata"
  SAML_SP_ACS_URL: "https://splunk-mcp.company.com/saml/acs"
  SAML_SP_SLS_URL: "https://splunk-mcp.company.com/saml/sls"
  SAML_ATTRIBUTE_MAPPING: |
    {
      "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
      "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
      "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
      "groups": "http://schemas.xmlsoap.org/claims/Group"
    }
  SAML_SIGNATURE_ALGORITHM: "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
  SAML_DIGEST_ALGORITHM: "http://www.w3.org/2001/04/xmlenc#sha256"
```

#### SAML Certificate Management
```bash
# Generate SAML signing certificate
openssl req -new -x509 -days 3652 -nodes -out saml-cert.crt -keyout saml-key.key \
  -subj "/C=US/ST=State/L=City/O=Organization/OU=IT/CN=splunk-mcp.company.com"

# Create secret for SAML certificates
kubectl create secret tls saml-certs \
  --cert=saml-cert.crt \
  --key=saml-key.key \
  -n splunk-mcp-prod

# Secure certificate files
chmod 600 saml-cert.crt saml-key.key
rm saml-cert.crt saml-key.key
```

### Multi-Factor Authentication

#### TOTP Configuration
```yaml
# mfa-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mfa-config
  namespace: splunk-mcp-prod
data:
  MFA_ENABLED: "true"
  MFA_REQUIRED_FOR_ADMIN: "true"
  MFA_GRACE_PERIOD: "86400"  # 24 hours
  MFA_ISSUER_NAME: "Splunk MCP Platform"
  MFA_TOKEN_VALIDITY: "300"  # 5 minutes
  MFA_BACKUP_CODES_COUNT: "10"
  MFA_RATE_LIMIT: "5"  # 5 attempts per minute
```

#### SMS/Email MFA Setup
```yaml
# mfa-providers.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mfa-providers
  namespace: splunk-mcp-prod
data:
  SMS_PROVIDER: "twilio"
  EMAIL_PROVIDER: "smtp"
  SMS_TOKEN_LENGTH: "6"
  EMAIL_TOKEN_LENGTH: "8"
  TOKEN_EXPIRY_MINUTES: "5"
  MAX_ATTEMPTS: "3"
```

---

## Authorization & Access Control

### Role-Based Access Control (RBAC)

#### Default Platform Roles
```yaml
# platform-roles.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: splunk-mcp-prod
  name: platform-admin
rules:
- apiGroups: [""]
  resources: ["*"]
  verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: splunk-mcp-prod
  name: platform-power-user
rules:
- apiGroups: [""]
  resources: ["dashboards", "alerts", "reports", "queries"]
  verbs: ["get", "list", "create", "update", "delete"]
- apiGroups: [""]
  resources: ["exports"]
  verbs: ["get", "list", "create"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: splunk-mcp-prod
  name: platform-analyst
rules:
- apiGroups: [""]
  resources: ["dashboards", "queries"]
  verbs: ["get", "list", "create", "update"]
- apiGroups: [""]
  resources: ["alerts", "reports"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: splunk-mcp-prod
  name: platform-viewer
rules:
- apiGroups: [""]
  resources: ["dashboards", "reports"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["queries"]
  verbs: ["get", "list", "create"]
```

#### Custom Role Creation
```bash
# Create custom security analyst role
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: splunk-mcp-prod
  name: security-analyst
rules:
- apiGroups: [""]
  resources: ["security-dashboards", "security-alerts", "incident-reports"]
  verbs: ["get", "list", "create", "update"]
- apiGroups: [""]
  resources: ["threat-queries", "investigation-reports"]
  verbs: ["get", "list", "create", "update", "delete"]
- apiGroups: [""]
  resources: ["compliance-reports"]
  verbs: ["get", "list"]
EOF

# Bind role to security team group
kubectl create rolebinding security-analysts \
  --role=security-analyst \
  --group="CN=Security-Team,OU=Groups,DC=company,DC=com" \
  -n splunk-mcp-prod
```

### Fine-Grained Permissions

#### Data Source Access Control
```yaml
# data-access-policy.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: data-access-policy
  namespace: splunk-mcp-prod
data:
  policy.json: |
    {
      "default_policy": "deny",
      "user_policies": {
        "security_analysts": {
          "indexes": ["security", "firewall", "ids"],
          "sourcetypes": ["cisco:asa", "snort", "windows:security"],
          "time_range_limit": "90d"
        },
        "it_operations": {
          "indexes": ["main", "infrastructure", "applications"],
          "sourcetypes": ["syslog", "apache", "nginx"],
          "time_range_limit": "30d"
        },
        "business_analysts": {
          "indexes": ["business", "sales", "marketing"],
          "sourcetypes": ["csv", "json", "database"],
          "time_range_limit": "365d"
        }
      },
      "field_restrictions": {
        "sensitive_fields": ["ssn", "credit_card", "password"],
        "redaction_rules": {
          "ssn": "XXX-XX-****",
          "credit_card": "****-****-****-****"
        }
      }
    }
```

#### Time-Based Access Controls
```yaml
# time-based-access.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: time-based-access
  namespace: splunk-mcp-prod
data:
  access_schedule.json: |
    {
      "business_hours": {
        "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "start_time": "08:00",
        "end_time": "18:00",
        "timezone": "America/New_York"
      },
      "role_schedules": {
        "contractors": {
          "allowed_hours": "business_hours",
          "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
        },
        "emergency_responders": {
          "allowed_hours": "24x7",
          "bypass_restrictions": true
        }
      },
      "holiday_restrictions": {
        "restricted_roles": ["contractors", "interns"],
        "holiday_calendar": "us_federal"
      }
    }
```

### Splunk Integration Security

#### Service Account Configuration
```bash
# Create dedicated Splunk service account
splunk_host="splunk.company.com"
admin_user="admin"
admin_pass="admin_password"

# Create service account
curl -k -u "$admin_user:$admin_pass" \
  -d "name=splunk-mcp-service" \
  -d "password=$(openssl rand -base64 32)" \
  -d "roles=splunk_mcp_role" \
  -d "email=splunk-mcp@company.com" \
  "https://$splunk_host:8089/servicesNS/admin/search/authentication/users"

# Create custom role with minimal permissions
curl -k -u "$admin_user:$admin_pass" \
  -d "name=splunk_mcp_role" \
  -d "capabilities=search,list_search_head_clustering" \
  -d "srchIndexesAllowed=main,security,application" \
  -d "srchIndexesDefault=main" \
  -d "rtSrchJobsQuota=10" \
  -d "srchJobsQuota=50" \
  -d "srchTimeWin=86400" \
  "https://$splunk_host:8089/servicesNS/admin/search/authorization/roles"
```

#### API Token Management
```bash
# Generate API token for service account
token_response=$(curl -k -u "splunk-mcp-service:service_password" \
  -d "name=platform-integration" \
  -d "audience=platform" \
  "https://$splunk_host:8089/services/authorization/tokens")

# Extract token
api_token=$(echo "$token_response" | xmllint --xpath "//s:key[@name='token']/text()" -)

# Store token securely
kubectl create secret generic splunk-api-token \
  --from-literal=token="$api_token" \
  -n splunk-mcp-prod
```

---

## Network Security

### Network Segmentation

#### Network Policies Implementation
```yaml
# network-policies.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-default
  namespace: splunk-mcp-prod
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-api
  namespace: splunk-mcp-prod
spec:
  podSelector:
    matchLabels:
      app: api-gateway
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-to-services
  namespace: splunk-mcp-prod
spec:
  podSelector:
    matchLabels:
      tier: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8001
    - protocol: TCP
      port: 8002
    - protocol: TCP
      port: 8003
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-database-access
  namespace: splunk-mcp-prod
spec:
  podSelector:
    matchLabels:
      app: postgresql
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: backend
    ports:
    - protocol: TCP
      port: 5432
```

#### Firewall Rules
```bash
# Example iptables rules for additional protection
# Block all traffic by default
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow Kubernetes API server
iptables -A INPUT -p tcp --dport 6443 -s 10.0.0.0/8 -j ACCEPT

# Allow HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Allow SSH (restrict to management network)
iptables -A INPUT -p tcp --dport 22 -s 192.168.1.0/24 -j ACCEPT

# Log dropped packets
iptables -A INPUT -j LOG --log-prefix "DROPPED: "
```

### SSL/TLS Security

#### TLS Configuration
```yaml
# tls-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tls-config
  namespace: splunk-mcp-prod
data:
  TLS_MIN_VERSION: "1.2"
  TLS_MAX_VERSION: "1.3"
  TLS_CIPHER_SUITES: |
    TLS_AES_256_GCM_SHA384
    TLS_CHACHA20_POLY1305_SHA256
    TLS_AES_128_GCM_SHA256
    TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
    TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305
    TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
  TLS_CURVES: |
    X25519
    secp256r1
    secp384r1
  TLS_HSTS_MAX_AGE: "31536000"
  TLS_HSTS_INCLUDE_SUBDOMAINS: "true"
  TLS_HSTS_PRELOAD: "true"
```

#### Certificate Security
```bash
# Generate strong certificates
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -days 365 -key ca-key.pem -sha256 -out ca.pem \
  -subj "/C=US/ST=CA/L=San Francisco/O=Company/CN=CA"

# Generate service certificate
openssl genrsa -out server-key.pem 4096
openssl req -subj "/CN=splunk-mcp.company.com" -sha256 -new -key server-key.pem -out server.csr

# Sign certificate
openssl x509 -req -days 365 -sha256 -in server.csr -CA ca.pem -CAkey ca-key.pem \
  -out server-cert.pem -extensions v3_req -extfile <(
echo '[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names
[alt_names]
DNS.1 = splunk-mcp.company.com
DNS.2 = *.splunk-mcp.company.com
IP.1 = 10.0.0.1'
)

# Create TLS secret
kubectl create secret tls platform-tls \
  --cert=server-cert.pem \
  --key=server-key.pem \
  -n splunk-mcp-prod
```

### API Security

#### Rate Limiting Configuration
```yaml
# rate-limiting.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rate-limiting-config
  namespace: splunk-mcp-prod
data:
  rate_limits.json: |
    {
      "global": {
        "requests_per_minute": 1000,
        "burst_limit": 2000
      },
      "per_user": {
        "requests_per_minute": 100,
        "burst_limit": 200
      },
      "per_ip": {
        "requests_per_minute": 200,
        "burst_limit": 400
      },
      "endpoints": {
        "/api/v1/auth/login": {
          "requests_per_minute": 10,
          "burst_limit": 20
        },
        "/api/v1/search": {
          "requests_per_minute": 30,
          "burst_limit": 60
        },
        "/api/v1/export": {
          "requests_per_minute": 5,
          "burst_limit": 10
        }
      },
      "whitelist": [
        "10.0.0.0/8",
        "192.168.1.0/24"
      ]
    }
```

#### API Security Headers
```yaml
# security-headers.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: security-headers
  namespace: splunk-mcp-prod
data:
  security_headers.json: |
    {
      "X-Content-Type-Options": "nosniff",
      "X-Frame-Options": "DENY",
      "X-XSS-Protection": "1; mode=block",
      "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
      "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'",
      "Referrer-Policy": "strict-origin-when-cross-origin",
      "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
    }
```

---

## Data Protection

### Encryption at Rest

#### Database Encryption
```yaml
# postgres-encrypted.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgresql-encrypted
  namespace: splunk-mcp-prod
spec:
  serviceName: postgresql
  template:
    spec:
      containers:
      - name: postgresql
        image: postgres:15
        env:
        - name: POSTGRES_INITDB_ARGS
          value: "--data-checksums --auth-host=scram-sha-256"
        - name: POSTGRES_HOST_AUTH_METHOD
          value: "scram-sha-256"
        volumeMounts:
        - name: postgresql-storage
          mountPath: /var/lib/postgresql/data
        - name: postgresql-config
          mountPath: /etc/postgresql/postgresql.conf
          subPath: postgresql.conf
      initContainers:
      - name: setup-encryption
        image: postgres:15
        command:
        - /bin/bash
        - -c
        - |
          # Enable transparent data encryption
          echo "ssl = on" >> /etc/postgresql/postgresql.conf
          echo "ssl_cert_file = '/etc/ssl/certs/server.crt'" >> /etc/postgresql/postgresql.conf
          echo "ssl_key_file = '/etc/ssl/private/server.key'" >> /etc/postgresql/postgresql.conf
          echo "ssl_ciphers = 'HIGH:!aNULL:!MD5'" >> /etc/postgresql/postgresql.conf
```

#### File System Encryption
```bash
# Set up encrypted storage class
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: encrypted-ssd
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  encrypted: "true"
  kmsKeyId: "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012"
reclaimPolicy: Retain
allowVolumeExpansion: true
EOF
```

### Encryption in Transit

#### Internal Service Communication
```yaml
# service-mesh-tls.yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: splunk-mcp-prod
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: default
  namespace: splunk-mcp-prod
spec:
  host: "*.local"
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
```

### Secrets Management

#### Kubernetes Secrets Encryption
```yaml
# encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
- resources:
  - secrets
  providers:
  - aescbc:
      keys:
      - name: key1
        secret: <base64-encoded-32-byte-key>
  - identity: {}
```

#### External Secret Management
```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets --create-namespace

# Configure AWS Secrets Manager integration
cat <<EOF | kubectl apply -f -
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: splunk-mcp-prod
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: platform-secrets
  namespace: splunk-mcp-prod
spec:
  refreshInterval: 15m
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: app-secrets
    creationPolicy: Owner
  data:
  - secretKey: jwt-secret-key
    remoteRef:
      key: splunk-mcp/jwt-secret
  - secretKey: database-password
    remoteRef:
      key: splunk-mcp/database-password
EOF
```

### Data Loss Prevention

#### Sensitive Data Detection
```python
# dlp-scanner.py
import re
import hashlib

class DLPScanner:
    def __init__(self):
        self.patterns = {
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}-\d{3}-\d{4}\b',
            'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        }
    
    def scan_text(self, text):
        findings = {}
        for pattern_name, pattern in self.patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                findings[pattern_name] = len(matches)
        return findings
    
    def redact_text(self, text):
        for pattern_name, pattern in self.patterns.items():
            if pattern_name == 'ssn':
                text = re.sub(pattern, 'XXX-XX-XXXX', text)
            elif pattern_name == 'credit_card':
                text = re.sub(pattern, 'XXXX-XXXX-XXXX-XXXX', text)
        return text
```

---

## Security Monitoring

### Security Information and Event Management (SIEM)

#### Log Aggregation Configuration
```yaml
# security-logging.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: security-logging-config
  namespace: splunk-mcp-prod
data:
  fluent.conf: |
    <source>
      @type kubernetes_metadata_filter
      @id filter_kube_metadata
      kubernetes_url "#{ENV['FLUENT_FILTER_KUBERNETES_URL'] || 'https://' + ENV['KUBERNETES_SERVICE_HOST'] + ':' + ENV['KUBERNETES_SERVICE_PORT'] + '/api'}"
      verify_ssl "#{ENV['KUBERNETES_VERIFY_SSL'] || true}"
      ca_file "#{ENV['KUBERNETES_CA_FILE']}"
      skip_labels "#{ENV['FLUENT_KUBERNETES_METADATA_SKIP_LABELS'] || 'false'}"
      skip_container_metadata "#{ENV['FLUENT_KUBERNETES_METADATA_SKIP_CONTAINER_METADATA'] || 'false'}"
      skip_master_url "#{ENV['FLUENT_KUBERNETES_METADATA_SKIP_MASTER_URL'] || 'false'}"
      skip_namespace_metadata "#{ENV['FLUENT_KUBERNETES_METADATA_SKIP_NAMESPACE_METADATA'] || 'false'}"
    </source>
    
    <filter kubernetes.**>
      @type parser
      key_name log
      reserve_data true
      <parse>
        @type json
        time_key timestamp
        time_format %Y-%m-%dT%H:%M:%S.%NZ
      </parse>
    </filter>
    
    <filter kubernetes.var.log.containers.**splunk-mcp**>
      @type record_transformer
      <record>
        security_event true
        environment production
        platform splunk-mcp
      </record>
    </filter>
    
    <match kubernetes.**>
      @type forward
      <server>
        host splunk-forwarder.security.svc.cluster.local
        port 24224
      </server>
      <buffer>
        @type file
        path /var/log/fluentd-buffers/kubernetes.system.buffer
        flush_mode interval
        retry_type exponential_backoff
        flush_thread_count 2
        flush_interval 5s
        retry_forever
        retry_max_interval 30
        chunk_limit_size 2M
        queue_limit_length 8
        overflow_action block
      </buffer>
    </match>
```

#### Security Event Detection
```yaml
# security-alerts.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: security-alerts
  namespace: monitoring
spec:
  groups:
  - name: security.rules
    rules:
    - alert: FailedAuthenticationAttempts
      expr: increase(http_requests_total{status="401"}[5m]) > 10
      for: 2m
      labels:
        severity: warning
        category: security
      annotations:
        summary: "High number of failed authentication attempts"
        description: "{{ $value }} failed authentication attempts in the last 5 minutes"
    
    - alert: PrivilegeEscalationAttempt
      expr: increase(security_events_total{event_type="privilege_escalation"}[1m]) > 0
      for: 0m
      labels:
        severity: critical
        category: security
      annotations:
        summary: "Privilege escalation attempt detected"
        description: "Potential privilege escalation attempt from {{ $labels.user }}"
    
    - alert: SuspiciousDataAccess
      expr: increase(data_access_total{time_of_day=~"(0[0-5]|2[3-4])"}[10m]) > 50
      for: 5m
      labels:
        severity: warning
        category: security
      annotations:
        summary: "Suspicious data access during off hours"
        description: "{{ $value }} data access events during off hours"
    
    - alert: UnauthorizedAPIAccess
      expr: increase(http_requests_total{status="403"}[5m]) > 20
      for: 3m
      labels:
        severity: warning
        category: security
      annotations:
        summary: "High number of unauthorized API access attempts"
        description: "{{ $value }} unauthorized API access attempts"
```

### Intrusion Detection

#### Network-Based Detection
```yaml
# suricata-deployment.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: suricata-ids
  namespace: security
spec:
  selector:
    matchLabels:
      app: suricata-ids
  template:
    metadata:
      labels:
        app: suricata-ids
    spec:
      hostNetwork: true
      containers:
      - name: suricata
        image: jasonish/suricata:latest
        securityContext:
          privileged: true
        volumeMounts:
        - name: suricata-config
          mountPath: /etc/suricata
        - name: rules
          mountPath: /var/lib/suricata/rules
        - name: logs
          mountPath: /var/log/suricata
        env:
        - name: SURICATA_OPTIONS
          value: "-i any --user suricata"
      volumes:
      - name: suricata-config
        configMap:
          name: suricata-config
      - name: rules
        configMap:
          name: suricata-rules
      - name: logs
        hostPath:
          path: /var/log/suricata
```

#### Host-Based Detection
```yaml
# falco-deployment.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: falco
  namespace: security
spec:
  selector:
    matchLabels:
      app: falco
  template:
    metadata:
      labels:
        app: falco
    spec:
      serviceAccount: falco
      hostNetwork: true
      hostPID: true
      containers:
      - name: falco
        image: falcosecurity/falco:latest
        securityContext:
          privileged: true
        volumeMounts:
        - name: boot
          mountPath: /host/boot
          readOnly: true
        - name: lib-modules
          mountPath: /host/lib/modules
          readOnly: true
        - name: usr
          mountPath: /host/usr
          readOnly: true
        - name: etc
          mountPath: /host/etc
          readOnly: true
        - name: falco-config
          mountPath: /etc/falco
        env:
        - name: FALCO_K8S_NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
      volumes:
      - name: boot
        hostPath:
          path: /boot
      - name: lib-modules
        hostPath:
          path: /lib/modules
      - name: usr
        hostPath:
          path: /usr
      - name: etc
        hostPath:
          path: /etc
      - name: falco-config
        configMap:
          name: falco-config
```

---

## Compliance & Auditing

### Audit Logging

#### Kubernetes Audit Configuration
```yaml
# audit-policy.yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: Metadata
  namespaces: ["splunk-mcp-prod"]
  verbs: ["create", "delete", "update", "patch"]
  resources:
  - group: ""
    resources: ["secrets", "configmaps"]
- level: Request
  namespaces: ["splunk-mcp-prod"]
  verbs: ["create", "delete"]
  resources:
  - group: ""
    resources: ["pods", "services"]
- level: RequestResponse
  namespaces: ["splunk-mcp-prod"]
  verbs: ["create", "delete", "update", "patch"]
  resources:
  - group: "rbac.authorization.k8s.io"
    resources: ["roles", "rolebindings"]
```

#### Application Audit Logging
```python
# audit_logger.py
import json
import logging
from datetime import datetime
from typing import Any, Dict

class SecurityAuditLogger:
    def __init__(self, logger_name: str = "security_audit"):
        self.logger = logging.getLogger(logger_name)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - AUDIT - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_event(self, event_type: str, user_id: str, resource: str, 
                  action: str, result: str, details: Dict[str, Any] = None):
        audit_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "result": result,
            "details": details or {},
            "source_ip": self._get_source_ip(),
            "user_agent": self._get_user_agent()
        }
        self.logger.info(json.dumps(audit_event))
    
    def log_authentication(self, user_id: str, method: str, result: str, source_ip: str):
        self.log_event(
            event_type="authentication",
            user_id=user_id,
            resource="auth_system",
            action=f"login_{method}",
            result=result,
            details={"source_ip": source_ip, "method": method}
        )
    
    def log_data_access(self, user_id: str, index: str, query: str, result_count: int):
        self.log_event(
            event_type="data_access",
            user_id=user_id,
            resource=f"splunk_index_{index}",
            action="search",
            result="success",
            details={
                "query_hash": hashlib.sha256(query.encode()).hexdigest(),
                "result_count": result_count
            }
        )
    
    def log_privilege_change(self, admin_user: str, target_user: str, 
                           old_roles: list, new_roles: list):
        self.log_event(
            event_type="privilege_change",
            user_id=admin_user,
            resource=f"user_{target_user}",
            action="role_modification",
            result="success",
            details={
                "old_roles": old_roles,
                "new_roles": new_roles,
                "target_user": target_user
            }
        )
```

### Compliance Frameworks

#### SOC 2 Compliance
```yaml
# soc2-controls.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: soc2-controls
  namespace: splunk-mcp-prod
data:
  controls.json: |
    {
      "CC6.1": {
        "description": "Logical and physical access controls",
        "controls": [
          "Multi-factor authentication implemented",
          "Role-based access control configured",
          "Network segmentation in place",
          "Physical access controls for data centers"
        ]
      },
      "CC6.2": {
        "description": "Access control management",
        "controls": [
          "Regular access reviews conducted",
          "Privilege escalation monitoring",
          "Automated user provisioning/deprovisioning",
          "Segregation of duties enforced"
        ]
      },
      "CC6.3": {
        "description": "Access control removal",
        "controls": [
          "Automated account deactivation",
          "Regular orphaned account cleanup",
          "Access recertification process",
          "Emergency access procedures"
        ]
      },
      "CC7.2": {
        "description": "System monitoring",
        "controls": [
          "Continuous security monitoring",
          "Intrusion detection systems",
          "Security event correlation",
          "Incident response procedures"
        ]
      }
    }
```

#### GDPR Compliance
```yaml
# gdpr-controls.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: gdpr-controls
  namespace: splunk-mcp-prod
data:
  gdpr_controls.json: |
    {
      "data_protection": {
        "encryption_at_rest": true,
        "encryption_in_transit": true,
        "data_minimization": true,
        "pseudonymization": true
      },
      "data_rights": {
        "right_to_access": {
          "endpoint": "/api/v1/privacy/data-export",
          "response_time": "30 days"
        },
        "right_to_rectification": {
          "endpoint": "/api/v1/privacy/data-correction",
          "response_time": "30 days"
        },
        "right_to_erasure": {
          "endpoint": "/api/v1/privacy/data-deletion",
          "response_time": "30 days"
        },
        "right_to_portability": {
          "endpoint": "/api/v1/privacy/data-export",
          "format": "JSON"
        }
      },
      "breach_notification": {
        "internal_notification": "24 hours",
        "authority_notification": "72 hours",
        "data_subject_notification": "without undue delay"
      }
    }
```

### Compliance Monitoring

#### Automated Compliance Checks
```bash
#!/bin/bash
# compliance-check.sh

NAMESPACE="splunk-mcp-prod"
COMPLIANCE_REPORT="/tmp/compliance-report-$(date +%Y%m%d-%H%M%S).json"

echo "Starting compliance check..."

# Initialize report
cat > $COMPLIANCE_REPORT <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "namespace": "$NAMESPACE",
  "checks": {}
}
EOF

# Check encryption at rest
echo "Checking encryption at rest..."
encrypted_volumes=$(kubectl get pv -o json | jq '.items[] | select(.spec.awsElasticBlockStore.encrypted == true) | .metadata.name' | wc -l)
total_volumes=$(kubectl get pv -o json | jq '.items | length')

if [ "$encrypted_volumes" -eq "$total_volumes" ]; then
    encryption_status="PASS"
else
    encryption_status="FAIL"
fi

# Update report
jq --arg status "$encryption_status" --arg encrypted "$encrypted_volumes" --arg total "$total_volumes" \
   '.checks.encryption_at_rest = {
     "status": $status,
     "encrypted_volumes": ($encrypted | tonumber),
     "total_volumes": ($total | tonumber)
   }' $COMPLIANCE_REPORT > ${COMPLIANCE_REPORT}.tmp && mv ${COMPLIANCE_REPORT}.tmp $COMPLIANCE_REPORT

# Check network policies
echo "Checking network policies..."
network_policies=$(kubectl get networkpolicy -n $NAMESPACE -o json | jq '.items | length')
if [ "$network_policies" -gt 0 ]; then
    network_policy_status="PASS"
else
    network_policy_status="FAIL"
fi

jq --arg status "$network_policy_status" --arg count "$network_policies" \
   '.checks.network_policies = {
     "status": $status,
     "policy_count": ($count | tonumber)
   }' $COMPLIANCE_REPORT > ${COMPLIANCE_REPORT}.tmp && mv ${COMPLIANCE_REPORT}.tmp $COMPLIANCE_REPORT

# Check RBAC configuration
echo "Checking RBAC configuration..."
roles=$(kubectl get roles -n $NAMESPACE -o json | jq '.items | length')
rolebindings=$(kubectl get rolebindings -n $NAMESPACE -o json | jq '.items | length')

if [ "$roles" -gt 0 ] && [ "$rolebindings" -gt 0 ]; then
    rbac_status="PASS"
else
    rbac_status="FAIL"
fi

jq --arg status "$rbac_status" --arg roles "$roles" --arg bindings "$rolebindings" \
   '.checks.rbac = {
     "status": $status,
     "roles": ($roles | tonumber),
     "role_bindings": ($bindings | tonumber)
   }' $COMPLIANCE_REPORT > ${COMPLIANCE_REPORT}.tmp && mv ${COMPLIANCE_REPORT}.tmp $COMPLIANCE_REPORT

echo "Compliance check completed. Report saved to $COMPLIANCE_REPORT"
cat $COMPLIANCE_REPORT
```

---

## Incident Response

### Security Incident Response Plan

#### Incident Classification
```yaml
# incident-classification.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: incident-classification
  namespace: splunk-mcp-prod
data:
  classification.json: |
    {
      "severity_levels": {
        "critical": {
          "response_time": "15 minutes",
          "escalation_time": "30 minutes",
          "examples": [
            "Active data breach",
            "System compromise",
            "Service unavailability",
            "Privilege escalation"
          ]
        },
        "high": {
          "response_time": "1 hour",
          "escalation_time": "2 hours",
          "examples": [
            "Suspicious activity",
            "Failed security controls",
            "Unauthorized access attempts",
            "Data integrity issues"
          ]
        },
        "medium": {
          "response_time": "4 hours",
          "escalation_time": "8 hours",
          "examples": [
            "Policy violations",
            "Configuration issues",
            "Performance anomalies",
            "Audit findings"
          ]
        },
        "low": {
          "response_time": "24 hours",
          "escalation_time": "48 hours",
          "examples": [
            "Information gathering",
            "Minor policy violations",
            "Documentation issues",
            "Training requirements"
          ]
        }
      }
    }
```

#### Automated Response Actions
```python
# incident_response.py
import json
import subprocess
from datetime import datetime
from typing import Dict, List

class SecurityIncidentResponse:
    def __init__(self):
        self.namespace = "splunk-mcp-prod"
        self.incident_log = []
    
    def detect_brute_force_attack(self, failed_attempts: int, user: str, source_ip: str):
        """Detect and respond to brute force attacks"""
        if failed_attempts > 10:
            self.isolate_user_account(user)
            self.block_source_ip(source_ip)
            self.create_incident("brute_force", "high", {
                "user": user,
                "source_ip": source_ip,
                "failed_attempts": failed_attempts
            })
    
    def detect_data_exfiltration(self, user: str, data_volume: int, time_window: int):
        """Detect and respond to potential data exfiltration"""
        if data_volume > 10000 and time_window < 300:  # 10GB in 5 minutes
            self.limit_user_bandwidth(user)
            self.alert_security_team("data_exfiltration", {
                "user": user,
                "data_volume": data_volume,
                "time_window": time_window
            })
    
    def isolate_user_account(self, user: str):
        """Temporarily disable user account"""
        try:
            # Disable user in platform
            subprocess.run([
                "kubectl", "patch", "user", user,
                "-n", self.namespace,
                "--type=merge",
                "-p", '{"spec":{"disabled":true}}'
            ], check=True)
            
            self.log_action(f"User account {user} temporarily disabled")
        except subprocess.CalledProcessError as e:
            self.log_action(f"Failed to disable user {user}: {e}")
    
    def block_source_ip(self, source_ip: str):
        """Block malicious IP address"""
        try:
            # Create network policy to block IP
            network_policy = {
                "apiVersion": "networking.k8s.io/v1",
                "kind": "NetworkPolicy",
                "metadata": {
                    "name": f"block-{source_ip.replace('.', '-')}",
                    "namespace": self.namespace
                },
                "spec": {
                    "podSelector": {},
                    "policyTypes": ["Ingress"],
                    "ingress": [{
                        "from": [{
                            "ipBlock": {
                                "cidr": f"{source_ip}/32",
                                "except": []
                            }
                        }]
                    }]
                }
            }
            
            with open(f"/tmp/block-{source_ip.replace('.', '-')}.yaml", "w") as f:
                yaml.dump(network_policy, f)
            
            subprocess.run([
                "kubectl", "apply", "-f", f"/tmp/block-{source_ip.replace('.', '-')}.yaml"
            ], check=True)
            
            self.log_action(f"Blocked source IP {source_ip}")
        except Exception as e:
            self.log_action(f"Failed to block IP {source_ip}: {e}")
    
    def create_incident(self, incident_type: str, severity: str, details: Dict):
        """Create security incident record"""
        incident = {
            "id": f"INC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.utcnow().isoformat(),
            "type": incident_type,
            "severity": severity,
            "status": "open",
            "details": details,
            "actions_taken": [],
            "assigned_to": "security_team"
        }
        
        self.incident_log.append(incident)
        self.notify_security_team(incident)
    
    def log_action(self, action: str):
        """Log incident response action"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action
        }
        print(json.dumps(log_entry))
```

### Forensic Procedures

#### Evidence Collection
```bash
#!/bin/bash
# collect-evidence.sh

INCIDENT_ID="$1"
NAMESPACE="splunk-mcp-prod"
EVIDENCE_DIR="/tmp/evidence-$INCIDENT_ID"

if [ -z "$INCIDENT_ID" ]; then
    echo "Usage: $0 <incident-id>"
    exit 1
fi

mkdir -p "$EVIDENCE_DIR"
cd "$EVIDENCE_DIR"

echo "Collecting evidence for incident $INCIDENT_ID..."

# Collect system state
kubectl get all -n $NAMESPACE -o yaml > system-state.yaml
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' > events.log

# Collect logs from all pods
for pod in $(kubectl get pods -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}'); do
    echo "Collecting logs from pod $pod..."
    kubectl logs $pod -n $NAMESPACE --previous > ${pod}-previous.log 2>/dev/null || true
    kubectl logs $pod -n $NAMESPACE > ${pod}-current.log 2>/dev/null || true
done

# Collect network policies
kubectl get networkpolicy -n $NAMESPACE -o yaml > network-policies.yaml

# Collect security events from monitoring
if command -v curl &> /dev/null; then
    # Query Prometheus for security metrics
    curl -G 'http://prometheus:9090/api/v1/query_range' \
        --data-urlencode 'query=security_events_total' \
        --data-urlencode 'start='$(date -d '1 hour ago' +%s) \
        --data-urlencode 'end='$(date +%s) \
        --data-urlencode 'step=60' > security-metrics.json
fi

# Create forensic hash
find . -type f -exec sha256sum {} \; > evidence-hashes.txt

# Create evidence package
cd ..
tar -czf "evidence-$INCIDENT_ID-$(date +%Y%m%d-%H%M%S).tar.gz" "evidence-$INCIDENT_ID/"

echo "Evidence collection completed. Package created: evidence-$INCIDENT_ID-$(date +%Y%m%d-%H%M%S).tar.gz"
```

---

## Security Maintenance

### Regular Security Tasks

#### Daily Security Tasks
```bash
#!/bin/bash
# daily-security-tasks.sh

NAMESPACE="splunk-mcp-prod"
LOG_FILE="/var/log/security-maintenance.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_FILE
}

log_message "Starting daily security maintenance tasks"

# Check for failed authentication attempts
log_message "Checking failed authentication attempts..."
failed_auth_count=$(kubectl logs -n $NAMESPACE deployment/api-gateway --since=24h | grep "auth_failure" | wc -l)
if [ "$failed_auth_count" -gt 100 ]; then
    log_message "WARNING: High number of failed authentication attempts: $failed_auth_count"
fi

# Check for security policy violations
log_message "Checking security policy violations..."
kubectl get events -n $NAMESPACE --field-selector reason=FailedMount,reason=FailedScheduling --since=24h

# Check certificate expiration
log_message "Checking certificate expiration..."
cert_expiry=$(kubectl get secret platform-tls -n $NAMESPACE -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -enddate | cut -d= -f2)
log_message "TLS certificate expires: $cert_expiry"

# Check for outdated images
log_message "Checking for outdated container images..."
kubectl get pods -n $NAMESPACE -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].image}{"\n"}{end}' | while read pod image; do
    if [[ "$image" == *":latest"* ]]; then
        log_message "WARNING: Pod $pod using :latest tag"
    fi
done

log_message "Daily security maintenance tasks completed"
```

#### Weekly Security Tasks
```bash
#!/bin/bash
# weekly-security-tasks.sh

NAMESPACE="splunk-mcp-prod"
LOG_FILE="/var/log/security-maintenance.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_FILE
}

log_message "Starting weekly security maintenance tasks"

# Review user access
log_message "Reviewing user access permissions..."
kubectl get rolebindings -n $NAMESPACE -o yaml > /tmp/rolebindings-$(date +%Y%m%d).yaml

# Check for unused service accounts
log_message "Checking for unused service accounts..."
kubectl get serviceaccounts -n $NAMESPACE --sort-by=.metadata.creationTimestamp

# Review network policies
log_message "Reviewing network policies..."
kubectl get networkpolicy -n $NAMESPACE -o yaml > /tmp/networkpolicies-$(date +%Y%m%d).yaml

# Security vulnerability scan
log_message "Running security vulnerability scan..."
# This would integrate with your chosen vulnerability scanner
# Example with trivy:
# trivy image --severity HIGH,CRITICAL ghcr.io/your-org/splunk-mcp/api-gateway:latest

# Check for security updates
log_message "Checking for security updates..."
kubectl get nodes -o wide

log_message "Weekly security maintenance tasks completed"
```

#### Monthly Security Tasks
```bash
#!/bin/bash
# monthly-security-tasks.sh

NAMESPACE="splunk-mcp-prod"
LOG_FILE="/var/log/security-maintenance.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_FILE
}

log_message "Starting monthly security maintenance tasks"

# Comprehensive security audit
log_message "Running comprehensive security audit..."
./compliance-check.sh

# Review and rotate secrets
log_message "Reviewing secrets rotation schedule..."
for secret in jwt-keys splunk-secrets ai-secrets; do
    creation_date=$(kubectl get secret $secret -n $NAMESPACE -o jsonpath='{.metadata.creationTimestamp}')
    log_message "Secret $secret created: $creation_date"
done

# Backup security configurations
log_message "Backing up security configurations..."
kubectl get secrets,configmaps,networkpolicies,roles,rolebindings -n $NAMESPACE -o yaml > /backup/security-config-$(date +%Y%m%d).yaml

# Review incident response procedures
log_message "Reviewing incident response procedures..."
# This would trigger a tabletop exercise or procedure review

# Update security documentation
log_message "Updating security documentation..."
# This would trigger documentation review and updates

log_message "Monthly security maintenance tasks completed"
```

### Automated Security Scanning

#### Container Security Scanning
```yaml
# security-scan-job.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: security-scanner
  namespace: splunk-mcp-prod
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: trivy-scanner
            image: aquasec/trivy:latest
            command:
            - /bin/sh
            - -c
            - |
              echo "Starting security scan..."
              
              # Scan all images in the namespace
              for image in $(kubectl get pods -n splunk-mcp-prod -o jsonpath='{.items[*].spec.containers[*].image}' | tr ' ' '\n' | sort -u); do
                echo "Scanning image: $image"
                trivy image --severity HIGH,CRITICAL --format json --output /tmp/scan-results.json $image
                
                # Check if vulnerabilities found
                if [ -s /tmp/scan-results.json ]; then
                  echo "Vulnerabilities found in $image"
                  # Send alert (would integrate with your alerting system)
                fi
              done
              
              echo "Security scan completed"
          restartPolicy: OnFailure
```

---

*This security administration guide provides comprehensive procedures for maintaining the security posture of the Splunk MCP Integration Platform. Regular review and updates ensure continued protection against evolving threats.*