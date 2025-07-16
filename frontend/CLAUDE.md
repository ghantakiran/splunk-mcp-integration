# Frontend Application - CLAUDE.md

## Inherits From
- [Main Project Guidelines](../CLAUDE.md)
- [Shared Standards](../CLAUDE.md#core-data-models)

## Service Overview
The Frontend application provides the user interface for the Splunk MCP Integration, offering a modern React-based chat interface, dashboard management, and visualization capabilities. It communicates with backend services through the API Gateway.

## Architecture
- **Framework**: React 18 with TypeScript
- **State Management**: Redux Toolkit or Zustand
- **UI Components**: Material-UI or Ant Design
- **Charts**: D3.js or Chart.js for visualizations
- **Real-time**: WebSocket for live updates

## Development Guidelines

### Code Structure
```
frontend/
├── src/
│   ├── components/           # React components
│   │   ├── Chat/            # Chat interface components
│   │   ├── Dashboard/       # Dashboard components
│   │   ├── Charts/          # Chart components
│   │   ├── Auth/            # Authentication components
│   │   ├── Profile/         # User profile components
│   │   └── Common/          # Shared components
│   ├── services/            # API services
│   │   ├── api.ts           # API client configuration
│   │   ├── auth.ts          # Authentication service
│   │   ├── chat.ts          # Chat service
│   │   ├── dashboard.ts     # Dashboard service
│   │   └── charts.ts        # Chart service
│   ├── hooks/               # Custom React hooks
│   │   ├── useAuth.ts       # Authentication hook
│   │   ├── useChat.ts       # Chat functionality hook
│   │   ├── useDashboard.ts  # Dashboard management hook
│   │   └── useCharts.ts     # Chart management hook
│   ├── store/               # State management
│   │   ├── authSlice.ts     # Authentication state
│   │   ├── chatSlice.ts     # Chat state
│   │   ├── dashboardSlice.ts # Dashboard state
│   │   └── index.ts         # Store configuration
│   ├── utils/               # Utility functions
│   │   ├── constants.ts     # Application constants
│   │   ├── helpers.ts       # Helper functions
│   │   ├── validators.ts    # Input validation
│   │   └── formatters.ts    # Data formatting
│   ├── types/               # TypeScript types
│   │   ├── auth.ts          # Authentication types
│   │   ├── chat.ts          # Chat types
│   │   ├── dashboard.ts     # Dashboard types
│   │   └── api.ts           # API response types
│   ├── App.tsx              # Main application component
│   └── index.tsx            # Application entry point
├── public/                  # Static assets
│   ├── index.html           # HTML template
│   └── favicon.ico          # Application icon
├── package.json             # Dependencies and scripts
├── tsconfig.json            # TypeScript configuration
├── Dockerfile               # Container configuration
└── README.md                # Frontend documentation
```

### Key Components

#### Chat Interface
- **Message Display**: Rich message rendering with markdown support
- **Input System**: Natural language input with autocomplete
- **Conversation History**: Persistent conversation management
- **Real-time Updates**: WebSocket for live message updates

#### Dashboard Management
- **Dashboard Builder**: Drag-and-drop dashboard creation
- **Panel Management**: Chart panel configuration and layout
- **Responsive Design**: Mobile and tablet support
- **Export Features**: Dashboard export in multiple formats

#### Chart Components
- **Chart Display**: Interactive chart rendering
- **Customization**: Chart styling and theming options
- **Interactions**: Zoom, pan, drill-down capabilities
- **Export**: Chart export functionality

#### Authentication
- **Login/Logout**: Secure authentication flow
- **Session Management**: Token handling and refresh
- **Role-based UI**: Permission-based component rendering
- **Profile Management**: User profile editing

## API Integration

### Service Configuration
```typescript
// API client configuration
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});
```

### Authentication Service
```typescript
interface AuthService {
  login(credentials: LoginCredentials): Promise<AuthResponse>;
  logout(): Promise<void>;
  refreshToken(): Promise<AuthResponse>;
  getCurrentUser(): Promise<User>;
}
```

### Chat Service
```typescript
interface ChatService {
  sendMessage(message: string, conversationId?: string): Promise<ChatResponse>;
  getConversationHistory(conversationId: string): Promise<Conversation>;
  getConversations(): Promise<Conversation[]>;
}
```

### Dashboard Service
```typescript
interface DashboardService {
  getDashboards(): Promise<Dashboard[]>;
  createDashboard(dashboard: CreateDashboardRequest): Promise<Dashboard>;
  updateDashboard(id: string, dashboard: UpdateDashboardRequest): Promise<Dashboard>;
  deleteDashboard(id: string): Promise<void>;
}
```

## State Management

### Authentication State
```typescript
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}
```

### Chat State
```typescript
interface ChatState {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  loading: boolean;
  error: string | null;
}
```

### Dashboard State
```typescript
interface DashboardState {
  dashboards: Dashboard[];
  currentDashboard: Dashboard | null;
  panels: Panel[];
  loading: boolean;
  error: string | null;
}
```

## Testing Guidelines

### Test Structure
```
src/
├── __tests__/              # Test files
│   ├── components/         # Component tests
│   ├── services/           # Service tests
│   ├── hooks/              # Hook tests
│   ├── utils/              # Utility tests
│   └── integration/        # Integration tests
├── __mocks__/              # Mock files
└── setupTests.ts           # Test setup
```

### Testing Patterns
- **Unit Tests**: Individual component and function testing
- **Integration Tests**: Component interaction testing
- **E2E Tests**: End-to-end user workflow testing
- **Visual Tests**: Component rendering validation

## Configuration

### Environment Variables
```bash
# API Configuration
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws

# Authentication
REACT_APP_AUTH_TIMEOUT=30000
REACT_APP_TOKEN_REFRESH_INTERVAL=300000

# Features
REACT_APP_ENABLE_CHAT=true
REACT_APP_ENABLE_DASHBOARDS=true
REACT_APP_ENABLE_EXPORTS=true

# Development
REACT_APP_LOG_LEVEL=info
REACT_APP_DEBUG=false
```

### Dependencies
- React 18 with TypeScript
- Redux Toolkit for state management
- Material-UI for UI components
- Axios for HTTP requests
- Socket.io for real-time communication
- Chart.js for chart rendering

## UI/UX Guidelines

### Design Principles
- **Responsive Design**: Mobile-first approach
- **Accessibility**: WCAG 2.1 AA compliance
- **Performance**: Optimized loading and rendering
- **Consistency**: Unified design language

### Component Standards
- **Reusable Components**: Modular component design
- **Props Validation**: TypeScript interfaces for props
- **Error Handling**: Graceful error display
- **Loading States**: Proper loading indicators

### User Experience
- **Intuitive Navigation**: Clear navigation structure
- **Feedback**: User action feedback
- **Error Messages**: Clear error communication
- **Help System**: Contextual help and documentation

## Performance Considerations

### Optimization Strategies
- **Code Splitting**: Lazy loading for route components
- **Memoization**: React.memo and useMemo for optimization
- **Bundle Optimization**: Webpack optimization
- **Image Optimization**: Compressed and lazy-loaded images

### Monitoring
- **Performance Metrics**: Core Web Vitals tracking
- **Error Tracking**: Client-side error monitoring
- **User Analytics**: User interaction tracking
- **Load Times**: Page load performance monitoring

## Security Considerations

### Client-Side Security
- **XSS Prevention**: Input sanitization and validation
- **CSRF Protection**: Token-based protection
- **Secure Storage**: Secure token storage
- **Content Security Policy**: CSP headers

### API Security
- **Token Management**: Secure token handling
- **Request Validation**: Input validation
- **Error Handling**: Secure error messages
- **Rate Limiting**: Client-side rate limiting

## Development Workflow

### Local Development
1. Install dependencies: `npm install`
2. Set environment variables
3. Start development server: `npm start`
4. Access at `http://localhost:3000`

### Build Process
1. Production build: `npm run build`
2. Test build: `npm run test`
3. Lint code: `npm run lint`
4. Type check: `npm run type-check`

### Deployment
- Docker containerization
- Environment-based configuration
- Health check endpoints
- CDN integration

## Current Implementation Status

### Completed Features
- Basic React application structure
- Docker configuration for development
- Package.json with TypeScript setup
- Basic component structure

### Planned Features
- Chat interface implementation
- Dashboard management system
- Authentication integration
- Real-time features
- Mobile responsive design

## Next Steps
- Implement chat interface with natural language input
- Create dashboard builder with drag-and-drop functionality
- Add authentication and user management
- Implement real-time updates with WebSocket
- Add comprehensive testing suite
- Optimize performance and accessibility