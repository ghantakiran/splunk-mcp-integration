# Getting Started Guide - Splunk MCP Integration Platform

Welcome! This quick start guide will have you up and running with the Splunk MCP Integration Platform in minutes.

## What You'll Learn

In this guide, you'll learn how to:
- Log in and navigate the interface
- Ask your first natural language questions
- Create your first dashboard
- Set up basic alerts
- Export your first report

**Estimated Time: 15 minutes**

---

## Step 1: First Login (2 minutes)

### Access the Platform
1. Open your web browser and go to the URL provided by your administrator
2. You'll see the Splunk MCP Integration login page

### Login
1. Enter your **username** and **password**
2. If prompted, complete **Multi-Factor Authentication (MFA)**:
   - Open your authenticator app (Google Authenticator, Authy, etc.)
   - Enter the 6-digit code
3. Click **"Sign In"**

### Welcome Tour
- On first login, you'll see a brief welcome tour
- Click **"Take Tour"** to see key features, or **"Skip"** to start immediately
- You can always access the tour later from the Help menu (? icon)

---

## Step 2: Your First Query (3 minutes)

### Navigate to Chat
1. Click the **"Chat"** tab in the main navigation
2. You'll see a clean interface with a message input box at the bottom

### Ask a Simple Question
Try one of these example queries (just type and press Enter):

```
Show me recent error messages
```

```
What happened in the last hour?
```

```
Find login attempts from today
```

### Understand the Response
- Results appear as both **text summaries** and **visual charts**
- Hover over charts to see detailed information
- Click on chart elements to drill down into specific data points

### Try a Follow-up Question
The system remembers context, so you can ask follow-up questions:

```
Show only the critical ones
```

```
Group them by server
```

```
Create a chart from this data
```

---

## Step 3: Create Your First Dashboard (5 minutes)

### From Your Query Results
1. After running a query that creates a chart, look for the **"Add to Dashboard"** button
2. Click it and select **"Create New Dashboard"**
3. Give your dashboard a name like "My First Dashboard"
4. Click **"Create"**

### Add More Panels
1. In the dashboard view, click **"Add Panel"**
2. Try asking another question like:
   ```
   CPU usage over the last 24 hours
   ```
3. The system will automatically create an appropriate visualization
4. Click **"Add to Dashboard"** to add this panel

### Customize Your Dashboard
- **Resize panels**: Drag the corners to adjust size
- **Move panels**: Drag the title bar to reposition
- **Edit panels**: Click the edit icon on any panel
- **Save changes**: Click **"Save Dashboard"** when finished

### Dashboard Quick Tips
- Use the **time picker** to change the time range for all panels
- Click **"Edit"** mode to modify layout and add new panels
- Use **"Present"** mode for full-screen viewing

---

## Step 4: Set Up Your First Alert (3 minutes)

### Create an Alert from Chat
1. Go back to the **Chat** interface
2. Type a question that could be monitored:
   ```
   Show me server CPU usage above 80%
   ```

### Convert to Alert
1. After seeing the results, type:
   ```
   Create an alert for this condition
   ```
2. The system will guide you through alert setup:
   - **Name**: "High CPU Usage Alert" 
   - **Check frequency**: "Every 5 minutes"
   - **Notification**: Your email address
   - **When to alert**: "When any server exceeds 80% CPU"

### Verify Your Alert
1. Click the **"Alerts"** tab to see your new alert
2. Your alert will show as "Active" and begin monitoring immediately
3. You'll receive notifications when the condition is met

---

## Step 5: Export Your First Report (2 minutes)

### Generate a Report
1. Go back to a query result or dashboard you created earlier
2. Look for the **Export** button (download icon)
3. Click it to see export options

### Choose Export Format
Popular options:
- **PDF**: Great for sharing with stakeholders
- **Excel**: Perfect for further data analysis
- **PowerPoint**: Ideal for presentations

