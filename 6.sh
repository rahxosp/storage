#!/bin/bash
# ESRGAN Server Setup - Main Script
# Ubuntu 22.04 - Complete setup for ESRGAN image upscaling

set -e  # Exit on error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ESRGAN_DIR="/home/esrgan"
V13_DIR="/home/v13"
ESRGAN_ZIP_URL="https://raw.githubusercontent.com/rahxosp/storage/refs/heads/main/esgan.zip"
V13_ZIP_URL="https://raw.githubusercontent.com/rahxosp/storage/refs/heads/main/v13.zip"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# STEP 1: System Update & Dependencies
# =============================================================================
setup_system() {
    log_info "Step 1: Updating system and installing dependencies..."
    
    apt update
    apt upgrade -y
    
    log_info "Installing essential packages..."
    apt install -y wget curl unzip build-essential git
    
    log_info "Checking for NVIDIA drivers..."
    if command -v nvidia-smi &> /dev/null; then
        log_info "NVIDIA driver detected:"
        nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
    else
        log_warn "NVIDIA driver not found. Installing..."
        apt install -y ubuntu-drivers-common
        ubuntu-drivers autoinstall
        log_warn "NVIDIA driver installed. You may need to REBOOT and re-run this script."
        read -p "Press Enter to continue or Ctrl+C to exit and reboot..."
    fi
    
    log_info "Installing Python and pip..."
    apt install -y python3 python3-pip python3-venv
    python3 --version
    pip3 --version
    
    log_info "System setup complete!"
}

# =============================================================================
# STEP 2: Vulkan Installation & Configuration
# =============================================================================
setup_vulkan() {
    log_info "Step 2: Installing and configuring Vulkan..."
    
    # Install Vulkan packages
    log_info "Installing Vulkan packages..."
    apt install -y vulkan-tools libvulkan1 mesa-vulkan-drivers vulkan-validationlayers
    
    # Install X11 libraries (required dependencies)
    log_info "Installing X11 libraries..."
    apt install -y xvfb x11-utils libx11-6 libxext6 libxrandr2 libxrender1 libxxf86vm1 libxfixes3
    
    # Configure NVIDIA Vulkan ICD
    NVIDIA_ICD_PATH="/etc/vulkan/icd.d/nvidia_icd.json"
    CUSTOM_VULKAN_DIR="/home/vulkan_config"
    CUSTOM_ICD_PATH="$CUSTOM_VULKAN_DIR/nvidia_icd.json"
    API_VERSION="1.3.289"
    
    log_info "Configuring NVIDIA Vulkan ICD for headless operation..."
    
    # Try to write to system directory first
    mkdir -p /etc/vulkan/icd.d/ 2>/dev/null || true
    
    # Attempt to create system-wide ICD config
    if cat > $NVIDIA_ICD_PATH <<'EOF' 2>/dev/null
{
    "file_format_version" : "1.0.0",
    "ICD": {
        "library_path": "libEGL_nvidia.so.0",
        "api_version" : "1.3.289"
    }
}
EOF
    then
        log_info "NVIDIA ICD configured at $NVIDIA_ICD_PATH (EGL mode)"
    else
        log_warn "Cannot write to $NVIDIA_ICD_PATH (read-only file system)"
        log_info "Creating custom Vulkan configuration at $CUSTOM_VULKAN_DIR..."
        
        # Create writable directory
        mkdir -p "$CUSTOM_VULKAN_DIR"
        
        # Check if original ICD file exists to copy from
        if [ -f "$NVIDIA_ICD_PATH" ]; then
            log_info "Copying existing ICD config as base..."
            cp "$NVIDIA_ICD_PATH" "$CUSTOM_ICD_PATH"
        fi
        
        # Create/overwrite with our custom config (EGL for headless)
        cat > "$CUSTOM_ICD_PATH" <<'EOF'
{
    "file_format_version" : "1.0.0",
    "ICD": {
        "library_path": "libEGL_nvidia.so.0",
        "api_version" : "1.3.289"
    }
}
EOF
        
        # Set environment variable to use custom config
        export VK_ICD_FILENAMES="$CUSTOM_ICD_PATH"
        
        # Make it permanent in bashrc and profile
        if ! grep -q "VK_ICD_FILENAMES" /root/.bashrc 2>/dev/null; then
            echo "export VK_ICD_FILENAMES=$CUSTOM_ICD_PATH" >> /root/.bashrc
        fi
        
        if ! grep -q "VK_ICD_FILENAMES" /etc/profile 2>/dev/null; then
            echo "export VK_ICD_FILENAMES=$CUSTOM_ICD_PATH" >> /etc/profile
        fi
        
        # Also add to /etc/environment for system-wide availability
        if ! grep -q "VK_ICD_FILENAMES" /etc/environment 2>/dev/null; then
            echo "VK_ICD_FILENAMES=$CUSTOM_ICD_PATH" >> /etc/environment
        fi
        
        log_info "Custom NVIDIA ICD configured at $CUSTOM_ICD_PATH"
        log_info "Environment variable VK_ICD_FILENAMES set to use custom config"
        log_info "Config added to /root/.bashrc, /etc/profile, and /etc/environment"
    fi
    
    # Run ldconfig
    ldconfig
    
    log_info "Vulkan installation complete!"
}


