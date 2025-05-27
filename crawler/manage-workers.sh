#!/bin/bash

# PACS RIS Crawler - RQ Workers Management Script
# Usage: ./manage-workers.sh [command] [options]

set -e

# Auto-detect environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$SCRIPT_DIR" == *"/var/www/pacs-ris-crawler/crawler" ]]; then
    # Production environment
    PROJECT_DIR="/var/www/pacs-ris-crawler"
    CRAWLER_DIR="$PROJECT_DIR/crawler"
    VENV_PATH="$PROJECT_DIR/.venv"
else
    # Development environment - assume we're in the crawler directory
    CRAWLER_DIR="$SCRIPT_DIR"
    PROJECT_DIR="$(dirname "$CRAWLER_DIR")"
    VENV_PATH="$PROJECT_DIR/.venv"
fi

# Configuration
WORKER_SERVICE_PREFIX="pacs_ris_crawler-worker-indexer@"
WORKER_COUNT=4

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root/sudo
check_sudo() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run with sudo privileges"
        exit 1
    fi
}

# Get worker status
get_worker_status() {
    local worker_num=$1
    systemctl is-active "${WORKER_SERVICE_PREFIX}${worker_num}.service" 2>/dev/null || echo "inactive"
}

# Get all worker statuses
get_all_worker_statuses() {
    local active_count=0
    local inactive_count=0
    
    echo "=== Worker Status ==="
    for i in $(seq 1 $WORKER_COUNT); do
        local status=$(get_worker_status $i)
        if [ "$status" = "active" ]; then
            echo -e "Worker $i: ${GREEN}$status${NC}"
            ((active_count++))
        else
            echo -e "Worker $i: ${RED}$status${NC}"
            ((inactive_count++))
        fi
    done
    
    echo ""
    echo "Active: $active_count, Inactive: $inactive_count"
}

# Start workers
start_workers() {
    log_info "Starting $WORKER_COUNT RQ workers..."
    
    for i in $(seq 1 $WORKER_COUNT); do
        local service="${WORKER_SERVICE_PREFIX}${i}.service"
        log_info "Starting worker $i..."
        systemctl start "$service"
        
        # Wait a moment and check if it started successfully
        sleep 1
        local status=$(get_worker_status $i)
        if [ "$status" = "active" ]; then
            log_success "Worker $i started successfully"
        else
            log_error "Worker $i failed to start"
        fi
    done
    
    echo ""
    get_all_worker_statuses
}

# Stop workers
stop_workers() {
    log_info "Stopping $WORKER_COUNT RQ workers..."
    
    for i in $(seq 1 $WORKER_COUNT); do
        local service="${WORKER_SERVICE_PREFIX}${i}.service"
        log_info "Stopping worker $i..."
        systemctl stop "$service"
        
        # Wait a moment and check if it stopped
        sleep 1
        local status=$(get_worker_status $i)
        if [ "$status" = "inactive" ]; then
            log_success "Worker $i stopped successfully"
        else
            log_warning "Worker $i may still be running"
        fi
    done
    
    echo ""
    get_all_worker_statuses
}

# Restart workers (graceful - one by one)
restart_workers() {
    local graceful=${1:-true}
    
    if [ "$graceful" = "true" ]; then
        log_info "Gracefully restarting $WORKER_COUNT RQ workers (one by one)..."
        
        for i in $(seq 1 $WORKER_COUNT); do
            local service="${WORKER_SERVICE_PREFIX}${i}.service"
            log_info "Restarting worker $i..."
            systemctl restart "$service"
            
            # Wait for worker to start before continuing
            sleep 3
            local status=$(get_worker_status $i)
            if [ "$status" = "active" ]; then
                log_success "Worker $i restarted successfully"
            else
                log_error "Worker $i failed to restart"
            fi
        done
    else
        log_info "Restarting all $WORKER_COUNT RQ workers simultaneously..."
        systemctl restart "${WORKER_SERVICE_PREFIX}{1..$WORKER_COUNT}.service"
        sleep 2
    fi
    
    echo ""
    get_all_worker_statuses
}

# Enable workers for auto-start
enable_workers() {
    log_info "Enabling $WORKER_COUNT RQ workers for auto-start..."
    
    for i in $(seq 1 $WORKER_COUNT); do
        local service="${WORKER_SERVICE_PREFIX}${i}.service"
        systemctl enable "$service"
        log_success "Worker $i enabled for auto-start"
    done
}

# Disable workers from auto-start
disable_workers() {
    log_info "Disabling $WORKER_COUNT RQ workers from auto-start..."
    
    for i in $(seq 1 $WORKER_COUNT); do
        local service="${WORKER_SERVICE_PREFIX}${i}.service"
        systemctl disable "$service"
        log_success "Worker $i disabled from auto-start"
    done
}

# Get queue information
get_queue_info() {
    log_info "Getting RQ queue information..."
    log_info "Using crawler directory: $CRAWLER_DIR"
    log_info "Using virtual environment: $VENV_PATH"
    
    if [ ! -d "$CRAWLER_DIR" ]; then
        log_error "Crawler directory not found: $CRAWLER_DIR"
        return 1
    fi
    
    cd "$CRAWLER_DIR"
    
    if [ ! -f "$VENV_PATH/bin/activate" ]; then
        log_error "Virtual environment not found: $VENV_PATH"
        return 1
    fi
    
    source "$VENV_PATH/bin/activate"
    
    echo "=== Queue Information ==="
    PYTHONPATH=. rq info --interval 0
}

