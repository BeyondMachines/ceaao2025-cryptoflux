#!/bin/bash

# Banking Security Training Application - Docker Setup Script
# This script helps you run the application with PostgreSQL

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print section headers
print_header() {
    echo
    print_color $YELLOW "============================================================"
    print_color $YELLOW "$1"
    print_color $YELLOW "============================================================"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_color $RED " Docker is not running. Please start Docker Desktop and try again."
        exit 1
    fi
    print_color $GREEN " Docker is running"
}

# Function to check if docker-compose is available
check_docker_compose() {
    if command -v docker-compose > /dev/null 2>&1; then
        DOCKER_COMPOSE="docker-compose"
    elif docker compose version > /dev/null 2>&1; then
        DOCKER_COMPOSE="docker compose"
    else
        print_color $RED " docker-compose or 'docker compose' is not available"
        exit 1
    fi
    print_color $GREEN " Using: $DOCKER_COMPOSE"
}

# Function to create docker directory and initialization scripts
setup_docker_files() {
    print_color $YELLOW " Setting up Docker configuration files..."
    
    # Create docker directory if it doesn't exist
    mkdir -p docker
    
    # Create logs directory for application logs
    mkdir -p logs
    
    print_color $GREEN " Docker directories created"
}

# Function to start Cryptoflux stack
start_cryptoflux() {
    print_header " STARTING CRYPTOFLUX STACK"

    # Start the services
    print_color $YELLOW " Starting local CryptoFlux environment"
    $DOCKER_COMPOSE -f docker-compose.yml --env-file .env up -d
    
    # Wait for services to be healthy
    print_color $YELLOW " Waiting for services to start..."
    sleep 10
    
    # Show service status
    $DOCKER_COMPOSE -f docker-compose.yml ps
    
    # Initialize database and populate with sample data
    print_color $YELLOW " Running database migrations..."
    sleep 5  # Give the app a moment to fully start
    docker exec cryptoflux-trading_ui flask db upgrade

    print_color $YELLOW " Copying schema from primary to DR..."
    source .env
    docker exec cryptoflux-postgres pg_dump -U ${DB_USER} -d ${DB_NAME} --schema-only --no-owner | \
        docker exec -i cryptoflux-postgres-dr psql -U ${DR_DB_USER} -d ${DR_DB_NAME}

    # Initialize database and populate with sample data
    print_color $YELLOW " Populating database with sample data..."
    sleep 5  # Give the app a moment to fully start
    docker exec cryptoflux-trading_ui python populate_db.py
    
    print_header " CRYPTOFLUX SETUP COMPLETE"
    print_color $GREEN "CryptoFlux Trading Application: http://localhost:5000"
    # print_color $GREEN "pgAdmin (Database Management): http://localhost:8080"
    # print_color $YELLOW "pgAdmin Login: admin@example.com / admin123"
    # print_color $YELLOW "pgAdmin Setup: host: postgres; user: bankuser; password: securepassword123"
    
}


# Function to stop all services
stop_services() {
    print_header "STOPPING ALL SERVICES"
    
    # Stop both possible stacks
    if [ -f "docker-compose.yml" ]; then
        print_color $YELLOW "Stopping CRYPTOFLUX stack..."
        $DOCKER_COMPOSE -f docker-compose.yml down
    fi
    
    print_color $GREEN "✅ All services stopped"
}

# Function to clean up (remove containers and volumes)
cleanup() {
    print_header "🧹 CLEANING UP"
    print_color $YELLOW "This will remove all containers, data volumes, and banking-app images!"
    print_color $YELLOW "The application will need to rebuild images on next startup."
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Stop and remove containers, volumes
        if [ -f "docker-compose.yml" ]; then
            $DOCKER_COMPOSE -f docker-compose.yml down -v
        fi

        # Remove banking-app related images
        print_color $YELLOW "Removing Cryptoflux images..."
        
        # Remove images that contain "banking" in the name (adjust pattern as needed)
        docker images --format "{{.Repository}}:{{.Tag}}" | grep -i cryptoflux | xargs -r docker rmi -f 2>/dev/null || true

        # Alternative: Remove specific image names if you know them
        # docker rmi -f banking-app:latest 2>/dev/null || true
        # docker rmi -f banking_banking-app:latest 2>/dev/null || true

        # Remove any orphaned containers
        docker container prune -f
        docker volume prune -f
        
        print_color $GREEN "Cleanup complete - images will be rebuilt on next startup"
    else
        print_color $RED "Cleanup cancelled"
    fi
}