# =============================================================================
# STEP 3: Verify Vulkan Configuration
# =============================================================================
verify_vulkan() {
    log_info "Step 3: Verifying Vulkan configuration..."
    
    if command -v vulkaninfo &> /dev/null; then
        log_info "Running vulkaninfo to check Vulkan setup..."
        
        if VULKAN_OUTPUT=$(vulkaninfo --summary 2>&1); then
            # Check if NVIDIA GPU is detected
            if echo "$VULKAN_OUTPUT" | grep -qi "NVIDIA\|GeForce\|RTX\|GTX"; then
                GPU_NAME=$(echo "$VULKAN_OUTPUT" | grep "deviceName" | head -1 | awk '{for(i=3;i<=NF;i++) printf "%s ", $i; print ""}')
                DRIVER_INFO=$(echo "$VULKAN_OUTPUT" | grep "driverInfo" | head -1 | awk '{print $3}')
                
                log_info "Vulkan configured successfully!"
                echo "  GPU Detected: $GPU_NAME"
                echo "  Driver Info: $DRIVER_INFO"
                return 0
            else
                log_warn "Vulkan installed but NVIDIA GPU not clearly detected."
                log_info "Detected devices:"
                echo "$VULKAN_OUTPUT" | grep "deviceName" | head -3
                log_info "Continuing anyway - ESRGAN test will confirm if working..."
                return 0
            fi
        else
            log_error "Vulkan verification failed"
            echo "$VULKAN_OUTPUT"
            log_info "Troubleshooting:"
            echo "  1. Check NVIDIA driver: nvidia-smi"
            echo "  2. Check ICD config: cat /etc/vulkan/icd.d/nvidia_icd.json"
            echo "  3. Check logs: VK_LOADER_DEBUG=all vulkaninfo --summary"
            return 1
        fi
    else
        log_error "vulkaninfo command not found"
        return 1
    fi
}

# =============================================================================
# STEP 4: Download and Install ESRGAN
# =============================================================================
install_esrgan() {
    log_info "Step 4: Downloading and installing ESRGAN..."
    
    # Create directory
    mkdir -p "$ESRGAN_DIR"
    
    # Download ESRGAN
    cd /tmp
    log_info "Downloading ESRGAN from $ESRGAN_ZIP_URL..."
    wget -O esrgan.zip "$ESRGAN_ZIP_URL" || curl -o esrgan.zip "$ESRGAN_ZIP_URL"
    
    if [ ! -f esrgan.zip ]; then
        log_error "Failed to download ESRGAN"
        return 1
    fi
    
    # Extract to target directory
    log_info "Extracting ESRGAN to $ESRGAN_DIR..."
    unzip -o esrgan.zip -d "$ESRGAN_DIR"
    
    # Navigate to ESRGAN directory
    cd "$ESRGAN_DIR"
    
    # Find the binary (might be in subdirectory)
    BINARY_PATH=$(find . -name "realesrgan-ncnn-vulkan" -type f | head -n 1)
    
    if [ -z "$BINARY_PATH" ]; then
        log_error "realesrgan-ncnn-vulkan binary not found in extracted files"
        ls -la "$ESRGAN_DIR"
        return 1
    fi
    
    log_info "Found binary at: $BINARY_PATH"
    
    # Copy and rename binary
    cp "$BINARY_PATH" "$ESRGAN_DIR/esrgan"
    chmod 777 "$ESRGAN_DIR/esrgan"
    
    # Add to PATH
    if ! grep -q "export PATH=\$PATH:$ESRGAN_DIR" ~/.bashrc; then
        echo "export PATH=\$PATH:$ESRGAN_DIR" >> ~/.bashrc
    fi
    export PATH=$PATH:$ESRGAN_DIR
    
    log_info "ESRGAN installed successfully!"
    log_info "Binary location: $ESRGAN_DIR/esrgan"
}

