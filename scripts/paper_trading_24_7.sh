#!/bin/bash
# DEPRECATED: paper_trading_24_7.sh
# 
# ⚠️  WARNING: This script is DEPRECATED but preserved for safety.
#     Use auto_trade.mode: paper in config/config.yaml instead.
#
# This script starts the deprecated paper_trading_24_7.py script.
# The main system now supports paper trading with better performance.
#
# PRESERVED FOR SAFETY: Contains service management features that could be useful.
# TODO: Integrate service management into main system, then remove this script.

# Configuration
SCRIPT_DIR="/Users/adrian/Desktop/Code/Trading/tracker"
VENV_PATH="$SCRIPT_DIR/venv"
PYTHON_SCRIPT="$SCRIPT_DIR/scripts/paper_trading_24_7.py"
CONFIG_FILE="$SCRIPT_DIR/config/paper_24_7.yaml"
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$LOG_DIR/paper_trading_24_7.pid"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to start the service
start_service() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Paper trading system is already running (PID: $PID)"
            return 1
        else
            echo "Removing stale PID file"
            rm -f "$PID_FILE"
        fi
    fi
    
    echo "Starting 24/7 paper trading system..."
    echo "Script: $PYTHON_SCRIPT"
    echo "Config: $CONFIG_FILE"
    echo "Logs: $LOG_DIR"
    
    # Activate virtual environment and start the service
    cd "$SCRIPT_DIR"
    source "$VENV_PATH/bin/activate"
    
    # Start the service in background
    nohup python "$PYTHON_SCRIPT" \
        --config "$CONFIG_FILE" \
        --initial-cash 100000 \
        --check-interval 300 \
        --max-restarts 10 \
        > "$LOG_DIR/paper_trading_24_7.out" \
        2> "$LOG_DIR/paper_trading_24_7.err" &
    
    # Save PID
    echo $! > "$PID_FILE"
    
    echo "Paper trading system started (PID: $!)"
    echo "Check logs: tail -f $LOG_DIR/paper_trading_24_7.out"
    echo "Check errors: tail -f $LOG_DIR/paper_trading_24_7.err"
}

# Function to stop the service
stop_service() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Stopping paper trading system (PID: $PID)..."
            kill -TERM $PID
            
            # Wait for graceful shutdown
            for i in {1..30}; do
                if ! ps -p $PID > /dev/null 2>&1; then
                    echo "Paper trading system stopped gracefully"
                    rm -f "$PID_FILE"
                    return 0
                fi
                sleep 1
            done
            
            # Force kill if still running
            echo "Force killing paper trading system..."
            kill -KILL $PID
            rm -f "$PID_FILE"
        else
            echo "Paper trading system is not running"
            rm -f "$PID_FILE"
        fi
    else
        echo "Paper trading system is not running"
    fi
}

# Function to check status
status_service() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Paper trading system is running (PID: $PID)"
            echo "Uptime: $(ps -o etime= -p $PID)"
            echo "Memory: $(ps -o rss= -p $PID) KB"
            return 0
        else
            echo "Paper trading system is not running (stale PID file)"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        echo "Paper trading system is not running"
        return 1
    fi
}

# Function to restart the service
restart_service() {
    stop_service
    sleep 2
    start_service
}

# Function to show logs
show_logs() {
    if [ -f "$LOG_DIR/paper_trading_24_7.out" ]; then
        echo "=== Recent logs ==="
        tail -n 50 "$LOG_DIR/paper_trading_24_7.out"
    else
        echo "No log file found"
    fi
}

# Function to show errors
show_errors() {
    if [ -f "$LOG_DIR/paper_trading_24_7.err" ]; then
        echo "=== Recent errors ==="
        tail -n 50 "$LOG_DIR/paper_trading_24_7.err"
    else
        echo "No error file found"
    fi
}

# Function to show performance summary
show_performance() {
    if [ -f "$LOG_DIR/paper_trading_24_7.out" ]; then
        echo "=== Performance Summary ==="
        grep -E "(HEARTBEAT|FINAL SUMMARY|Total Return|Total Trades)" "$LOG_DIR/paper_trading_24_7.out" | tail -n 20
    else
        echo "No log file found"
    fi
}

# Main script logic
case "$1" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        status_service
        ;;
    logs)
        show_logs
        ;;
    errors)
        show_errors
        ;;
    performance)
        show_performance
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|errors|performance}"
        echo ""
        echo "Commands:"
        echo "  start      - Start the 24/7 paper trading system"
        echo "  stop       - Stop the paper trading system"
        echo "  restart    - Restart the paper trading system"
        echo "  status     - Check if the system is running"
        echo "  logs       - Show recent logs"
        echo "  errors     - Show recent errors"
        echo "  performance - Show performance summary"
        echo ""
        echo "Example:"
        echo "  $0 start    # Start the system"
        echo "  $0 status   # Check if running"
        echo "  $0 logs     # View recent activity"
        echo "  $0 stop     # Stop the system"
        exit 1
        ;;
esac
