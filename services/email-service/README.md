# Email Service

A comprehensive email integration service for the Splunk MCP platform that enables natural language queries via email, automated report generation and delivery, and alert notifications.

## Features

📧 **Email Integration**
- Natural language query processing via email
- Automated report generation and delivery
- Alert notifications and escalations
- Scheduled report subscriptions
- Multi-format report generation (PDF, CSV, XLSX, HTML)

⚡ **Real-time Processing**
- SMTP/IMAP email server integration
- Webhook support for external email services
- Asynchronous email processing
- Queue management with retry logic

🔒 **Enterprise Security**
- JWT authentication for API access
- Rate limiting with Redis backend
- Email validation and sanitization
- Domain whitelist/blacklist support
- Audit logging and compliance

📊 **Rich Reports**
- Multiple output formats (PDF, CSV, XLSX, HTML)
- Visualization embedding
- Template-based email formatting
- Attachment support up to 25MB
- Scheduled and on-demand generation

## Quick Start

### Prerequisites

1. **SMTP Server Configuration**
   - Gmail, Outlook, or corporate SMTP server
   - Authentication credentials
   - TLS/SSL support

2. **Environment Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your SMTP and database credentials
   ```

3. **Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Development

```bash
# Start database services
docker-compose up -d postgres redis

# Run the email service
uvicorn app.main:app --host 0.0.0.0 --port 8006 --reload

# Health check
curl http://localhost:8006/health
```

### Production

```bash
# Start all services
docker-compose up -d

# Check service status
curl http://localhost:8006/health
curl http://localhost:9006/metrics  # Prometheus metrics
```

## Usage Examples

### Send Query via Email
```
To: splunk-assistant@your-domain.com
Subject: Show me errors from last hour

show me errors from the last hour where severity="high"
```

### Request Scheduled Report
```
To: splunk-assistant@your-domain.com
Subject: Weekly Error Report

Create a weekly report showing:
- Error counts by source
- Top 10 error types  
- Trend analysis
- Send every Monday at 9 AM
```

### Alert Configuration
```
To: splunk-assistant@your-domain.com
Subject: Create Alert

Alert me when error rate exceeds 100 per minute
Check every 5 minutes
Include visualization
```

## Configuration

### Environment Variables

```bash
# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com

# Backend Services
API_GATEWAY_URL=http://api-gateway:8000
NLP_ENGINE_URL=http://nlp-engine:8001
VISUALIZATION_URL=http://visualization:8002

# Database & Cache
DATABASE_URL=postgresql://email_user:email_pass@postgres:5432/email_service
REDIS_URL=redis://redis:6379/5

# Security
JWT_SECRET_KEY=your-secret-key
RATE_LIMIT_PER_USER=100  # requests per hour

# Features
ENABLE_ATTACHMENTS=true
ENABLE_HTML_EMAILS=true
ENABLE_IMAP_PROCESSING=false
```

### SMTP Setup Examples

#### Gmail Setup
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
# Use App Password, not regular password
SMTP_PASSWORD=your-16-char-app-password
```

#### Outlook/Hotmail Setup
```bash
SMTP_HOST=smtp.live.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

#### Corporate Exchange
```bash
SMTP_HOST=mail.company.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

## API Endpoints

### Core Endpoints

- `POST /emails/` - Send email manually
- `GET /emails/` - List user emails
- `GET /emails/{id}` - Get specific email
- `GET /emails/stats` - Email statistics

### Reports

- `POST /reports/` - Create new report
- `GET /reports/` - List user reports  
- `GET /reports/{id}` - Get specific report
- `GET /reports/stats` - Report statistics

### Users & Settings

- `GET /users/me` - Get current user
- `GET /users/me/settings` - Get email settings
- `PUT /users/me/settings` - Update email settings

### Subscriptions

- `POST /subscriptions/` - Create subscription
- `GET /subscriptions/` - List subscriptions
- `PUT /subscriptions/{id}` - Update subscription
- `DELETE /subscriptions/{id}` - Delete subscription

## Email Processing Flow

1. **Incoming Email**
   - IMAP polling or webhook receives email
   - Extract sender, subject, and body content
   - Validate sender against whitelist/permissions

2. **Query Extraction**
   - Parse email body for natural language queries
   - Extract query parameters and context
   - Validate query structure and permissions