# =============================================================================
# STEP 5: Configure ESRGAN
# =============================================================================
configure_esrgan() {
    log_info "Step 5: Configuring ESRGAN..."
    
    cd "$ESRGAN_DIR"
    
    # Create symbolic link in /usr/local/bin for system-wide access
    ln -sf "$ESRGAN_DIR/esrgan" /usr/local/bin/esrgan
    
    # Verify it's accessible
    if command -v esrgan &> /dev/null; then
        log_info "ESRGAN is now accessible system-wide!"
        esrgan -h || esrgan --help || log_warn "Could not display help (binary might need models)"
    else
        log_warn "ESRGAN not in PATH yet. Run: source ~/.bashrc"
    fi
    
    log_info "ESRGAN configuration complete!"
}

# =============================================================================
# STEP 6: Test ESRGAN
# =============================================================================
test_esrgan() {
    log_info "Step 6: Testing ESRGAN with input.jpg..."
    
    cd "$ESRGAN_DIR"
    
    # Find input.jpg
    INPUT_IMAGE="$ESRGAN_DIR/input.jpg"
    
    if [ ! -f "$INPUT_IMAGE" ]; then
        # Try to find it in subdirectories
        INPUT_IMAGE=$(find "$ESRGAN_DIR" -name "input.jpg" -type f | head -n 1)
    fi
    
    if [ -z "$INPUT_IMAGE" ] || [ ! -f "$INPUT_IMAGE" ]; then
        log_warn "input.jpg not found in ESRGAN directory. Skipping test..."
        log_info "Available files in $ESRGAN_DIR:"
        ls -la "$ESRGAN_DIR"
        return 0
    fi
    
    log_info "Found test image: $INPUT_IMAGE"
    log_info "Running ESRGAN upscaling test (scale 2x)..."
    
    # Run ESRGAN with scale 2
    if "$ESRGAN_DIR/esrgan" -i "$INPUT_IMAGE" -o "$ESRGAN_DIR/output.jpg" -s 2 2>&1; then
        if [ -f "$ESRGAN_DIR/output.jpg" ]; then
            log_info "Test successful! Output saved to: $ESRGAN_DIR/output.jpg"
            ls -lh "$ESRGAN_DIR/output.jpg"
            
            # Show size comparison
            INPUT_SIZE=$(stat -f%z "$INPUT_IMAGE" 2>/dev/null || stat -c%s "$INPUT_IMAGE" 2>/dev/null)
            OUTPUT_SIZE=$(stat -f%z "$ESRGAN_DIR/output.jpg" 2>/dev/null || stat -c%s "$ESRGAN_DIR/output.jpg" 2>/dev/null)
            echo "  Input size:  $(numfmt --to=iec $INPUT_SIZE 2>/dev/null || echo $INPUT_SIZE bytes)"
            echo "  Output size: $(numfmt --to=iec $OUTPUT_SIZE 2>/dev/null || echo $OUTPUT_SIZE bytes)"
        else
            log_warn "ESRGAN ran but output file not found at expected location"
        fi
    else
        log_warn "ESRGAN test completed with warnings. Check manually with: esrgan -i $INPUT_IMAGE -o $ESRGAN_DIR/output.jpg -s 2"
    fi
}

# =============================================================================
# STEP 7: Download and Extract v13 Python Program
# =============================================================================
install_v13() {
    log_info "Step 7: Downloading and installing v13 Python program..."
    
    # Create directory
    mkdir -p "$V13_DIR"
    
    # Download v13
    cd /tmp
    log_info "Downloading v13 from $V13_ZIP_URL..."
    wget -O v13.zip "$V13_ZIP_URL" || curl -o v13.zip "$V13_ZIP_URL"
    
    if [ ! -f v13.zip ]; then
        log_error "Failed to download v13"
        return 1
    fi
    
    # Extract
    log_info "Extracting v13 to $V13_DIR..."
    unzip -o v13.zip -d "$V13_DIR"
    
    cd "$V13_DIR"
    
    # Look for requirements.txt
    REQUIREMENTS=$(find . -name "requirements.txt" -type f | head -n 1)
    
    if [ -n "$REQUIREMENTS" ]; then
        log_info "Found requirements.txt at: $REQUIREMENTS"
        log_info "Installing Python dependencies..."
        
        # Install requirements
        pip3 install -r "$REQUIREMENTS"
        
        log_info "Python dependencies installed!"
    else
        log_warn "requirements.txt not found. You may need to install dependencies manually."
        log_info "Contents of $V13_DIR:"
        ls -la
    fi
    
    log_info "v13 installation complete!"
    log_info "Location: $V13_DIR"
}