### Download Your Report
1. Select **PDF** for your first export
2. Choose any customization options (title, date range, etc.)
3. Click **"Generate Report"**
4. The file will download to your computer automatically

---

## Next Steps: Explore More Features

Now that you've completed the basics, here are some advanced features to explore:

### Natural Language Queries
Try more complex questions:
```
Compare error rates between production and staging environments
```

```
Show memory usage trends grouped by application
```

```
Find security events that occurred outside business hours
```

### Dashboard Features
- **Templates**: Browse the dashboard template gallery
- **Sharing**: Share dashboards with team members
- **Scheduling**: Set up automatic dashboard delivery
- **Embedding**: Embed dashboards in other applications

### Advanced Analytics
- **Predictive Analytics**: "Predict CPU usage for the next 4 hours"
- **Anomaly Detection**: "Show unusual patterns in network traffic"
- **Correlation Analysis**: "Find correlation between response time and CPU usage"

### Integration Features
- **Slack Integration**: Query data directly from Slack
- **Teams Integration**: Get alerts in Microsoft Teams
- **API Access**: Use REST APIs for custom integrations

---

## Quick Reference

### Common Query Patterns

| What you want | Example query |
|---------------|---------------|
| Recent errors | "Show me errors from the last hour" |
| Performance metrics | "CPU and memory usage by server" |
| User activity | "Login attempts in the last 24 hours" |
| Trends over time | "Response time trends this week" |
| Top items | "Top 10 users by activity" |
| Comparisons | "Compare today's traffic vs yesterday" |

### Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| New query | Ctrl/Cmd + N |
| Search history | Ctrl/Cmd + H |
| Export current view | Ctrl/Cmd + E |
| Toggle dark mode | Ctrl/Cmd + D |
| Help | F1 or ? |

### Quick Actions Menu
Right-click on any chart or result to:
- Add to dashboard
- Create alert from data
- Export in different formats
- Share with team members
- Drill down into details

---

## Getting Help

### In-Platform Help
- **Help Icon (?)**: Click for contextual help
- **Documentation**: Access full user manual
- **Video Tutorials**: Step-by-step visual guides
- **Community Forum**: Connect with other users

### Support Options
- **Live Chat**: Click the chat bubble for immediate help
- **Email Support**: support@yourorganization.com
- **Phone Support**: Available during business hours
- **Knowledge Base**: Searchable help articles

### Best Practices Tips
1. **Start Simple**: Begin with basic queries and build complexity
2. **Use Time Ranges**: Always specify relevant time periods
3. **Save Favorites**: Bookmark frequently used queries and dashboards
4. **Explore Examples**: Use the query example library for inspiration
5. **Ask Questions**: The AI is designed to understand natural language - be conversational!

---

## Troubleshooting Quick Fixes

**No results for your query?**
- Check the time range (try "last 24 hours")
- Simplify your question
- Verify you have permission to access the data

**Dashboard not loading?**
- Refresh the page
- Check your internet connection
- Try viewing in a different browser

**Export not working?**
- Check pop-up blockers
- Try a smaller time range
- Use a different export format

**Can't find a feature?**
- Use the search bar in the top navigation
- Check the user menu (your profile icon)
- Look in the "More" or "..." menus

---

## What's Next?

Congratulations! You've successfully:
- ✅ Logged in and navigated the platform
- ✅ Asked questions in natural language
- ✅ Created your first dashboard
- ✅ Set up an alert
- ✅ Exported a report

### Continue Learning
- Explore the [full User Manual](README.md) for detailed feature explanations
- Try the [Query Examples Guide](query-examples.md) for more advanced queries
- Learn about [Dashboard Best Practices](dashboard-guide.md)
- Set up [Advanced Alerts](alert-guide.md)

### Join the Community
- Participate in weekly office hours
- Share your dashboards and queries with the team
- Request new features through the feedback portal
- Help other users in the community forum

**Ready to become a power user? Explore the advanced features and make data-driven decisions with confidence!**

---

*Questions about getting started? Contact support or check our comprehensive FAQ section.*