/**
 * Demo App B - Node.js/Express Test Service with Fault Injection
 * Used to demonstrate AgentOps auto-remediation capabilities
 */

const express = require('express');
const winston = require('winston');
const cors = require('cors');

// Configure logging
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console({
      format: winston.format.simple()
    })
  ]
});

// Fault injection configuration
const faultConfig = {
  enabled: false,
  faultType: 'none', // 'none', '5xx', 'latency', 'timeout'
  errorRate: 0, // 0-100 percentage
  latencyMs: 0,
  expiresAt: null
};

// Request counters
let requestCount = 0;
let errorCount = 0;

// Initialize Express app
const app = express();
const PORT = process.env.PORT || 8080;

// Middleware
app.use(cors());
app.use(express.json());

// Logging middleware
app.use((req, res, next) => {
  logger.info(`${req.method} ${req.path}`);
  next();
});

// Fault injection middleware
app.use((req, res, next) => {
  // Skip fault injection for health and fault management endpoints
  const skipPaths = ['/health', '/fault/status', '/fault/enable', '/fault/disable'];
  if (skipPaths.includes(req.path)) {
    return next();
  }

  requestCount++;

  // Check if fault injection is active
  if (!isFaultActive()) {
    return next();
  }

  // Determine if this request should have fault injected
  if (Math.random() * 100 < faultConfig.errorRate) {
    
    if (faultConfig.faultType === '5xx') {
      errorCount++;
      const errorCode = [500, 502, 503][Math.floor(Math.random() * 3)];
      logger.warn(`💥 Injecting ${errorCode} error (fault injection active)`);
      
      return res.status(errorCode).json({
        error: 'Simulated error',
        message: `This is a simulated ${errorCode} error for testing`,
        faultInjection: true,
        timestamp: new Date().toISOString()
      });
    }
    
    if (faultConfig.faultType === 'latency') {
      logger.warn(`⏱️  Injecting ${faultConfig.latencyMs}ms latency`);
      setTimeout(() => next(), faultConfig.latencyMs);
      return;
    }
    
    if (faultConfig.faultType === 'timeout') {
      logger.warn('⏱️  Injecting timeout (30s delay)');
      setTimeout(() => next(), 30000);
      return;
    }
  }

  next();
});

// Helper function to check if fault is active
function isFaultActive() {
  if (!faultConfig.enabled) {
    return false;
  }

  if (faultConfig.expiresAt && new Date() > new Date(faultConfig.expiresAt)) {
    // Fault expired, disable it
    faultConfig.enabled = false;
    faultConfig.faultType = 'none';
    logger.info('Fault injection expired and disabled');
    return false;
  }

  return true;
}

// Routes

app.get('/', (req, res) => {
  res.json({
    service: 'Demo App B',
    version: '1.0.0',
    status: isFaultActive() ? 'fault_injection_active' : 'healthy',
    timestamp: new Date().toISOString(),
    message: 'Hello from Demo App B! Use /fault endpoints to inject failures.'
  });
});

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    faultInjection: isFaultActive()
  });
});

app.get('/api/users', (req, res) => {
  res.json({
    users: [
      { id: 1, name: 'Alice', email: 'alice@example.com' },
      { id: 2, name: 'Bob', email: 'bob@example.com' },
      { id: 3, name: 'Charlie', email: 'charlie@example.com' }
    ],
    timestamp: new Date().toISOString()
  });
});

app.get('/api/products', (req, res) => {
  res.json({
    products: [
      { id: 1, name: 'Widget A', price: 19.99 },
      { id: 2, name: 'Widget B', price: 29.99 },
      { id: 3, name: 'Widget C', price: 39.99 }
    ],
    timestamp: new Date().toISOString()
  });
});

app.post('/api/orders', (req, res) => {
  // Simulate order processing
  const order = req.body;
  
  setTimeout(() => {
    res.json({
      success: true,
      orderId: Math.random().toString(36).substr(2, 9),
      order: order,
      timestamp: new Date().toISOString()
    });
  }, Math.random() * 50 + 10); // 10-60ms processing time
});