3. **Processing**
   - Send query to NLP engine for SPL translation
   - Execute query via API gateway
   - Generate visualizations if requested

4. **Response Generation**
   - Format results using email templates
   - Generate attachments (CSV, PDF, etc.)
   - Apply user preferences and settings

5. **Delivery**
   - Send response email with results
   - Log delivery status and metrics
   - Handle bounces and errors

## Report Generation

### Supported Formats

- **HTML**: Rich formatting with embedded charts
- **PDF**: Professional reports with visualizations
- **CSV**: Raw data export for analysis
- **XLSX**: Excel format with multiple sheets

### Template System

```html
<!-- Example HTML template -->
<h2>{{report_title}}</h2>
<p><strong>Generated:</strong> {{timestamp}}</p>
<p><strong>Query:</strong> {{query_text}}</p>

{{#if has_visualizations}}
<div class="charts">
  {{#each visualizations}}
  <img src="{{image_url}}" alt="{{title}}" />
  {{/each}}
</div>
{{/if}}

{{#if has_data}}
<table>
  {{#each results}}
  <tr>
    {{#each this}}
    <td>{{this}}</td>
    {{/each}}
  </tr>
  {{/each}}
</table>
{{/if}}
```

## Monitoring & Metrics

### Health Checks
- Database connectivity
- Redis availability  
- SMTP server connection
- Backend service health

### Prometheus Metrics
- Email processing rates
- Delivery success rates
- Queue sizes and processing times
- Error rates by type
- User activity metrics

### Logging

Structured JSON logging with correlation IDs:
```json
{
  "timestamp": "2025-01-16T10:30:00Z",
  "level": "INFO",
  "correlation_id": "uuid",
  "user_id": "user123",
  "email_type": "query_response",
  "message": "Email sent successfully"
}
```

## Security

### Authentication
- JWT token validation for API access
- SMTP/IMAP server authentication
- Rate limiting per user and domain

### Email Security
- Content sanitization (XSS prevention)
- Attachment type validation
- Domain whitelist/blacklist
- Auto-reply detection and filtering

### Data Protection
- Database encryption at rest
- TLS for email transmission
- Audit logging for compliance
- Personal data anonymization options

## Troubleshooting

### Common Issues

1. **SMTP Authentication Failed**
   - Check username/password credentials
   - Verify App Password for Gmail
   - Confirm TLS/SSL settings

2. **Emails Not Sending**
   - Check SMTP server connectivity
   - Verify rate limiting settings
   - Review error logs

3. **Database Connection Issues**
   - Verify PostgreSQL connection string
   - Check database user permissions
   - Review connection pool settings

4. **High Memory Usage**
   - Monitor large attachment processing
   - Check report generation limits
   - Review Redis cache sizes

### Debug Commands

```bash
# Check service health
curl http://localhost:8006/health

# View service metrics
curl http://localhost:9006/metrics

# Check email queue status
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8006/emails/stats

# Test SMTP connection
python -c "
import aiosmtplib
import asyncio
async def test():
    smtp = aiosmtplib.SMTP('smtp.gmail.com', 587, use_tls=True)
    await smtp.connect()
    print('SMTP connection successful')
    await smtp.quit()
asyncio.run(test())
"
```

## Development

### Code Structure
```
app/
├── main.py              # FastAPI application
├── core/
│   ├── config.py        # Configuration settings
│   └── logging.py       # Logging configuration
├── api/                 # API endpoints
├── models/              # Data models
├── services/            # Business logic
├── utils/               # Utilities and helpers
└── templates/           # Email templates
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest tests/test_email_processing.py -v
pytest tests/test_report_generation.py -v
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

See the main [CLAUDE.md](../../CLAUDE.md) for project guidelines.

## Integration

### Backend Services

The email service integrates with:
- **API Gateway**: Authentication and request routing
- **NLP Engine**: Natural language to SPL translation
- **Visualization Service**: Chart and dashboard generation
- **Alert Manager**: Alert rule creation and management

### External Services

- **SMTP Servers**: Gmail, Outlook, Exchange, Postfix
- **IMAP Servers**: For email monitoring and processing
- **Webhook Providers**: SendGrid, Mailgun, Amazon SES
- **Cloud Storage**: S3, GCS for attachment storage

## License

This project is part of the Splunk MCP Integration platform.