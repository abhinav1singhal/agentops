# Dashboard Web

Real-time monitoring dashboard for AgentOps - AI-powered Cloud Run health monitoring with comprehensive analytics and incident management.

> **✅ Production Ready:** Enhanced v2.0.0 with dark mode, analytics dashboard, incident details modal, and AI-powered insights visualization.

## 🎯 Overview

The Dashboard Web is the visual interface for the AgentOps monitoring system. It provides real-time visualization of Cloud Run service health, AI-powered incident analysis, and comprehensive analytics to help teams understand and respond to service degradations quickly.

### Key Features

- 🎨 **Modern UI** - Professional component library with custom Tailwind theme
- 🌙 **Dark Mode** - Full dark mode support with localStorage persistence
- 📊 **Real-time Monitoring** - Live service health metrics with auto-refresh (10s)
- 🤖 **AI Insights** - Displays Gemini-powered recommendations and explanations
- 📈 **Analytics Dashboard** - MTTR tracking, success rates, and incident trends
- 🔍 **Detailed Incident Views** - Slide-in modal with complete incident history
- ⚡ **Smooth Animations** - Framer Motion animations throughout
- 📱 **Responsive Design** - Works on desktop, tablet, and mobile
- 🎭 **Loading States** - Shimmer skeleton screens for better UX

## 🏗️ Architecture

### Technology Stack

```
Frontend Framework: Next.js 14.0.4 (React 18.2.0)
Styling: Tailwind CSS 3.3.6 (custom configuration)
Animations: Framer Motion 10.16.16
Charts: Recharts 2.10.3
Icons: Lucide React 0.294.0
Dates: date-fns 2.30.0
Data Fetching: Native fetch API
Build: Multi-stage Docker (Node 18-slim)
```

### Component Architecture

```
dashboard-web/
├── components/           # Reusable UI components
│   ├── StatusBadge.js         # Status indicators with animations
│   ├── MetricCard.js          # Service health card display
│   ├── IncidentCard.js        # Incident preview cards
│   ├── LoadingSkeleton.js     # Loading state placeholders
│   ├── DarkModeToggle.js      # Theme switcher
│   ├── IncidentDetailsModal.js # Full incident details panel
│   └── AnalyticsSection.js    # Analytics dashboard with charts
├── pages/
│   ├── index.js              # Main dashboard page
│   └── api/
│       └── health.js         # Health check endpoint
├── public/                   # Static assets
├── tailwind.config.js        # Custom Tailwind configuration
├── next.config.js            # Next.js configuration
├── Dockerfile                # Multi-stage production build
├── package.json              # Dependencies
└── README.md                 # This file
```

### Component Library

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **StatusBadge** | Visual status indicator | Color-coded (healthy/warning/critical), animated pulse, size variants |
| **MetricCard** | Service metrics display | Error rate, latency P95, request count, color-coded thresholds, hover effects |
| **IncidentCard** | Incident summary | AI recommendation preview, confidence score, MTTR, action status |
| **LoadingSkeleton** | Loading states | Shimmer animation, multiple types (card/incident/chart) |
| **DarkModeToggle** | Theme switcher | Persistent preference, smooth transitions, sun/moon icons |
| **IncidentDetailsModal** | Full incident view | Slide-in animation, complete timeline, AI analysis, error logs |
| **AnalyticsSection** | Dashboard analytics | Interactive charts, MTTR, success rate, incident breakdown |

## 🚀 Quick Start

### Prerequisites

- Node.js >= 18.0.0
- npm or yarn
- Supervisor API running and accessible

### Local Development

1. **Install dependencies**
```bash
cd apps/dashboard-web
npm install
```

2. **Set environment variables**

Create `.env.local`:
```bash
NEXT_PUBLIC_SUPERVISOR_API_URL=http://localhost:8080
NEXT_PUBLIC_PROJECT_ID=your-gcp-project-id
```

3. **Run development server**
```bash
npm run dev
```

The dashboard will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
npm start
```

## 🐳 Docker Deployment

### Build Docker Image

```bash
docker build -t dashboard-web .
```

### Run Container Locally

```bash
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_SUPERVISOR_API_URL=http://localhost:8080 \
  -e NEXT_PUBLIC_PROJECT_ID=your-project \
  dashboard-web
```

## ☁️ Cloud Run Deployment

### Using PowerShell (Windows)

```powershell
# Set variables
$PROJECT_ID = "agent-ops-2025"
$REGION = "us-central1"
$SUPERVISOR_URL = "https://supervisor-api-xxx.run.app"

# Build and push to Container Registry
cd apps/dashboard-web
gcloud builds submit --tag gcr.io/$PROJECT_ID/dashboard-web

