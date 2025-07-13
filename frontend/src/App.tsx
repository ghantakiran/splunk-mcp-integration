import React from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Container, Typography, Box, Paper } from '@mui/material';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="lg">
        <Box sx={{ my: 4 }}>
          <Typography variant="h2" component="h1" gutterBottom align="center">
            Splunk MCP Integration
          </Typography>
          <Paper elevation={3} sx={{ p: 4, mt: 4 }}>
            <Typography variant="h4" component="h2" gutterBottom>
              Welcome to Splunk MCP Integration
            </Typography>
            <Typography variant="body1" paragraph>
              Transform your Splunk Enterprise into an intelligent, conversational analytics platform. 
              Chat with your data in natural language and get instant insights.
            </Typography>
            <Typography variant="h6" component="h3" gutterBottom sx={{ mt: 3 }}>
              Key Features:
            </Typography>
            <ul>
              <li>Natural Language Queries - Ask questions about your data in plain English</li>
              <li>Intelligent SPL Translation - Automatic conversion from natural language to Splunk SPL</li>
              <li>Interactive Dashboards - Create sophisticated dashboards without learning complex syntax</li>
              <li>Smart Alerts - Set up intelligent alerts through natural conversation</li>
              <li>Enterprise Security - Full RBAC integration and compliance with existing security policies</li>
            </ul>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>
              Status: Development Environment - Services Starting...
            </Typography>
          </Paper>
        </Box>
      </Container>
    </ThemeProvider>
  );
}

export default App;