# Health check
health_check() {
    echo "=== RQ Workers Health Check - $(date) ==="
    echo ""
    
    # Check systemd services
    get_all_worker_statuses
    echo ""
    
    # Check queue information
    get_queue_info
    echo ""
    
    # Check for recent errors in logs
    log_info "Checking for recent errors (last 10 minutes)..."
    local error_count=$(journalctl -u "${WORKER_SERVICE_PREFIX}*" --since "10 minutes ago" 2>/dev/null | grep -i error | wc -l)
    
    if [ "$error_count" -eq 0 ]; then
        log_success "No errors found in recent logs"
    else
        log_warning "Found $error_count error(s) in recent logs"
        echo "Recent errors:"
        journalctl -u "${WORKER_SERVICE_PREFIX}*" --since "10 minutes ago" 2>/dev/null | grep -i error | tail -5
    fi
    
    echo ""
    
    # Check worker processes
    log_info "Checking worker processes..."
    local process_count=$(ps aux | grep "rq worker index" | grep -v grep | wc -l)
    echo "Active RQ worker processes: $process_count"
    
    if [ "$process_count" -ne "$WORKER_COUNT" ]; then
        log_warning "Expected $WORKER_COUNT workers, but found $process_count processes"
    else
        log_success "All $WORKER_COUNT workers are running"
    fi
}

# Monitor workers (continuous)
monitor_workers() {
    log_info "Starting continuous monitoring (Press Ctrl+C to stop)..."
    
    while true; do
        clear
        health_check
        echo ""
        echo "=== Live Process Information ==="
        ps aux | grep "rq worker" | grep -v grep || echo "No RQ worker processes found"
        echo ""
        echo "Refreshing in 10 seconds..."
        sleep 10
    done
}

# Show logs
show_logs() {
    local worker_num=${1:-"*"}
    local follow=${2:-false}
    
    if [ "$worker_num" = "*" ]; then
        log_info "Showing logs for all workers..."
        if [ "$follow" = "true" ]; then
            journalctl -u "${WORKER_SERVICE_PREFIX}*" -f
        else
            journalctl -u "${WORKER_SERVICE_PREFIX}*" --since "1 hour ago"
        fi
    else
        log_info "Showing logs for worker $worker_num..."
        if [ "$follow" = "true" ]; then
            journalctl -u "${WORKER_SERVICE_PREFIX}${worker_num}.service" -f
        else
            journalctl -u "${WORKER_SERVICE_PREFIX}${worker_num}.service" --since "1 hour ago"
        fi
    fi
}

# Show usage
show_usage() {
    echo "PACS RIS Crawler - RQ Workers Management Script"
    echo ""
    echo "Environment: $([ "$SCRIPT_DIR" == *"/var/www/"* ] && echo "Production" || echo "Development")"
    echo "Project Dir: $PROJECT_DIR"
    echo "Crawler Dir: $CRAWLER_DIR"
    echo "Virtual Env: $VENV_PATH"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  start                 Start all workers"
    echo "  stop                  Stop all workers"
    echo "  restart [fast]        Restart workers (graceful by default, 'fast' for simultaneous)"
    echo "  status                Show worker status"
    echo "  health                Perform health check"
    echo "  monitor               Start continuous monitoring"
    echo "  enable                Enable workers for auto-start on boot"
    echo "  disable               Disable workers from auto-start"
    echo "  logs [worker_num] [follow]  Show logs (all workers by default, 'follow' for live logs)"
    echo "  queue                 Show queue information"
    echo ""
    echo "Examples:"
    echo "  $0 start              # Start all workers"
    echo "  $0 restart            # Graceful restart (one by one)"
    echo "  $0 restart fast       # Fast restart (all at once)"
    echo "  $0 logs 1 follow      # Follow logs for worker 1"
    echo "  $0 logs               # Show recent logs for all workers"
    echo ""
}

# Main script logic
main() {
    local command=${1:-""}
    
    case "$command" in
        "start")
            check_sudo
            start_workers
            ;;
        "stop")
            check_sudo
            stop_workers
            ;;
        "restart")
            check_sudo
            local mode=${2:-"graceful"}
            if [ "$mode" = "fast" ]; then
                restart_workers false
            else
                restart_workers true
            fi
            ;;
        "status")
            get_all_worker_statuses
            ;;
        "health")
            health_check
            ;;
        "monitor")
            monitor_workers
            ;;
        "enable")
            check_sudo
            enable_workers
            ;;
        "disable")
            check_sudo
            disable_workers
            ;;
        "logs")
            local worker_num=${2:-"*"}
            local follow_flag=""
            if [ "$3" = "follow" ]; then
                follow_flag="true"
            fi
            show_logs "$worker_num" "$follow_flag"
            ;;
        "queue")
            get_queue_info
            ;;
        "help"|"-h"|"--help"|"")
            show_usage
            ;;
        *)
            log_error "Unknown command: $command"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@" 