# Deploy to Cloud Run
gcloud run deploy dashboard-web `
  --image gcr.io/$PROJECT_ID/dashboard-web `
  --platform managed `
  --region $REGION `
  --min-instances 0 `
  --max-instances 5 `
  --port 3000 `
  --allow-unauthenticated `
  --set-env-vars "NEXT_PUBLIC_SUPERVISOR_API_URL=$SUPERVISOR_URL,NEXT_PUBLIC_PROJECT_ID=$PROJECT_ID"
```

### Using Bash (Linux/Mac)

```bash
# Set variables
export PROJECT_ID="agent-ops-2025"
export REGION="us-central1"
export SUPERVISOR_URL="https://supervisor-api-xxx.run.app"

# Build and deploy
cd apps/dashboard-web
gcloud builds submit --tag gcr.io/$PROJECT_ID/dashboard-web

gcloud run deploy dashboard-web \
  --image gcr.io/$PROJECT_ID/dashboard-web \
  --platform managed \
  --region $REGION \
  --min-instances 0 \
  --max-instances 5 \
  --port 3000 \
  --allow-unauthenticated \
  --set-env-vars "NEXT_PUBLIC_SUPERVISOR_API_URL=$SUPERVISOR_URL,NEXT_PUBLIC_PROJECT_ID=$PROJECT_ID"
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `NEXT_PUBLIC_SUPERVISOR_API_URL` | Supervisor API endpoint | Yes | `http://localhost:8080` |
| `NEXT_PUBLIC_PROJECT_ID` | GCP Project ID | No | `N/A` |
| `PORT` | Server port | No | `3000` |
| `NODE_ENV` | Environment | No | `production` |

### Tailwind Theme Customization

The dashboard uses a custom Tailwind configuration with health-based color palette:

```javascript
// tailwind.config.js
colors: {
  healthy: { /* Green shades */ },
  warning: { /* Yellow shades */ },
  critical: { /* Red shades */ },
  unknown: { /* Gray shades */ }
}
```

Custom animations:
- `pulse-slow` - 3s pulse for active states
- `slide-in-right` - Modal entrance
- `shimmer` - Loading skeleton effect
- `fade-in` - Smooth appearance

## 📊 Dashboard Features

### 1. System Health Overview

**Location:** Header section

**Displays:**
- Overall system status badge (animated for non-healthy states)
- Aggregate counts: Healthy, Warning, Critical services
- Last update timestamp
- Manual scan trigger button
- Dark mode toggle

### 2. Service Monitoring Grid

**Location:** Main content area

**Each service card shows:**
- Service name and region
- Status badge with animation
- Error rate (color-coded by threshold)
- Latency P95 (color-coded by threshold)
- Request count (formatted K/M)
- Last checked time (relative format)
- Hover effects and click interactions

**Color-coded thresholds:**
- Error Rate: <2% green, 2-5% yellow, >5% red
- Latency: <300ms green, 300-500ms yellow, >500ms red

### 3. Recent Incidents

**Location:** Below services grid

**Incident cards display:**
- Service name
- Status badge
- Started time (relative)
- AI recommendation (action type)
- Confidence score with progress bar
- MTTR (if resolved)
- Action status (if completed)

**Click incident card → Opens detailed modal**

### 4. Incident Details Modal

**Triggered by:** Clicking any incident card

**Displays:**
- **Service Information:** Name, region, duration
- **Timeline:** Detection, remediation start, resolution
- **Metrics:** Error rate, latency, request count, MTTR
- **AI Recommendation:** Action, confidence, reasoning, risk assessment
- **AI Explanation:** Full Gemini-powered analysis
- **Action Result:** Success/failure status, details, modifications
- **Error Logs:** Up to 10 most recent error samples

**Features:**
- Slide-in animation from right
- Smooth transitions (Framer Motion)
- Click backdrop or X to close
- Scrollable content for long incidents
- Dark mode compatible

### 5. Analytics Dashboard

**Location:** Below incidents (when incidents exist)

**Displays:**
- **Total Incidents:** Counter with breakdown
- **Resolved Incidents:** Success count
- **Failed Incidents:** Failure count
- **Pending Incidents:** In-progress count
- **Average MTTR:** Mean Time To Recovery in minutes
- **Action Success Rate:** Percentage with progress bar
- **Incidents by Service Chart:** Interactive bar chart showing resolved/failed/pending per service

**Chart Features:**
- Recharts ResponsiveContainer (auto-sizing)
- Color-coded bars (green/red/yellow)
- Tooltip on hover
- Legend for clarity
- Dark mode compatible

