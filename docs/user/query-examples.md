# Natural Language Query Examples and Best Practices

This guide provides comprehensive examples of natural language queries and best practices for getting the most out of the Splunk MCP Integration Platform.

## Table of Contents

1. [Basic Query Patterns](#basic-query-patterns)
2. [Time-Based Queries](#time-based-queries)
3. [Filtering and Searching](#filtering-and-searching)
4. [Statistical Analysis](#statistical-analysis)
5. [Advanced Analytics](#advanced-analytics)
6. [Industry-Specific Examples](#industry-specific-examples)
7. [Query Optimization Tips](#query-optimization-tips)
8. [Common Mistakes to Avoid](#common-mistakes-to-avoid)

---

## Basic Query Patterns

### Simple Data Retrieval

**Show recent events:**
```
Show me recent events
Display the latest log entries
What happened in the last few minutes?
```

**Basic searches:**
```
Find all error messages
Show me warning events
Display critical alerts
```

**Event counts:**
```
How many events occurred today?
Count all login attempts
Show me the total number of errors
```

### Field-Based Queries

**Query specific fields:**
```
Show me all events from source "nginx"
Find events where status=404
Display logs from host "web-server-01"
```

**Multiple field conditions:**
```
Show events from source "apache" with status "error"
Find login events from user "admin" on host "server-01"
Display events with severity "high" and type "security"
```

---

## Time-Based Queries

### Relative Time Ranges

**Recent time periods:**
```
Show me events from the last hour
Display logs from the past 30 minutes
Find errors in the last 15 minutes
```

**Daily patterns:**
```
Show me today's activity
Compare today with yesterday
Display this week's trends
```

**Extended periods:**
```
Show events from the last 7 days
Display monthly trends
Find patterns over the past year
```

### Specific Time Windows

**Exact time ranges:**
```
Show events between 9 AM and 5 PM today
Display logs from January 1st to January 7th
Find activity during business hours this week
```

**Time comparisons:**
```
Compare last week's performance with this week
Show difference between morning and evening traffic
Display weekend vs weekday patterns
```

### Time-Based Analysis

**Trending over time:**
```
Show CPU usage trends over the last 24 hours
Display error rate changes throughout the day
Find peak activity times this month
```

**Time series analysis:**
```
Group events by hour for the last day
Show daily patterns for the past month
Display seasonal trends over the year
```

---

## Filtering and Searching

### Text-Based Filtering

**Keyword searches:**
```
Find events containing "timeout"
Show logs with "connection refused"
Display messages mentioning "memory"
```

**Pattern matching:**
```
Find IP addresses starting with "192.168"
Show phone numbers in the format XXX-XXX-XXXX
Display emails ending with "@company.com"
```

**Exclusion filters:**
```
Show all events except informational ones
Find errors but exclude warnings
Display logs without debug messages
```

### Field-Based Filtering

**Numeric filtering:**
```
Show events where response_time > 1000
Find servers with CPU usage above 80%
Display transactions with amount > $1000
```

**String filtering:**
```
Show events where user starts with "admin"
Find hosts containing "prod" in the name
Display sources ending with ".log"
```

**Boolean conditions:**
```
Show events where success=true and duration<500
Find failed logins OR locked accounts
Display events where (status=200 OR status=201) AND method=POST
```

### Complex Filtering

**Multi-condition filters:**
```
Show failed login attempts from external IP addresses during business hours
Find high CPU usage events on production servers excluding scheduled maintenance
Display security events with critical severity from the last 24 hours excluding known false positives
```

**Nested conditions:**
```
Show events where (user="admin" OR user="root") AND (action="login" OR action="sudo") AND host LIKE "prod-*"
```

---

## Statistical Analysis

### Basic Statistics

**Counting and totals:**
```
Count events by source
Show total bytes transferred by host
Display number of unique users per day
```

**Averages and sums:**
```
Average response time by server
Total memory usage across all hosts
Mean CPU utilization per application
```

**Min/Max values:**
```
Highest CPU usage in the last hour
Lowest disk space by server
Peak network traffic today
```

### Grouping and Aggregation

**Group by single field:**
```
Count errors by server
Sum bandwidth by user
Average response time by endpoint
```

**Multiple grouping:**
```
Count events by source and host
Average CPU usage by server and time of day
Total transactions by user and product category
```

**Time-based grouping:**
```
Count events by hour for the last day
Sum bytes transferred by day for the last month
Average response time by week for the last quarter
```

### Advanced Statistics

**Percentiles and distributions:**
```
Show 95th percentile response time
Display median CPU usage by server
Find response time distribution by endpoint
```

**Ratios and rates:**
```
Calculate error rate as percentage of total requests
Show success ratio by application
Display growth rate month over month
```

**Statistical functions:**
```
Show standard deviation of response times
Calculate variance in CPU usage
Display correlation between memory and response time
```

---

## Advanced Analytics

### Trend Analysis

**Growth and decline:**
```
Show user growth trend over the last year
Display declining performance metrics
Find increasing error rates by service
```

**Seasonal patterns:**
```
Identify weekly traffic patterns
Show monthly usage seasonality
Display holiday impact on system performance
```

**Comparative trends:**
```
Compare this quarter's performance with last quarter
Show year-over-year growth in user activity
Display trend differences between regions
```

### Anomaly Detection

**Unusual patterns:**
```
Find unusual spikes in error rates
Detect abnormal user login patterns
Identify unexpected network traffic
```

**Baseline comparisons:**
```
Show metrics that deviate from normal baseline
Find servers performing outside typical ranges
Detect applications with unusual resource consumption
```

**Time-based anomalies:**
```
Identify unusual activity outside business hours
Find weekend patterns that differ from weekdays
Detect holiday anomalies in system usage
```

### Predictive Analytics

**Forecasting:**
```
Predict CPU usage for the next 4 hours
Forecast disk space needs for next month
Estimate user growth for next quarter
```

**Capacity planning:**
```
When will we reach 80% disk capacity?
Predict bandwidth requirements for next year
Estimate server needs based on user growth
```

**Risk assessment:**
```
Identify servers at risk of failure
Predict potential security threats
Forecast system performance degradation
```

---

## Industry-Specific Examples

### IT Operations and Infrastructure

**System performance:**
```
Show server health dashboard for production environment
Find performance bottlenecks across all applications
Display network latency by geographic region
Monitor database query performance and resource usage
```

**Capacity management:**
```
Show disk space utilization trends across all servers
Find servers approaching memory limits
Display network bandwidth usage by department
Monitor storage growth rates and predict capacity needs
```

**Security monitoring:**
```
Find failed login attempts from external IP addresses
Show privilege escalation events in the last 24 hours
Display unauthorized access attempts to sensitive systems
Monitor data exfiltration patterns and suspicious file transfers
```

### Application Performance Monitoring

**Web application metrics:**
```
Show page load times by geographic region
Display API response times and error rates
Find slow database queries affecting user experience
Monitor user session duration and abandonment rates
```

**Error tracking:**
```
Show application errors grouped by severity and component
Find error patterns that correlate with deployments
Display user-reported issues with system error correlation
Monitor exception rates and their impact on business metrics
```

**User experience:**
```
Show user journey completion rates by path
Display mobile vs desktop performance differences
Find pages with highest bounce rates and loading issues
Monitor real user performance metrics across all browsers
```

### Business Intelligence and Analytics

**Sales and revenue:**
```
Show sales performance by product line and region
Display revenue trends with seasonal adjustments
Find top-performing sales representatives and their activities
Monitor conversion rates from marketing campaigns to sales
```

**Customer analytics:**
```
Show customer segmentation by behavior and value
Display customer lifetime value trends over time
Find customer churn indicators and retention metrics
Monitor customer satisfaction scores and feedback patterns
```

**Marketing effectiveness:**
```
Show campaign performance by channel and audience
Display website traffic sources and conversion rates
Find content engagement metrics across all platforms
Monitor social media sentiment and brand mentions
```

### Financial Services

**Transaction monitoring:**
```
Show transaction volumes by type and geographic region
Display payment processing times and failure rates
Find unusual transaction patterns that may indicate fraud
Monitor regulatory compliance metrics and exception rates
```

**Risk management:**
```
Show credit risk exposure by portfolio and region
Display market volatility impact on trading positions
Find operational risk events and their business impact
Monitor liquidity ratios and regulatory capital requirements
```

**Compliance reporting:**
```
Show audit trail completeness for all critical transactions
Display regulatory reporting accuracy and timeliness
Find compliance violations and their resolution status
Monitor data privacy compliance and access controls
```

### Healthcare and Life Sciences

**Patient monitoring:**
```
Show patient vital sign trends and alert patterns
Display medication administration compliance rates
Find adverse event patterns and their correlation with treatments
Monitor patient satisfaction scores and feedback themes
```

**Operational efficiency:**
```
Show hospital bed utilization rates and patient flow
Display staff scheduling efficiency and overtime patterns
Find equipment maintenance needs and utilization rates
Monitor supply chain performance and inventory levels
```

**Research and development:**
```
Show clinical trial enrollment and completion rates
Display research data quality and completeness metrics
Find correlations between treatments and patient outcomes
Monitor regulatory submission timelines and approval rates
```

---

## Query Optimization Tips

### Efficient Query Construction

**Start specific, then broaden:**
```
Good: "Show HTTP 500 errors from web-app-01 in the last hour"
Better than: "Show me errors" (too broad initially)
```

**Use appropriate time ranges:**
```
Efficient: "Show CPU usage for the last 24 hours"
Less efficient: "Show all CPU usage data" (unbounded)
```

**Leverage field knowledge:**
```
Optimized: "Show events where sourcetype=access_combined AND status>=400"
Generic: "Show web server error events"
```

### Performance Best Practices

**Filter early in the query:**
```
Efficient: Find specific hosts first, then analyze their data
Less efficient: Analyze all data, then filter by host
```

**Use summary data when available:**
```
Fast: "Show hourly CPU averages for the last week"
Slower: "Show individual CPU measurements for the last week"
```

**Batch related questions:**
```
Efficient: "Show CPU, memory, and disk usage for server-01"
Less efficient: Three separate queries for each metric
```

### Context and Conversation

**Build on previous queries:**
```
First: "Show login attempts from the last hour"
Follow-up: "Now show only the failed ones"
Refinement: "Group them by source IP"
```

**Use conversational context:**
```
"Show me server performance"
"Now compare with yesterday"
"Highlight any anomalies"
"Create an alert for unusual patterns"
```

**Reference previous results:**
```
"Export this data to Excel"
"Add this chart to my dashboard"
"Create an alert based on these conditions"
```

---

## Common Mistakes to Avoid

### Query Construction Issues

**Avoid overly vague queries:**
```
❌ "Show me data"
✅ "Show me error logs from the web server in the last hour"
```

**Don't forget time boundaries:**
```
❌ "Show all user activity"
✅ "Show user activity from the last 24 hours"
```

**Avoid conflicting conditions:**
```
❌ "Show events that are both successful and failed"
✅ "Show all events with their success status"
```

### Time Range Mistakes

**Unrealistic time ranges:**
```
❌ "Show minute-by-minute data for the last year"
✅ "Show daily averages for the last year"
```

**Timezone confusion:**
```
❌ "Show events from 9 AM to 5 PM" (unclear timezone)
✅ "Show events from 9 AM to 5 PM EST today"
```

**Past vs present tense confusion:**
```
❌ "Show me what will happen tomorrow"
✅ "Show me predictions for tomorrow based on historical data"
```

### Field and Data Issues

**Assuming field names:**
```
❌ "Show events where username=admin" (if field is actually 'user')
✅ "Show events for admin user" (let system map fields)
```

**Ignoring data types:**
```
❌ "Show numeric data as text"
✅ "Show response times as numbers for averaging"
```

**Case sensitivity assumptions:**
```
❌ "Show events where Status=ERROR" (might be lowercase)
✅ "Show events with error status" (system handles case)
```

### Analysis Mistakes

**Correlation vs causation:**
```
❌ "High CPU causes slow response times"
✅ "Show correlation between CPU usage and response times"
```

**Sample size issues:**
```
❌ "Calculate average from 2 data points"
✅ "Calculate average from sufficient sample size"
```

**Ignoring outliers:**
```
❌ "Average response time including timeouts"
✅ "Average response time excluding extreme outliers"
```

---

## Advanced Query Patterns

### Complex Conditional Logic

**Multiple conditions with precedence:**
```
Show events where (severity="critical" OR severity="high") AND 
(source="firewall" OR source="ids") AND 
timestamp > "2024-01-01" AND 
NOT (user="system" OR user="monitor")
```

**Nested logical operations:**
```
Find users who have (logged in more than 10 times today OR 
have admin privileges) AND (accessed sensitive data OR 
performed administrative actions) BUT are not in the 
authorized_users list
```

### Time-Based Complex Queries

**Rolling window analysis:**
```
Show the 7-day rolling average of CPU usage compared to 
the same period last month for all production servers
```

**Time-shifted comparisons:**
```
Compare this week's error rates with the average of the 
previous 4 weeks, highlighting servers that deviate more 
than 2 standard deviations
```

**Seasonal analysis:**
```
Show monthly traffic patterns adjusted for seasonal trends 
and highlight months that significantly deviate from 
expected seasonal behavior
```

### Multi-Dimensional Analysis

**Cross-tabulation queries:**
```
Create a cross-tab showing user activity by hour of day 
and day of week, with color coding for activity levels
```

**Hierarchical analysis:**
```
Show error rates grouped by region, then by data center, 
then by server, with drill-down capabilities
```

**Cohort analysis:**
```
Analyze user retention by signup month, showing how many 
users remain active after 1, 3, 6, and 12 months
```

---

## Getting Help with Queries

### Using the Query Assistant

**Ask for help:**
```
"How do I find errors from a specific server?"
"What's the best way to analyze response time trends?"
"Can you help me create a query for user activity?"
```

**Request examples:**
```
"Show me examples of security monitoring queries"
"Give me sample queries for performance analysis"
"What are common ways to analyze log data?"
```

**Query explanation:**
```
"Explain what this query does: [paste query]"
"Why isn't my query returning results?"
"How can I make this query more efficient?"
```

### Community and Resources

**Share successful patterns:**
- Document queries that work well for your use cases
- Share with team members for consistency
- Contribute to organization query library

**Learn from others:**
- Browse community query examples
- Attend query workshops and training sessions
- Participate in user forums and discussions

**Continuous improvement:**
- Regularly review and optimize frequently used queries
- Stay updated on new features and capabilities
- Experiment with advanced analytics features

---

*This guide is continuously updated with new examples and best practices. For the latest query patterns and advanced features, check the platform's built-in help system and community resources.*