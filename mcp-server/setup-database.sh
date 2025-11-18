#!/bin/bash
# Database Setup Script for MCP Server
# =====================================

set -e

echo "MCP Server Database Setup"
echo "========================="
echo ""

# Check if PostgreSQL is installed
if command -v psql &> /dev/null; then
    echo "✓ PostgreSQL found"
    PSQL_CMD="psql"
elif command -v docker &> /dev/null; then
    echo "✓ Docker found - will use Docker for PostgreSQL"
    USE_DOCKER=true
else
    echo "✗ Neither PostgreSQL nor Docker found"
    echo ""
    echo "Please install PostgreSQL:"
    echo "  macOS: brew install postgresql@15"
    echo "  Linux: sudo apt-get install postgresql"
    echo ""
    echo "Or use Docker:"
    echo "  docker run --name postgres-banking -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=banking -p 5432:5432 -d postgres:15"
    exit 1
fi

# Database configuration
DB_NAME="${DB_NAME:-banking}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

if [ "$USE_DOCKER" = true ]; then
    echo ""
    echo "Using Docker for PostgreSQL..."
    echo ""
    
    # Check if container exists
    if docker ps -a --format '{{.Names}}' | grep -q "^postgres-banking$"; then
        echo "Container 'postgres-banking' already exists"
        if ! docker ps --format '{{.Names}}' | grep -q "^postgres-banking$"; then
            echo "Starting container..."
            docker start postgres-banking
            echo "Waiting for PostgreSQL to start..."
            sleep 3
        else
            echo "Container is already running"
        fi
    else
        echo "Creating PostgreSQL container..."
        docker run --name postgres-banking \
            -e POSTGRES_PASSWORD="${DB_PASSWORD}" \
            -e POSTGRES_DB="${DB_NAME}" \
            -e POSTGRES_USER="${DB_USER}" \
            -p "${DB_PORT}:5432" \
            -d postgres:15
        
        echo "Waiting for PostgreSQL to start..."
        sleep 5
    fi
    
    # Wait for PostgreSQL to be ready
    echo "Waiting for PostgreSQL to be ready..."
    for i in {1..30}; do
        if docker exec postgres-banking pg_isready -U "${DB_USER}" > /dev/null 2>&1; then
            echo "PostgreSQL is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "Error: PostgreSQL did not become ready in time"
            exit 1
        fi
        sleep 1
    done
    
    # Run schema using docker exec
    echo "Running schema migration..."
    docker exec -i postgres-banking psql -U "${DB_USER}" -d "${DB_NAME}" < schema.sql
    
    echo ""
    echo "✓ Database setup complete!"
    echo ""
    echo "Connection string:"
    echo "  postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    echo ""
    echo "To stop the container:"
    echo "  docker stop postgres-banking"
    echo ""
    echo "To start it again:"
    echo "  docker start postgres-banking"
    
else
    echo ""
    echo "Using local PostgreSQL..."
    echo ""
    
    # Check if database exists
    if $PSQL_CMD -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -lqt | cut -d \| -f 1 | grep -qw "${DB_NAME}"; then
        echo "Database '${DB_NAME}' already exists"
        read -p "Do you want to recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Dropping database..."
            $PSQL_CMD -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -c "DROP DATABASE ${DB_NAME};"
            echo "Creating database..."
            $PSQL_CMD -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -c "CREATE DATABASE ${DB_NAME};"
        fi
    else
        echo "Creating database '${DB_NAME}'..."
        $PSQL_CMD -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -c "CREATE DATABASE ${DB_NAME};"
    fi
    
    echo "Running schema migration..."
    $PSQL_CMD -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -d "${DB_NAME}" < schema.sql
    
    echo ""
    echo "✓ Database setup complete!"
    echo ""
    echo "Connection string:"
    echo "  postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
fi

