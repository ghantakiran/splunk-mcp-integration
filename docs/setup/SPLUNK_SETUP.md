# Splunk REST Endpoint Setup Guide

This guide provides comprehensive instructions for configuring Splunk Enterprise or Splunk Cloud to work with the MCP Integration platform via REST API endpoints.

## Overview

The Splunk MCP Integration platform connects to Splunk via REST API endpoints to:
- Execute SPL (Search Processing Language) queries
- Retrieve search results and metadata
- Manage saved searches and dashboards
- Monitor Splunk system health
- Access index and sourcetype information

## Prerequisites

### Splunk Version Requirements
- **Splunk Enterprise**: Version 9.0+ (recommended: 9.1+)
- **Splunk Cloud**: Any current version
- **Splunk Universal Forwarder**: Not supported (needs full Splunk instance)

### Network Requirements
- REST API access on port 8089 (default)
- HTTPS/TLS encryption recommended for production
- Network connectivity from MCP platform to Splunk instance

## 1. Splunk Enterprise Setup

### Step 1: Enable REST API Access

#### Check Current Configuration
```bash
# SSH to your Splunk server
ssh admin@your-splunk-server.com

# Check if REST API is enabled
sudo -u splunk /opt/splunk/bin/splunk show web-port
sudo -u splunk /opt/splunk/bin/splunk show splunkd-port
```

#### Enable REST API (if disabled)
```bash
# Enable splunkd (REST API) service
sudo -u splunk /opt/splunk/bin/splunk enable boot-start

# Configure splunkd port (default 8089)
sudo -u splunk /opt/splunk/bin/splunk set splunkd-port 8089

# Restart Splunk to apply changes
sudo -u splunk /opt/splunk/bin/splunk restart
```

#### Verify REST API Access
```bash
# Test REST API endpoint
curl -k -u admin:password https://your-splunk-server.com:8089/services/server/info

# Expected response: XML with server information
```

### Step 2: Create Dedicated Service Account