# Function to show logs
show_logs() {
    local service=$1
    if [ -z "$service" ]; then
        print_color $YELLOW "Showing logs for all services..."
        if [ -f ".env" ] && grep -q "postgresql" .env; then
            $DOCKER_COMPOSE -f docker-compose.yml logs -f
        else
            print_color $RED "No active configuration found"
        fi
    else
        print_color $YELLOW "Showing logs for $service..."
        docker logs -f "$service"
    fi
}

# Function to show status
show_status() {
    print_header "DOCKER SERVICES STATUS"
    
    # Check which configuration is active
    if [ -f ".env" ]; then
        if grep -q "postgresql" .env; then
            print_color $GREEN "Active Configuration: PostgreSQL"
            $DOCKER_COMPOSE -f docker-compose.yml ps
        fi
    else
        print_color $YELLOW "No active configuration found"
    fi
    
    # Show running containers
    echo
    print_color $YELLOW "All Cryptoflux App Containers:"
    docker ps --filter "name=cryptoflux" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

# Main menu function
show_menu() {
    print_header "CRYPTOFLUX TRAINING PLATFORM - DOCKER SETUP"
    echo "Choose your setup option:"
    echo
    echo "1)  Start Cryptoflux"
    echo "2)  Show status"
    echo "3)  Show logs"
    echo "4)  Stop all services"
    echo "5)  Cleanup (remove all data)"
    echo "6)  Help"
    echo "7) Exit"
    echo
}

# Help function
show_help() {
    print_header "HELP & TROUBLESHOOTING"
    echo "Important Files:"
    echo "   - .env: Configuration configuration"
    echo "   - configs/: Initialization scripts"
    echo
    echo "Troubleshooting:"
    echo "   - Check Docker is running: docker info"
    echo "   - View logs: ./setup.sh and choose option 3"
    echo "   - Reset everything: ./setup.sh and choose option 5"
    echo "   - Ports in use: 5000 (app), 5432 (db), 8080 (admin)"
    echo
    echo "Access Points:"
    echo "   - Cryptoflux App: http://localhost:5000"
    # echo "   - Database Admin: http://localhost:8080"
    echo
}

# Main script logic
main() {
    # Initial checks
    check_docker
    check_docker_compose
    setup_docker_files
    
    # Interactive menu
    while true; do
        show_menu
        read -p "Enter your choice (1-7): " choice
        
        case $choice in
            1)
                start_cryptoflux
                ;;
            2)
                show_status
                ;;
            3)
                echo "Which service logs? (cryptoflux-data_ingestion_service, cryptoflux-ext_api, cryptoflux-postgres, cryptoflux-trading_ui or Enter for all):"                
                read -p "Service name: " service
                show_logs "$service"
                ;;
            4)
                stop_services
                ;;
            5)
                cleanup
                ;;
            6)
                show_help
                ;;
            7)
                print_color $GREEN "Goodbye!"
                exit 0
                ;;
            *)
                print_color $RED "Invalid option. Please choose 1-7."
                ;;
        esac
        
        echo
        read -p "Press Enter to continue..."
    done
}

# Check if script is being called with parameters
if [ $# -eq 0 ]; then
    # No parameters, show interactive menu
    main
else
    # Handle command line parameters
    case $1 in
        "postgres")
            check_docker
            check_docker_compose
            setup_docker_files
            start_cryptoflux
            ;;
        "stop")
            check_docker_compose
            stop_services
            ;;
        "status")
            check_docker_compose
            show_status
            ;;
        "cleanup")
            check_docker_compose
            cleanup
            ;;
        "help")
            show_help
            ;;
        *)
            echo "Usage: $0 [postgres|stop|status|cleanup|help]"
            echo "Or run without parameters for interactive menu"
            exit 1
            ;;
    esac
fi