app.get('/metrics', (req, res) => {
  const successCount = requestCount - errorCount;
  const errorRate = requestCount > 0 ? (errorCount / requestCount * 100) : 0;

  res.json({
    totalRequests: requestCount,
    successCount: successCount,
    errorCount: errorCount,
    errorRatePct: Math.round(errorRate * 100) / 100,
    faultInjectionActive: isFaultActive(),
    timestamp: new Date().toISOString()
  });
});

app.get('/fault/status', (req, res) => {
  res.json({
    enabled: faultConfig.enabled,
    active: isFaultActive(),
    faultType: faultConfig.faultType,
    errorRate: faultConfig.errorRate,
    latencyMs: faultConfig.latencyMs,
    expiresAt: faultConfig.expiresAt,
    timestamp: new Date().toISOString()
  });
});

app.post('/fault/enable', (req, res) => {
  const {
    type = '5xx',
    error_rate = 15,
    latency_ms = 1000,
    duration = 300 // seconds
  } = req.query;

  // Validate inputs
  const errorRate = parseFloat(error_rate);
  const latencyMs = parseInt(latency_ms);
  const durationSec = parseInt(duration);

  if (errorRate < 0 || errorRate > 100) {
    return res.status(400).json({ error: 'error_rate must be between 0 and 100' });
  }

  if (latencyMs < 0) {
    return res.status(400).json({ error: 'latency_ms must be positive' });
  }

  if (durationSec < 0) {
    return res.status(400).json({ error: 'duration must be positive' });
  }

  // Enable fault injection
  faultConfig.enabled = true;
  faultConfig.faultType = type;
  faultConfig.errorRate = errorRate;
  faultConfig.latencyMs = latencyMs;
  faultConfig.expiresAt = new Date(Date.now() + durationSec * 1000).toISOString();

  logger.warn(
    `🔴 FAULT INJECTION ENABLED: type=${type}, error_rate=${errorRate}%, ` +
    `latency=${latencyMs}ms, duration=${durationSec}s`
  );

  res.json({
    message: 'Fault injection enabled',
    config: {
      type: type,
      errorRate: errorRate,
      latencyMs: latencyMs,
      duration: durationSec,
      expiresAt: faultConfig.expiresAt
    },
    warning: 'This service will now start failing. AgentOps should detect and remediate.',
    timestamp: new Date().toISOString()
  });
});

app.post('/fault/disable', (req, res) => {
  faultConfig.enabled = false;
  faultConfig.faultType = 'none';
  faultConfig.errorRate = 0;
  faultConfig.expiresAt = null;

  logger.info('✅ FAULT INJECTION DISABLED');

  res.json({
    message: 'Fault injection disabled',
    timestamp: new Date().toISOString()
  });
});

app.get('/stress', (req, res) => {
  const count = Math.min(parseInt(req.query.count) || 100, 1000); // Cap at 1000
  
  const results = {
    success: 0,
    errors: 0
  };

  for (let i = 0; i < count; i++) {
    try {
      // Simulate processing
      const start = Date.now();
      while (Date.now() - start < 1) {} // Busy wait 1ms
      results.success++;
    } catch (error) {
      results.errors++;
    }
  }

  res.json({
    message: `Stress test completed with ${count} iterations`,
    results: results,
    timestamp: new Date().toISOString()
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    path: req.path,
    timestamp: new Date().toISOString()
  });
});

// Error handler
app.use((err, req, res, next) => {
  logger.error(`Error: ${err.message}`, { error: err.stack });
  
  res.status(500).json({
    error: 'Internal Server Error',
    message: err.message,
    timestamp: new Date().toISOString()
  });
});

// Start server
app.listen(PORT, () => {
  logger.info(`Demo App B listening on port ${PORT}`);
  logger.info(`Environment: ${process.env.NODE_ENV || 'development'}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM signal received: closing HTTP server');
  process.exit(0);
});

process.on('SIGINT', () => {
  logger.info('SIGINT signal received: closing HTTP server');
  process.exit(0);
});