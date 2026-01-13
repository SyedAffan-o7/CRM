#!/bin/bash

# Deployment script for AAA CRM
# Run this on your production server

set -e

echo "🚀 Starting deployment..."

# Variables
APP_NAME="aaa-crm"
DOCKER_IMAGE="your-registry/aaa-crm:latest"
COMPOSE_FILE="docker-compose.prod.yml"

# Pull latest changes
echo "📥 Pulling latest code..."
git pull origin main

# Build and deploy
echo "🔨 Building and deploying..."
docker-compose -f $COMPOSE_FILE down
docker-compose -f $COMPOSE_FILE up -d --build

# Run migrations
echo "🗄️ Running database migrations..."
docker-compose -f $COMPOSE_FILE exec -T app python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
docker-compose -f $COMPOSE_FILE exec -T app python manage.py collectstatic --noinput

# Restart services
echo "🔄 Restarting services..."
docker-compose -f $COMPOSE_FILE restart

# Health check
echo "🏥 Running health check..."
sleep 10
if curl -f http://localhost/health/ > /dev/null 2>&1; then
    echo "✅ Deployment successful!"
else
    echo "❌ Deployment failed! Check logs."
    exit 1
fi

echo "🎉 Deployment completed successfully!"