#### Using Splunk Web Interface
1. Log into Splunk Web (http://your-splunk-server.com:8000)
2. Go to **Settings** → **Access controls** → **Users**
3. Click **New User**
4. Fill in user details:
   - Username: `splunk_mcp_service`
   - Full Name: `Splunk MCP Integration Service`
   - Email: `admin@yourcompany.com`
   - Password: Generate strong password
   - Roles: `user`, `power` (or custom role)

#### Using CLI
```bash
# Create service user via CLI
sudo -u splunk /opt/splunk/bin/splunk add user splunk_mcp_service \
  -password 'SecurePassword123!' \
  -role user \
  -role power \
  -email admin@yourcompany.com \
  -full-name "Splunk MCP Integration Service"

# Restart Splunk
sudo -u splunk /opt/splunk/bin/splunk restart
```

### Step 3: Configure User Permissions

#### Create Custom Role (Recommended)
```bash
# Create custom role with specific capabilities
sudo -u splunk /opt/splunk/bin/splunk add role splunk_mcp_role \
  -capability "search" \
  -capability "list_storage_passwords" \
  -capability "rest_apps_view" \
  -capability "rest_properties_get" \
  -capability "rest_properties_set"

# Assign role to service user
sudo -u splunk /opt/splunk/bin/splunk edit user splunk_mcp_service \
  -role splunk_mcp_role
```

#### Manual Permission Configuration
1. Go to **Settings** → **Access controls** → **Roles**
2. Create new role: `splunk_mcp_role`
3. Configure **Capabilities**:
   ```
   ✓ search
   ✓ list_storage_passwords
   ✓ rest_apps_view
   ✓ rest_properties_get
   ✓ schedule_search
   ✓ embed_report
   ✓ export_results_is_visible
   ```
4. Configure **Indexes** (grant access to required indexes):
   ```
   ✓ main
   ✓ _internal
   ✓ your_custom_indexes
   ```
5. Configure **Inheritance**: Inherit from `user` role

### Step 4: Configure SSL/TLS (Production)

#### Generate SSL Certificate
```bash
# Navigate to Splunk SSL directory
cd /opt/splunk/etc/auth

# Generate private key
sudo -u splunk openssl genrsa -out server.key 2048

# Generate certificate signing request
sudo -u splunk openssl req -new -key server.key -out server.csr

# Generate self-signed certificate (or use CA-signed)
sudo -u splunk openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.pem

# Combine certificate and key
sudo -u splunk cat server.pem server.key > server.pem
```

#### Configure SSL in Splunk
```bash
# Edit server.conf
sudo -u splunk vi /opt/splunk/etc/system/local/server.conf

# Add SSL configuration
[sslConfig]
enableSplunkdSSL = true
serverCert = /opt/splunk/etc/auth/server.pem
sslPassword = your_ssl_password

[httpServer]
acceptFrom = your.mcp.platform.ip
```

#### Restart Splunk
```bash
sudo -u splunk /opt/splunk/bin/splunk restart
```

### Step 5: Test Connection

#### Basic Authentication Test
```bash
# Test basic authentication
curl -k -u splunk_mcp_service:SecurePassword123! \
  https://your-splunk-server.com:8089/services/server/info

# Test search capability
curl -k -u splunk_mcp_service:SecurePassword123! \
  https://your-splunk-server.com:8089/services/search/jobs \
  -d "search=search index=main | head 10"
```

#### Advanced Authentication Test
```python
#!/usr/bin/env python3
"""
Splunk REST API connection test script
"""

import requests
import json
import urllib3
from urllib.parse import urljoin

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SplunkTester:
    def __init__(self, host, port, username, password, scheme='https'):
        self.base_url = f"{scheme}://{host}:{port}"
        self.auth = (username, password)
        self.session = requests.Session()
        self.session.verify = False  # Set to True for production with valid certs
    
    def test_connection(self):
        """Test basic connection to Splunk"""
        try:
            url = urljoin(self.base_url, '/services/server/info')
            response = self.session.get(url, auth=self.auth, timeout=10)
            
            if response.status_code == 200:
                print("✅ Connection successful")
                return True
            else:
                print(f"❌ Connection failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Connection error: {str(e)}")
            return False
    
    def test_search_capability(self):
        """Test search execution capability"""
        try:
            # Start a search job
            search_url = urljoin(self.base_url, '/services/search/jobs')
            search_data = {
                'search': 'search index=_internal | head 5',
                'output_mode': 'json',
                'exec_mode': 'oneshot'
            }
            
            response = self.session.post(
                search_url, 
                auth=self.auth, 
                data=search_data,
                timeout=30
            )
            
            if response.status_code == 200:
                results = response.json()
                print(f"✅ Search capability verified - {len(results.get('results', []))} results returned")
                return True
            else:
                print(f"❌ Search test failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Search test error: {str(e)}")
            return False
    
    def test_indexes_access(self):
        """Test access to indexes"""
        try:
            url = urljoin(self.base_url, '/services/data/indexes')
            params = {'output_mode': 'json'}
            
            response = self.session.get(url, auth=self.auth, params=params, timeout=10)
            
            if response.status_code == 200:
                indexes = response.json()
                index_names = [entry['name'] for entry in indexes.get('entry', [])]
                print(f"✅ Index access verified - {len(index_names)} indexes accessible")
                print(f"   Available indexes: {', '.join(index_names[:5])}...")
                return True
            else:
                print(f"❌ Index access test failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Index access test error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all connectivity tests"""
        print("🔍 Testing Splunk REST API connectivity...")
        print("=" * 50)
        
        tests = [
            ("Basic Connection", self.test_connection),
            ("Search Capability", self.test_search_capability),
            ("Index Access", self.test_indexes_access),
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}:")
            success = test_func()
            results.append(success)
        
        print("\n" + "=" * 50)
        passed = sum(results)
        total = len(results)
        
        if passed == total:
            print(f"🎉 All {total} tests passed! Splunk is ready for MCP integration.")
        else:
            print(f"⚠️  {passed}/{total} tests passed. Please fix the failing tests.")
        
        return passed == total

# Usage example
if __name__ == "__main__":
    # Configuration
    SPLUNK_HOST = "your-splunk-server.com"
    SPLUNK_PORT = 8089
    SPLUNK_USERNAME = "splunk_mcp_service"
    SPLUNK_PASSWORD = "SecurePassword123!"
    
    tester = SplunkTester(SPLUNK_HOST, SPLUNK_PORT, SPLUNK_USERNAME, SPLUNK_PASSWORD)
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Configuration ready for MCP platform integration!")
    else:
        print("\n❌ Please fix the configuration issues before proceeding.")
```

## 2. Splunk Cloud Setup

### Step 1: Access Splunk Cloud Console
1. Log into Splunk Cloud at https://cloud.splunk.com/
2. Navigate to your Splunk Cloud instance
3. Access the **Settings** menu

### Step 2: Configure REST API Access

#### Enable REST API
- REST API is enabled by default in Splunk Cloud
- Default endpoint: `https://your-instance.splunkcloud.com:8089`

#### Check API Limits
```bash
# Splunk Cloud has API rate limits
# Default limits:
# - 100 concurrent searches per user
# - 50 requests per second per user
# - 10,000 API calls per day per user
```

### Step 3: Create Service Account

#### Using Splunk Web Interface
1. In Splunk Cloud console, go to **Settings** → **Users and Authentication**
2. Click **Add User**
3. Configure user:
   - Username: `splunk_mcp_service`
   - Email: `service@yourcompany.com`
   - Roles: `sc_admin` or custom role

#### Configure Authentication Method
```bash
# Option 1: Username/Password (basic)
# Use the created service account credentials

# Option 2: SAML/SSO (enterprise)
# Configure SAML integration if using enterprise SSO

# Option 3: API Token (recommended for production)
# Generate API tokens in Splunk Cloud console
```

### Step 4: Test Splunk Cloud Connection

```python
#!/usr/bin/env python3
"""
Splunk Cloud connection test
"""

import requests
import json

def test_splunk_cloud(instance_url, username, password):
    """Test Splunk Cloud connectivity"""
    
    # Splunk Cloud URLs
    base_url = f"https://{instance_url}:8089"
    
    # Test connection
    try:
        response = requests.get(
            f"{base_url}/services/server/info",
            auth=(username, password),
            verify=True,  # Splunk Cloud uses valid SSL certificates
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Splunk Cloud connection successful")
            
            # Get instance info
            # Note: Splunk Cloud returns data in XML format by default
            print(f"✅ Instance accessible at: {base_url}")
            return True
        else:
            print(f"❌ Connection failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        return False

# Usage
if __name__ == "__main__":
    # Replace with your Splunk Cloud instance details
    INSTANCE_URL = "your-instance.splunkcloud.com"
    USERNAME = "splunk_mcp_service"
    PASSWORD = "your_password"
    
    test_splunk_cloud(INSTANCE_URL, USERNAME, PASSWORD)
```

## 3. Advanced Configuration

### REST API Endpoints Reference

#### Essential Endpoints for MCP Integration
```bash
# Server Information
GET /services/server/info

# Search Management
POST /services/search/jobs                    # Start search
GET /services/search/jobs/{sid}               # Get search status
GET /services/search/jobs/{sid}/results       # Get search results
DELETE /services/search/jobs/{sid}            # Cancel search

# Index Information
GET /services/data/indexes                    # List indexes
GET /services/data/indexes/{name}             # Get index details

# Saved Searches
GET /services/saved/searches                  # List saved searches
POST /services/saved/searches                 # Create saved search
GET /services/saved/searches/{name}           # Get saved search details

# Data Input Information
GET /services/data/inputs                     # List data inputs
GET /services/data/sourcetypes                # List sourcetypes

# Apps and Configuration
GET /services/apps/local                      # List installed apps
GET /services/properties                      # Get configuration properties
```

#### Example API Calls
```bash
# Get server info
curl -k -u admin:password \
  "https://splunk-server:8089/services/server/info?output_mode=json"

# Run a simple search
curl -k -u admin:password \
  -d "search=search index=main | head 10" \
  -d "output_mode=json" \
  "https://splunk-server:8089/services/search/jobs"

# Get search results (replace {sid} with actual search ID)
curl -k -u admin:password \
  "https://splunk-server:8089/services/search/jobs/{sid}/results?output_mode=json"

# List available indexes
curl -k -u admin:password \
  "https://splunk-server:8089/services/data/indexes?output_mode=json"
```

### Performance Optimization

#### Search Performance Settings
```bash
# Configure search limits in limits.conf
sudo -u splunk vi /opt/splunk/etc/system/local/limits.conf

[search]
# Maximum concurrent searches per user
max_searches_per_cpu = 8

# Maximum search time (seconds)
max_search_time = 86400

# Maximum results returned
max_count = 500000

# Subsearch limits
max_subsearch_depth = 25
max_subsearch_time = 60
```

#### REST API Performance Tuning
```bash
# Configure web.conf for API performance
sudo -u splunk vi /opt/splunk/etc/system/local/web.conf

[settings]
# Increase max request size
max_upload_size = 500

# Configure timeouts
splunkdConnectionTimeout = 30
ui_inactivity_timeout = 60

# Enable compression
enableSplunkWebClientNetloc = true
```

### Security Configuration

#### IP Restriction
```bash
# Restrict API access to specific IPs
sudo -u splunk vi /opt/splunk/etc/system/local/server.conf

[httpServer]
# Allow access only from MCP platform
acceptFrom = 192.168.1.100, 10.0.0.0/8, your.mcp.platform.ip

[sslConfig]
# Enforce SSL for all connections
requireClientCert = false
enableSplunkdSSL = true
```

#### Authentication Token Management
```python
#!/usr/bin/env python3
"""
Splunk authentication token management
"""

import requests
import json
import time

class SplunkTokenManager:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.auth = (username, password)
        self.session = requests.Session()
        self.session.verify = False
        self.token = None
        self.token_expiry = None
    
    def get_session_token(self):
        """Get authentication token for session-based authentication"""
        try:
            response = self.session.post(
                f"{self.base_url}/services/auth/login",
                data={'username': self.auth[0], 'password': self.auth[1]},
                timeout=10
            )
            
            if response.status_code == 200:
                # Extract session key from response
                session_key = response.text.split('<sessionKey>')[1].split('</sessionKey>')[0]
                self.token = session_key
                self.token_expiry = time.time() + 3600  # 1 hour
                return session_key
            else:
                raise Exception(f"Token request failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Token generation failed: {str(e)}")
            return None
    
    def make_authenticated_request(self, endpoint, method='GET', data=None, params=None):
        """Make authenticated request using session token"""
        if not self.token or time.time() > self.token_expiry:
            self.get_session_token()
        
        headers = {'Authorization': f'Splunk {self.token}'}
        
        if method == 'GET':
            response = self.session.get(
                f"{self.base_url}{endpoint}",
                headers=headers,
                params=params,
                timeout=30
            )
        elif method == 'POST':
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                headers=headers,
                data=data,
                timeout=30
            )
        
        return response

# Usage example
token_manager = SplunkTokenManager(
    "https://your-splunk-server.com:8089",
    "splunk_mcp_service",
    "SecurePassword123!"
)

# Make authenticated search request
response = token_manager.make_authenticated_request(
    "/services/search/jobs",
    method='POST',
    data={'search': 'search index=main | head 10', 'output_mode': 'json'}
)
```

## 4. Environment Configuration for MCP Platform

### Environment Variables for Splunk Connection
```bash
# Add to your MCP platform .env file

# Splunk Enterprise Configuration
SPLUNK_HOST=your-splunk-server.com
SPLUNK_PORT=8089
SPLUNK_SCHEME=https
SPLUNK_USERNAME=splunk_mcp_service
SPLUNK_PASSWORD=SecurePassword123!

# Splunk Cloud Configuration (alternative)
SPLUNK_CLOUD_HOST=your-instance.splunkcloud.com
SPLUNK_CLOUD_PORT=8089
SPLUNK_CLOUD_USERNAME=splunk_mcp_service
SPLUNK_CLOUD_PASSWORD=your_password

# Connection Settings
SPLUNK_VERIFY_SSL=true
SPLUNK_TIMEOUT=30
SPLUNK_MAX_RETRIES=3

# Search Settings
SPLUNK_DEFAULT_INDEX=main
SPLUNK_MAX_SEARCH_TIME=300
SPLUNK_MAX_RESULTS=10000
```

### Configuration Validation
```bash
# Create validation script for Splunk configuration
cat > scripts/validate-splunk-config.py << 'EOF'
#!/usr/bin/env python3
import os
import requests
import urllib3
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def validate_splunk_config():
    """Validate Splunk configuration"""
    
    # Get configuration from environment
    host = os.getenv('SPLUNK_HOST')
    port = os.getenv('SPLUNK_PORT', '8089')
    scheme = os.getenv('SPLUNK_SCHEME', 'https')
    username = os.getenv('SPLUNK_USERNAME')
    password = os.getenv('SPLUNK_PASSWORD')
    verify_ssl = os.getenv('SPLUNK_VERIFY_SSL', 'false').lower() == 'true'
    
    if not all([host, username, password]):
        print("❌ Missing required Splunk configuration")
        return False
    
    base_url = f"{scheme}://{host}:{port}"
    
    try:
        # Test connection
        response = requests.get(
            urljoin(base_url, '/services/server/info'),
            auth=(username, password),
            verify=verify_ssl,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Splunk configuration validated successfully")
            print(f"   Connected to: {base_url}")
            return True
        else:
            print(f"❌ Splunk connection failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Splunk validation error: {str(e)}")
        return False

if __name__ == "__main__":
    success = validate_splunk_config()
    exit(0 if success else 1)
EOF

# Make executable
chmod +x scripts/validate-splunk-config.py

# Run validation
python scripts/validate-splunk-config.py
```

## 5. Troubleshooting

### Common Issues and Solutions

#### Issue: Connection Refused
```bash
# Check if Splunk is running
sudo systemctl status splunk

# Check if splunkd is listening on port 8089
sudo netstat -tlnp | grep 8089

# Check Splunk logs
sudo tail -f /opt/splunk/var/log/splunk/splunkd.log
```

#### Issue: Authentication Failures
```bash
# Verify user credentials
sudo -u splunk /opt/splunk/bin/splunk list user splunk_mcp_service

# Check user roles and capabilities
sudo -u splunk /opt/splunk/bin/splunk list role splunk_mcp_role

# Reset user password
sudo -u splunk /opt/splunk/bin/splunk edit user splunk_mcp_service -password NewPassword123!
```

#### Issue: SSL Certificate Problems
```bash
# Test without SSL verification (development only)
curl -k -u username:password https://splunk-server:8089/services/server/info

# Check certificate validity
openssl s_client -connect splunk-server:8089 -servername splunk-server

# Regenerate self-signed certificate
cd /opt/splunk/etc/auth
sudo -u splunk openssl req -new -x509 -days 365 -nodes -out server.pem -keyout server.key
```

#### Issue: Search Permissions
```bash
# Check user search capabilities
curl -k -u username:password \
  "https://splunk-server:8089/services/authentication/users/splunk_mcp_service?output_mode=json"

# Test basic search
curl -k -u username:password \
  -d "search=| rest /services/server/info | head 1" \
  "https://splunk-server:8089/services/search/jobs"
```

### Performance Troubleshooting

#### Monitor API Usage
```bash
# Check REST API performance metrics
curl -k -u admin:password \
  "https://splunk-server:8089/services/server/status/resource-usage/splunk-processes?output_mode=json"

# Monitor search performance
curl -k -u admin:password \
  "https://splunk-server:8089/services/search/distributed/peers?output_mode=json"
```

#### Check System Resources
```bash
# Monitor Splunk system resources
sudo -u splunk /opt/splunk/bin/splunk show config server --debug

# Check disk usage
df -h /opt/splunk

# Check memory usage
free -h
ps aux | grep splunk
```

## 6. Integration Testing

### Complete Integration Test Script
```python
#!/usr/bin/env python3
"""
Complete Splunk integration test for MCP platform
"""

import requests
import json
import time
import urllib3
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SplunkIntegrationTest:
    def __init__(self, host, port, username, password, scheme='https'):
        self.base_url = f"{scheme}://{host}:{port}"
        self.auth = (username, password)
        self.session = requests.Session()
        self.session.verify = False
    
    def test_basic_connectivity(self):
        """Test basic Splunk connectivity"""
        try:
            response = self.session.get(
                f"{self.base_url}/services/server/info",
                auth=self.auth,
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def test_search_execution(self):
        """Test search execution and results retrieval"""
        try:
            # Start search
            search_response = self.session.post(
                f"{self.base_url}/services/search/jobs",
                auth=self.auth,
                data={
                    'search': 'search index=_internal | head 5',
                    'output_mode': 'json'
                },
                timeout=10
            )
            
            if search_response.status_code != 201:
                return False
            
            # Extract search ID
            search_id = search_response.text.split('<sid>')[1].split('</sid>')[0]
            
            # Wait for search completion
            max_wait = 30
            while max_wait > 0:
                status_response = self.session.get(
                    f"{self.base_url}/services/search/jobs/{search_id}",
                    auth=self.auth,
                    params={'output_mode': 'json'},
                    timeout=10
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data['entry'][0]['content']['isDone']:
                        break
                
                time.sleep(1)
                max_wait -= 1
            
            # Get results
            results_response = self.session.get(
                f"{self.base_url}/services/search/jobs/{search_id}/results",
                auth=self.auth,
                params={'output_mode': 'json'},
                timeout=10
            )
            
            return results_response.status_code == 200
            
        except Exception as e:
            print(f"Search test error: {e}")
            return False
    
    def test_index_access(self):
        """Test index access and listing"""
        try:
            response = self.session.get(
                f"{self.base_url}/services/data/indexes",
                auth=self.auth,
                params={'output_mode': 'json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return len(data.get('entry', [])) > 0
            return False
            
        except:
            return False
    
    def run_comprehensive_test(self):
        """Run all integration tests"""
        print("🔍 Running Splunk Integration Tests...")
        print("=" * 50)
        
        tests = [
            ("Basic Connectivity", self.test_basic_connectivity),
            ("Search Execution", self.test_search_execution),
            ("Index Access", self.test_index_access),
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"📋 {test_name}: ", end="")
            success = test_func()
            status = "✅ PASS" if success else "❌ FAIL"
            print(status)
            results.append(success)
        
        print("=" * 50)
        passed = sum(results)
        total = len(results)
        
        if passed == total:
            print(f"🎉 All {total} tests passed! Splunk integration ready.")
        else:
            print(f"⚠️  {passed}/{total} tests passed. Please check configuration.")
        
        return passed == total

# Usage
if __name__ == "__main__":
    import sys
    
    # Configuration (replace with your values)
    HOST = "your-splunk-server.com"
    PORT = 8089
    USERNAME = "splunk_mcp_service"
    PASSWORD = "SecurePassword123!"
    
    tester = SplunkIntegrationTest(HOST, PORT, USERNAME, PASSWORD)
    success = tester.run_comprehensive_test()
    
    sys.exit(0 if success else 1)
```

---

**Next Steps**: After completing Splunk setup, proceed to [Complete Setup Configuration Guide](./COMPLETE_SETUP.md) for end-to-end deployment instructions.