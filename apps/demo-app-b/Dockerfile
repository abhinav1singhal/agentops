# Use official Node.js runtime as base image
FROM node:18-slim

# Set working directory
WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies (use npm install instead of npm ci)
RUN npm install --omit=dev

# Copy application code
COPY . .

# Node image already has a 'node' user, use that instead
# Change ownership to node user
RUN chown -R node:node /app

# Switch to node user
USER node

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:8080/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# Set environment variables
ENV NODE_ENV=production
ENV PORT=8080

# Run the application
CMD ["node", "index.js"]