# =============================================================================
# STEP 8: Install Process Manager (PM2 for Docker/Supervisor for VM)
# =============================================================================
setup_process_manager() {
    log_info "Step 8: Installing process manager..."
    
    # Check if running in Docker container
    if [ -f "/.dockerenv" ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
        log_info "Docker environment detected - installing PM2..."
        
        # Install Node.js and npm (required for PM2)
        log_info "Installing Node.js and npm..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
        apt install -y nodejs
        
        # Install PM2 globally
        log_info "Installing PM2..."
        npm install -g pm2
        
        # Setup PM2 to start on system boot (via rc.local or custom init)
        pm2 startup systemv -u root --hp /root 2>/dev/null || log_warn "PM2 startup registration skipped (no systemd)"
        
        log_info "PM2 installed successfully!"
        echo "PM2" > /tmp/process_manager_type
    else
        log_info "VM environment detected - installing Supervisor..."
        
        # Install supervisor
        apt install -y supervisor
        
        # Enable and start supervisor service
        systemctl enable supervisor 2>/dev/null || true
        systemctl start supervisor 2>/dev/null || service supervisor start || true
        
        log_info "Supervisor installed and started!"
        echo "SUPERVISOR" > /tmp/process_manager_type
    fi
}

# =============================================================================
# STEP 9: Configure Process Manager for v13 Ultra Processor
# =============================================================================
configure_v13_process_manager() {
    log_info "Step 9: Configuring process manager for v13 ultra processor..."
    
    cd "$V13_DIR"
    
    # Find ultra_aggressive_worker.py
    MAIN_SCRIPT=""
    
    if [ -f "$V13_DIR/ultra_aggressive_worker.py" ]; then
        MAIN_SCRIPT="ultra_aggressive_worker.py"
    elif [ -f "$V13_DIR/v13/ultra_aggressive_worker.py" ]; then
        MAIN_SCRIPT="v13/ultra_aggressive_worker.py"
    fi
    
    if [ -z "$MAIN_SCRIPT" ]; then
        log_warn "Could not find ultra_aggressive_worker.py automatically."
        log_info "Available Python files:"
        find "$V13_DIR" -name "*.py" -type f | head -10
        log_warn "Please configure process manager manually"
        return 0
    fi
    
    log_info "Found main script: $MAIN_SCRIPT"
    
    # Get the actual directory where the script is located
    SCRIPT_DIR=$(dirname "$V13_DIR/$MAIN_SCRIPT")
    SCRIPT_NAME=$(basename "$MAIN_SCRIPT")
    
    # Determine which process manager to use
    PM_TYPE=$(cat /tmp/process_manager_type 2>/dev/null || echo "SUPERVISOR")
    
    if [ "$PM_TYPE" = "PM2" ]; then
        configure_pm2_processor "$SCRIPT_DIR" "$SCRIPT_NAME"
    else
        configure_supervisor_processor "$SCRIPT_DIR" "$SCRIPT_NAME"
    fi
}

# Configure PM2 for v13 processor
configure_pm2_processor() {
    local SCRIPT_DIR="$1"
    local SCRIPT_NAME="$2"
    
    log_info "Configuring PM2 for v13 processor..."
    
    # Create PM2 ecosystem config file
    cat > "$V13_DIR/ecosystem.config.js" <<EOF
module.exports = {
  apps: [{
    name: 'v13-ultra-processor',
    script: 'python3',
    args: '$SCRIPT_NAME',
    cwd: '$SCRIPT_DIR',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '2G',
    env: {
      PATH: '/usr/local/bin:/usr/bin:/bin:$ESRGAN_DIR',
      VK_ICD_FILENAMES: '/home/vulkan_config/nvidia_icd.json'
    },
    error_file: '/var/log/pm2/v13-processor-error.log',
    out_file: '/var/log/pm2/v13-processor.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    restart_delay: 4000,
    max_restarts: 10,
    kill_timeout: 5000
  }]
};
EOF
    
    mkdir -p /var/log/pm2
    
    log_info "PM2 configuration created!"
    log_info "Config file: $V13_DIR/ecosystem.config.js"
    log_info "Script location: $SCRIPT_DIR/$SCRIPT_NAME"
}

# Configure Supervisor for v13 processor
configure_supervisor_processor() {
    local SCRIPT_DIR="$1"
    local SCRIPT_NAME="$2"
    
    log_info "Configuring Supervisor for v13 processor..."
    
    SUPERVISOR_CONF="/etc/supervisor/conf.d/v13-processor.conf"
    
    cat > "$SUPERVISOR_CONF" <<EOF
[program:v13-ultra-processor]
command=python3 $SCRIPT_NAME
directory=$SCRIPT_DIR
autostart=false
autorestart=true
startretries=10
user=root
redirect_stderr=true
stdout_logfile=/var/log/supervisor/v13-processor.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
stderr_logfile=/var/log/supervisor/v13-processor-error.log
stopwaitsecs=30
stopsignal=TERM
environment=PATH="/usr/local/bin:/usr/bin:/bin:$ESRGAN_DIR"

; Restart policy - Always restart if it exits
stopasgroup=true
killasgroup=true
EOF
    
    # If custom Vulkan config exists, add it to environment
    if [ -f "/home/vulkan_config/nvidia_icd.json" ]; then
        sed -i "s|environment=PATH=|environment=VK_ICD_FILENAMES=/home/vulkan_config/nvidia_icd.json,PATH=|" "$SUPERVISOR_CONF"
    fi
    
    mkdir -p /var/log/supervisor
    
    # Reload supervisor configuration
    supervisorctl reread 2>/dev/null || true
    supervisorctl update 2>/dev/null || true
    
    log_info "Supervisor configuration created!"
    log_info "Configuration file: $SUPERVISOR_CONF"
    log_info "Script location: $SCRIPT_DIR/$SCRIPT_NAME"
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================
main() {
    echo "=========================================="
    echo "  ESRGAN Server Setup - Main Script"
    echo "  Ubuntu 22.04"
    echo "=========================================="
    echo ""
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run this script as root (use sudo or run as root user)."
        exit 1
    fi
    
    log_info "Starting setup process..."
    echo ""
    
    # Execute all steps
    setup_system
    echo ""
    
    setup_vulkan
    echo ""
    
    verify_vulkan
    echo ""
    
    install_esrgan
    echo ""
    
    configure_esrgan
    echo ""
    
    test_esrgan
    echo ""
    
    install_v13
    echo ""
    
    setup_process_manager
    echo ""
    
    configure_v13_process_manager
    echo ""
    
    echo "=========================================="
    echo "  Setup Complete!"
    echo "=========================================="
    echo ""
    # Determine which process manager was installed
    PM_TYPE=$(cat /tmp/process_manager_type 2>/dev/null || echo "SUPERVISOR")
    
    log_info "Summary:"
    echo "  - ESRGAN installed at: $ESRGAN_DIR"
    echo "  - v13 program installed at: $V13_DIR"
    echo "  - ESRGAN command: esrgan (accessible system-wide)"
    echo "  - Process manager: $PM_TYPE"
    echo ""
    
    if [ "$PM_TYPE" = "PM2" ]; then
        log_info "PM2 Management Commands:"
        echo "  - Start:   pm2 start $V13_DIR/ecosystem.config.js"
        echo "  - Stop:    pm2 start /home/v13/ecosystem.config.js"
        echo "  - Stop:    pm2 stop v13-ultra-processor"
        echo "  - Restart: pm2 restart v13-ultra-processor"
        echo "  - Delete:  pm2 delete v13-ultra-processor"
        echo "  - Status:  pm2 status"
        echo "  - Logs:    pm2 logs v13-ultra-processor"
        echo "  - Monitor: pm2 monit"
        echo "  - Save:    pm2 save  (save current process list)"
    else
        log_info "Supervisor Management Commands:"
        echo "  - Start:   supervisorctl start v13-ultra-processor"
        echo "  - Stop:    supervisorctl stop v13-ultra-processor"
        echo "  - Restart: supervisorctl restart v13-ultra-processor"
        echo "  - Status:  supervisorctl status v13-ultra-processor"
        echo "  - Logs:    tail -f /var/log/supervisor/v13-processor.log"
    fi
    
    echo ""
    log_info "Next steps:"
    echo "  1. Run: source ~/.bashrc"
    echo "  2. Verify ESRGAN: esrgan -h"
    echo "  3. Configure v13 with your Laravel webapp settings"
    if [ "$PM_TYPE" = "PM2" ]; then
        echo "  4. Start processor: pm2 start $V13_DIR/ecosystem.config.js"
    else
        echo "  4. Start processor: supervisorctl start v13-ultra-processor"
    fi
    echo ""
    log_warn "NOTE: v13 processor is NOT auto-started. Configure your webapp first!"
    log_warn "If NVIDIA driver was installed, REBOOT is recommended!"
    echo ""
}

# Run main function
main