### 6. Dark Mode

**Activation:** Click sun/moon icon in header

**Features:**
- Persisted to localStorage
- Instant theme switching
- All components support dark mode
- Smooth color transitions
- Accessible contrast ratios (WCAG AA)

**Color scheme:**
- Light: Blue/indigo gradient background
- Dark: Gray gradient background
- All components have dark variants

## 🔄 Data Flow

```
Dashboard (Browser)
    ↓
    → Fetch /services/status (10s interval)
    → Fetch /incidents?limit=10 (10s interval)
    ↓
    For each incident:
      → Fetch /incidents/{id} (full details)
      → Fetch /explain/{id} (AI explanation)
    ↓
Display in UI:
  - MetricCard components (services)
  - IncidentCard components (incidents)
  - AnalyticsSection (aggregated data)
    ↓
User clicks incident:
    → IncidentDetailsModal opens
    → Displays complete incident data
```

### API Integration

**Endpoints Used:**

```
GET /services/status
- Returns array of service health data
- Used by: MetricCard components
- Refresh: Every 10 seconds

GET /incidents?limit=10
- Returns recent incidents
- Used by: IncidentCard components, Analytics
- Refresh: Every 10 seconds

GET /incidents/{incident_id}
- Returns full incident details
- Used by: Enhanced incident data, modal
- Called: On initial load for recent incidents

POST /explain/{incident_id}
- Returns Gemini AI explanation
- Used by: IncidentDetailsModal
- Called: On-demand for incidents without explanation

POST /health/scan
- Triggers manual health scan
- Used by: Trigger Scan button
- Called: On user click
```

## 🎨 UI/UX Highlights

### Visual Design
- **Clean Card-based Layout:** Services and incidents in card grids
- **Color-coded Status:** Instant visual feedback for health states
- **Smooth Animations:** Framer Motion for professional feel
- **Loading States:** Shimmer skeletons prevent layout shift
- **Hover Effects:** Subtle lift and shadow on cards
- **Responsive Grid:** 1-3 columns based on screen size

### Interactions
- **Auto-refresh:** Data updates every 10 seconds automatically
- **Click to Explore:** Incident cards open detailed modal
- **Smooth Transitions:** All state changes animated
- **Loading Feedback:** Skeleton screens while fetching
- **Error Handling:** User-friendly error messages

### Accessibility
- **Keyboard Navigation:** All interactive elements accessible
- **ARIA Labels:** Proper labeling for screen readers
- **Color Contrast:** WCAG AA compliant
- **Focus Indicators:** Visible focus states
- **Semantic HTML:** Proper heading hierarchy

## 🧪 Testing

### Manual Testing

1. **Service Health Display**
```bash
# Start supervisor-api
# Open dashboard
# Verify services appear with metrics
# Check color coding for different states
```

2. **Incident Details**
```bash
# Trigger incident in supervisor-api
# Click incident card
# Verify modal opens with full details
# Check AI recommendation and explanation
```

3. **Dark Mode**
```bash
# Click dark mode toggle
# Verify all components switch themes
# Refresh page - theme should persist
```

4. **Analytics**
```bash
# Create multiple incidents
# Verify analytics section appears
# Check MTTR calculation
# Verify chart displays correct data
```

### Component Testing

```bash
# Type check
npm run type-check

# Lint
npm run lint

# Build test
npm run build
```

## 🐛 Troubleshooting

### Issue: Dashboard shows "No services found"

**Cause:** Supervisor API not configured with TARGET_SERVICES

**Fix:**
```bash
# In supervisor-api, set environment variable:
TARGET_SERVICES=demo-app-a,demo-app-b
```

### Issue: "Failed to fetch services" error

**Cause:** Cannot connect to supervisor-api

**Fix:**
1. Verify supervisor-api is running
2. Check `NEXT_PUBLIC_SUPERVISOR_API_URL` environment variable
3. Check CORS settings if accessing from different domain
4. Verify network connectivity

```bash
# Test supervisor-api directly
curl http://localhost:8080/services/status
```

### Issue: Incidents don't show AI explanations

**Cause:** Supervisor API may not have Gemini enabled or incidents are too new

**Fix:**
- Ensure Vertex AI API is enabled in GCP
- Check supervisor-api has GEMINI_MODEL configured
- Wait for incident to transition beyond "action_pending" status

### Issue: Dark mode doesn't work

**Cause:** Tailwind dark mode not configured properly

**Fix:**
1. Verify `tailwind.config.js` has `darkMode: 'class'`
2. Clear browser localStorage
3. Rebuild application: `npm run build`

### Issue: Charts don't render

**Cause:** Recharts not loaded or no incident data

**Fix:**
1. Verify recharts installed: `npm list recharts`
2. Check browser console for errors
3. Ensure incidents exist (analytics only shows with data)

### Issue: Modal doesn't animate

**Cause:** Framer Motion not loaded

**Fix:**
```bash
# Reinstall dependencies
npm install framer-motion@^10.16.16
npm run build
```

### Issue: Build fails with "Module not found"

**Cause:** Missing dependencies after updates

**Fix:**
```bash
# Clean install
rm -rf node_modules package-lock.json
npm install
npm run build
```

## 📈 Performance Optimization

### Built-in Optimizations

- **Next.js Standalone Output:** Minimal production bundle
- **Code Splitting:** Automatic route-based splitting
- **Multi-stage Docker:** Optimized layer caching
- **Auto-refresh Throttling:** 10-second intervals prevent overload
- **Conditional Rendering:** Analytics only loads with data
- **Lazy Modal:** IncidentDetailsModal only renders when needed

### Recommendations

1. **Enable CDN:** Deploy behind Cloud CDN for faster global access
2. **Image Optimization:** Use Next.js Image component if adding images
3. **API Caching:** Consider SWR for better data fetching (already installed)
4. **Bundle Analysis:** Use `@next/bundle-analyzer` to identify large deps

## 🔐 Security

### Authentication

Currently, the dashboard is deployed with `--allow-unauthenticated` for demo purposes.

**For production, add authentication:**

```bash
# Deploy with authentication required
gcloud run deploy dashboard-web \
  --no-allow-unauthenticated \
  ...

# Add IAM binding for users
gcloud run services add-iam-policy-binding dashboard-web \
  --member="user:email@example.com" \
  --role="roles/run.invoker"
```

### CORS Configuration

If supervisor-api is on different domain, ensure CORS is configured:

```python
# In supervisor-api main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dashboard-web-xxx.run.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🔄 Roadmap

### Phase 4 (Future Enhancements)

- [ ] WebSocket integration for real-time updates (eliminate polling)
- [ ] Historical metric charts (24h/7d trends)
- [ ] Service details page (click service for detailed view)
- [ ] Incident filtering and search
- [ ] Export incidents to CSV/JSON
- [ ] Custom alert thresholds per service
- [ ] Mobile app (React Native)
- [ ] Multi-project support
- [ ] User preferences panel
- [ ] Notification system (desktop alerts)

## 📚 Related Documentation

- [Supervisor API Documentation](../supervisor-api/README.MD)
- [Fixer Agent Documentation](../fixer-agent/README.md)
- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Framer Motion Documentation](https://www.framer.com/motion/)
- [Recharts Documentation](https://recharts.org/)

## 🤝 Contributing

### Code Style

- Use functional components with hooks
- Follow existing naming conventions
- Add PropTypes or TypeScript types for components
- Write descriptive commit messages
- Test dark mode compatibility

### Component Guidelines

```javascript
// Component template
import React from 'react';

const MyComponent = ({ prop1, prop2 }) => {
  // Logic here

  return (
    <div className="bg-white dark:bg-gray-800">
      {/* Content */}
    </div>
  );
};

export default MyComponent;
```

### Adding New Features

1. Create component in `components/` directory
2. Add dark mode styles (use `dark:` prefix)
3. Test with loading states
4. Update this README
5. Commit with descriptive message

## 📝 Version History

### v2.0.0 (Current)
- ✅ Added custom Tailwind configuration with health-based colors
- ✅ Created component library (7 components)
- ✅ Implemented dark mode with persistence
- ✅ Added loading skeletons with shimmer effect
- ✅ Enhanced incident data fetching (AI explanations)
- ✅ Created incident details modal with animations
- ✅ Added analytics dashboard with interactive charts
- ✅ System health overview in header
- ✅ Framer Motion animations throughout
- ✅ Responsive grid layouts

### v1.0.0
- Basic service monitoring
- Simple incident list
- Manual scan trigger
- Light theme only

## 📄 License

Part of the AgentOps project. See root LICENSE file.

---

## 🎯 Quick Reference

**Local Development:**
```bash
npm install && npm run dev
```

**Production Build:**
```bash
npm run build && npm start
```

**Docker Build:**
```bash
docker build -t dashboard-web .
```

**Cloud Run Deploy:**
```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/dashboard-web
gcloud run deploy dashboard-web --image gcr.io/$PROJECT_ID/dashboard-web
```

---

**Dashboard Web v2.0.0** - Professional monitoring interface for AgentOps
Built with ❤️ using Next.js, Tailwind CSS, and Framer Motion
