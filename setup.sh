#!/bin/bash

################################################################################
# Laravel ESRGAN Server Setup Script
# Version: 2.0.0
# OS: Ubuntu 22.04 LTS
# Purpose: Enterprise-grade automated server configuration for ESRGAN
################################################################################

set -o pipefail  # Capture pipe failures
set -o nounset   # Exit on undefined variables

################################################################################
# CONFIGURATION
################################################################################

readonly SCRIPT_VERSION="2.0.0"
readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_DIR="/var/log/esrgan-setup"
readonly LOG_FILE="${LOG_DIR}/setup-$(date +%Y%m%d-%H%M%S).log"
readonly STATE_FILE="/tmp/esrgan-setup.state"
readonly BACKUP_DIR="/var/backups/esrgan-setup"

# Installation paths
readonly ESRGAN_DIR="/home/esrgan"
readonly V13_DIR="/home/v13"

# Download URLs
readonly ESRGAN_URL="https://raw.githubusercontent.com/rahxosp/storage/refs/heads/main/esgan.zip"
readonly V13_URL="https://raw.githubusercontent.com/rahxosp/storage/refs/heads/main/v13.zip"

# NVIDIA driver version
readonly NVIDIA_DRIVER_VERSION="525"

# Timeout settings (seconds)
readonly DOWNLOAD_TIMEOUT=300
readonly COMMAND_TIMEOUT=600

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly MAGENTA='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# Exit codes
readonly E_SUCCESS=0
readonly E_GENERAL=1
readonly E_DEPENDENCY=2
readonly E_DOWNLOAD=3
readonly E_PERMISSION=4
readonly E_CONFIG=5
readonly E_VALIDATION=6

################################################################################
# LOGGING FUNCTIONS
################################################################################

setup_logging() {
    # Create log directory
    sudo mkdir -p "${LOG_DIR}"
    sudo chmod 755 "${LOG_DIR}"
    
    # Create backup directory
    sudo mkdir -p "${BACKUP_DIR}"
    sudo chmod 755 "${BACKUP_DIR}"
    
    # Initialize log file
    {
        echo "=================================="
        echo "ESRGAN Setup Script v${SCRIPT_VERSION}"
        echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Hostname: $(hostname)"
        echo "User: $(whoami)"
        echo "=================================="
    } | sudo tee "${LOG_FILE}" > /dev/null
}

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    
    # Log to file
    echo "[${timestamp}] [${level}] ${message}" | sudo tee -a "${LOG_FILE}" > /dev/null
    
    # Log to console with colors
    case "${level}" in
        INFO)
            echo -e "${GREEN}[${timestamp}] [INFO] ${message}${NC}"
            ;;
        WARN)
            echo -e "${YELLOW}[${timestamp}] [WARN] ${message}${NC}"
            ;;
        ERROR)
            echo -e "${RED}[${timestamp}] [ERROR] ${message}${NC}"
            ;;
        DEBUG)
            echo -e "${CYAN}[${timestamp}] [DEBUG] ${message}${NC}"
            ;;
        SUCCESS)
            echo -e "${MAGENTA}[${timestamp}] [SUCCESS] ${message}${NC}"
            ;;
        *)
            echo "[${timestamp}] ${message}"
            ;;
    esac
}

################################################################################
# ERROR HANDLING & CLEANUP
################################################################################

cleanup_on_exit() {
    local exit_code=$?
    
    if [ ${exit_code} -ne 0 ]; then
        log ERROR "Script failed with exit code: ${exit_code}"
        log INFO "Check log file: ${LOG_FILE}"
    else
        log SUCCESS "Script completed successfully"
    fi
    
    # Clean up temporary files
    rm -f /tmp/esrgan_*.log 2>/dev/null
    
    exit ${exit_code}
}

cleanup_on_error() {
    local exit_code=$?
    local line_no=$1
    
    log ERROR "Error occurred at line ${line_no} (exit code: ${exit_code})"
    log INFO "Initiating cleanup..."
    
    # Save state for potential recovery
    save_state "FAILED" "Line ${line_no}"
    
    exit ${exit_code}
}

trap cleanup_on_exit EXIT
trap 'cleanup_on_error ${LINENO}' ERR

################################################################################
# STATE MANAGEMENT
################################################################################

save_state() {
    local state="$1"
    local details="${2:-}"
    
    cat > "${STATE_FILE}" <<EOF
TIMESTAMP=$(date +%s)
STATE=${state}
DETAILS=${details}
VERSION=${SCRIPT_VERSION}
EOF
    
    log DEBUG "State saved: ${state}"
}

load_state() {
    if [ -f "${STATE_FILE}" ]; then
        source "${STATE_FILE}"
        log INFO "Previous state loaded: ${STATE}"
        return 0
    fi
    return 1
}

################################################################################
# VALIDATION FUNCTIONS
################################################################################

check_root_or_sudo() {
    if [ "${EUID}" -eq 0 ]; then
        log WARN "Running as root. This is not recommended for production."
    fi
    
    if ! sudo -n true 2>/dev/null; then
        log ERROR "This script requires sudo privileges"
        exit ${E_PERMISSION}
    fi
    
    log INFO "Sudo access confirmed"
}

check_os_version() {
    log INFO "Checking OS version..."
    
    if [ -f /etc/os-release ]; then
        source /etc/os-release
        
        if [ "${ID}" != "ubuntu" ]; then
            log ERROR "This script is designed for Ubuntu. Detected: ${ID}"
            exit ${E_GENERAL}
        fi
        
        if [ "${VERSION_ID}" != "22.04" ]; then
            log WARN "This script is optimized for Ubuntu 22.04. Detected: ${VERSION_ID}"
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit ${E_GENERAL}
            fi
        fi
        
        log SUCCESS "OS check passed: ${PRETTY_NAME}"
    else
        log ERROR "Cannot determine OS version"
        exit ${E_GENERAL}
    fi
}

check_disk_space() {
    log INFO "Checking disk space..."
    
    local required_space=10485760  # 10 GB in KB
    local available_space=$(df /home | tail -1 | awk '{print $4}')
    
    if [ "${available_space}" -lt "${required_space}" ]; then
        log ERROR "Insufficient disk space. Required: 10GB, Available: $((available_space / 1024 / 1024))GB"
        exit ${E_GENERAL}
    fi
    
    log SUCCESS "Disk space check passed: $((available_space / 1024 / 1024))GB available"
}

check_internet_connection() {
    log INFO "Checking internet connectivity..."
    
    if ! ping -c 1 -W 5 8.8.8.8 &> /dev/null; then
        log ERROR "No internet connection detected"
        exit ${E_GENERAL}
    fi
    
    log SUCCESS "Internet connectivity confirmed"
}

pre_flight_checks() {
    log INFO "Running pre-flight checks..."
    
    check_root_or_sudo
    check_os_version
    check_disk_space
    check_internet_connection
    
    log SUCCESS "All pre-flight checks passed"
}

################################################################################
# BACKUP FUNCTIONS
################################################################################

backup_file() {
    local file="$1"
    
    if [ -f "${file}" ]; then
        local backup_name="$(basename ${file}).$(date +%Y%m%d-%H%M%S).bak"
        sudo cp "${file}" "${BACKUP_DIR}/${backup_name}"
        log INFO "Backed up: ${file} -> ${backup_name}"
    fi
}

backup_directory() {
    local dir="$1"
    
    if [ -d "${dir}" ]; then
        local backup_name="$(basename ${dir}).$(date +%Y%m%d-%H%M%S).tar.gz"
        sudo tar -czf "${BACKUP_DIR}/${backup_name}" -C "$(dirname ${dir})" "$(basename ${dir})" 2>/dev/null
        log INFO "Backed up directory: ${dir} -> ${backup_name}"
    fi
}

################################################################################
# SYSTEM UPDATE & DEPENDENCIES
################################################################################

update_system() {
    log INFO "Starting system update..."
    save_state "UPDATE_SYSTEM" "In progress"
    
    # Update package cache
    log INFO "Updating package cache..."
    if ! sudo apt update 2>&1 | sudo tee -a "${LOG_FILE}"; then
        log ERROR "Failed to update package cache"
        return ${E_DEPENDENCY}
    fi
    
    # Upgrade packages
    log INFO "Upgrading packages (this may take a while)..."
    if ! sudo DEBIAN_FRONTEND=noninteractive apt upgrade -y 2>&1 | sudo tee -a "${LOG_FILE}"; then
        log ERROR "Failed to upgrade packages"
        return ${E_DEPENDENCY}
    fi
    
    # Install essential packages
    log INFO "Installing essential packages..."
    local packages=(
        curl
        wget
        unzip
        build-essential
        software-properties-common
        ca-certificates
        gnupg
        lsb-release
    )
    
    if ! sudo DEBIAN_FRONTEND=noninteractive apt install -y "${packages[@]}" 2>&1 | sudo tee -a "${LOG_FILE}"; then
        log ERROR "Failed to install essential packages"
        return ${E_DEPENDENCY}
    fi
    
    log SUCCESS "System update completed"
    save_state "UPDATE_SYSTEM" "Completed"
}

install_nvidia_drivers() {
    log INFO "Checking NVIDIA drivers..."
    save_state "NVIDIA_DRIVERS" "In progress"
    
    if command -v nvidia-smi &> /dev/null; then
        log INFO "NVIDIA drivers already installed:"
        nvidia-smi --query-gpu=name,driver_version --format=csv,noheader | while read line; do
            log INFO "  GPU: ${line}"
        done
        save_state "NVIDIA_DRIVERS" "Already installed"
        return 0
    fi
    
    log WARN "NVIDIA drivers not found. Installing..."
    
    # Check if NVIDIA GPU exists
    if ! lspci | grep -i nvidia &> /dev/null; then
        log WARN "No NVIDIA GPU detected. Skipping driver installation."
        save_state "NVIDIA_DRIVERS" "No GPU detected"
        return 0
    fi
    
    # Install drivers
    if ! sudo DEBIAN_FRONTEND=noninteractive apt install -y \
        nvidia-driver-${NVIDIA_DRIVER_VERSION} \
        nvidia-utils-${NVIDIA_DRIVER_VERSION} 2>&1 | sudo tee -a "${LOG_FILE}"; then
        log ERROR "Failed to install NVIDIA drivers"
        return ${E_DEPENDENCY}
    fi
    
    log SUCCESS "NVIDIA drivers installed successfully"
    log WARN "System reboot required for drivers to take effect"
    save_state "NVIDIA_DRIVERS" "Installed - Reboot required"
}

install_python() {
    log INFO "Installing Python and pip..."
    save_state "PYTHON" "In progress"
    
    if ! sudo DEBIAN_FRONTEND=noninteractive apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev 2>&1 | sudo tee -a "${LOG_FILE}"; then
        log ERROR "Failed to install Python"
        return ${E_DEPENDENCY}
    fi
    
    # Verify installations
    local python_version=$(python3 --version 2>&1)
    local pip_version=$(pip3 --version 2>&1)
    
    log SUCCESS "Python installed: ${python_version}"
    log SUCCESS "Pip installed: ${pip_version}"
    save_state "PYTHON" "Completed"
}

################################################################################
# VULKAN INSTALLATION & CONFIGURATION
################################################################################

install_vulkan() {
    log INFO "Installing Vulkan..."
    save_state "VULKAN" "In progress"
    
    # Install Vulkan packages
    local vulkan_packages=(
        vulkan-tools
        libvulkan1
        libvulkan-dev
        mesa-vulkan-drivers
        vulkan-validationlayers
    )
    
    if ! sudo DEBIAN_FRONTEND=noninteractive apt install -y "${vulkan_packages[@]}" 2>&1 | sudo tee -a "${LOG_FILE}"; then
        log ERROR "Failed to install Vulkan packages"
        return ${E_DEPENDENCY}
    fi
    
    # Install X11 libraries (required for headless Vulkan)
    log INFO "Installing X11 libraries for headless operation..."
    local x11_packages=(
        xvfb
        x11-utils
        libx11-6
        libxext6
        libxrandr2
        libxrender1
        libxxf86vm1
        libxfixes3
    )
    
    if ! sudo DEBIAN_FRONTEND=noninteractive apt install -y "${x11_packages[@]}" 2>&1 | sudo tee -a "${LOG_FILE}"; then
        log WARN "Failed to install some X11 packages, but continuing..."
    fi
    
    log SUCCESS "Vulkan packages installed"
    save_state "VULKAN" "Packages installed"
}

configure_vulkan() {
    log INFO "Configuring Vulkan..."
    save_state "VULKAN_CONFIG" "In progress"
    
    local nvidia_icd="/etc/vulkan/icd.d/nvidia_icd.json"
    
    # Create ICD directory if it doesn't exist
    sudo mkdir -p /etc/vulkan/icd.d/
    
    # Always create/update NVIDIA ICD configuration for headless operation
    log INFO "Creating NVIDIA Vulkan ICD configuration..."
    sudo tee "${nvidia_icd}" > /dev/null <<'EOF'
{
    "file_format_version": "1.0.0",
    "ICD": {
        "library_path": "libEGL_nvidia.so.0",
        "api_version": "1.3.289"
    }
}
EOF
    
    log SUCCESS "NVIDIA ICD configured for headless operation (EGL)"
    
    # Check if nvidia_icd.json exists and is readable
    if [ ! -f "${nvidia_icd}" ]; then
        log ERROR "nvidia_icd.json creation failed"
        log WARN "Creating user-level custom Vulkan configuration..."
        
        # Create custom Vulkan directory
        mkdir -p ~/.local/share/vulkan/icd.d/
        
        # Create custom nvidia_icd.json
        cat > ~/.local/share/vulkan/icd.d/nvidia_icd.json <<'EOF'
{
    "file_format_version": "1.0.0",
    "ICD": {
        "library_path": "libEGL_nvidia.so.0",
        "api_version": "1.3.289"
    }
}
EOF
        
        # Set environment variable
        export VK_ICD_FILENAMES=~/.local/share/vulkan/icd.d/nvidia_icd.json
        
        if ! grep -q "VK_ICD_FILENAMES" ~/.bashrc; then
            echo 'export VK_ICD_FILENAMES=~/.local/share/vulkan/icd.d/nvidia_icd.json' >> ~/.bashrc
        fi
        
        log SUCCESS "Custom Vulkan configuration created"
        save_state "VULKAN_CONFIG" "Custom config created"
        return 0
    fi
    
    # Check if nvidia_icd.json is writable
    if [ ! -w "${nvidia_icd}" ]; then
        log WARN "nvidia_icd.json is read-only. Creating custom configuration..."
        
        mkdir -p ~/.local/share/vulkan/icd.d/
        sudo cp "${nvidia_icd}" ~/.local/share/vulkan/icd.d/nvidia_icd.json
        sudo chown $(whoami):$(whoami) ~/.local/share/vulkan/icd.d/nvidia_icd.json
        
        export VK_ICD_FILENAMES=~/.local/share/vulkan/icd.d/nvidia_icd.json
        
        if ! grep -q "VK_ICD_FILENAMES" ~/.bashrc; then
            echo 'export VK_ICD_FILENAMES=~/.local/share/vulkan/icd.d/nvidia_icd.json' >> ~/.bashrc
        fi
        
        log SUCCESS "Custom Vulkan configuration created from system file"
    else
        log SUCCESS "System Vulkan configuration is accessible"
    fi
    
    save_state "VULKAN_CONFIG" "Completed"
}

test_vulkan() {
    log INFO "Testing Vulkan configuration..."
    save_state "VULKAN_TEST" "In progress"
    
    if ! command -v vulkaninfo &> /dev/null; then
        log WARN "vulkaninfo command not found"
        save_state "VULKAN_TEST" "Command not found"
        return 0
    fi
    
    # Run vulkaninfo
    if vulkaninfo --summary > /tmp/vulkan_test.log 2>&1; then
        if grep -q "Vulkan Instance" /tmp/vulkan_test.log; then
            log SUCCESS "Vulkan is properly configured"
            
            # Log GPU information
            if grep -q "GPU" /tmp/vulkan_test.log; then
                log INFO "Vulkan GPU information:"
                grep "GPU" /tmp/vulkan_test.log | head -5 | while read line; do
                    log INFO "  ${line}"
                done
            fi
            
            save_state "VULKAN_TEST" "Passed"
            return 0
        fi
    fi
    
    log WARN "Vulkan test did not pass completely"
    log INFO "This may be normal if NVIDIA drivers need a reboot"
    log INFO "Check ${LOG_FILE} for details"
    save_state "VULKAN_TEST" "Incomplete - may need reboot"
}

################################################################################
# ESRGAN INSTALLATION
################################################################################

download_with_retry() {
    local url="$1"
    local output="$2"
    local max_attempts=3
    local attempt=1
    
    while [ ${attempt} -le ${max_attempts} ]; do
        log INFO "Download attempt ${attempt}/${max_attempts}: ${url}"
        
        if sudo wget --timeout=${DOWNLOAD_TIMEOUT} \
                     --tries=3 \
                     --progress=bar:force \
                     -O "${output}" \
                     "${url}" 2>&1 | sudo tee -a "${LOG_FILE}"; then
            log SUCCESS "Download successful"
            return 0
        fi
        
        log WARN "Download attempt ${attempt} failed"
        attempt=$((attempt + 1))
        
        if [ ${attempt} -le ${max_attempts} ]; then
            log INFO "Retrying in 5 seconds..."
            sleep 5
        fi
    done
    
    log ERROR "Failed to download after ${max_attempts} attempts"
    return ${E_DOWNLOAD}
}

verify_checksum() {
    local file="$1"
    local expected_checksum="${2:-}"
    
    if [ -z "${expected_checksum}" ]; then
        log DEBUG "No checksum provided, skipping verification"
        return 0
    fi
    
    local actual_checksum=$(sha256sum "${file}" | awk '{print $1}')
    
    if [ "${actual_checksum}" != "${expected_checksum}" ]; then
        log ERROR "Checksum mismatch for ${file}"
        log ERROR "Expected: ${expected_checksum}"
        log ERROR "Actual: ${actual_checksum}"
        return ${E_VALIDATION}
    fi
    
    log SUCCESS "Checksum verified for ${file}"
}

install_esrgan() {
    log INFO "Installing ESRGAN..."
    save_state "ESRGAN_INSTALL" "In progress"
    
    # Backup existing installation
    if [ -d "${ESRGAN_DIR}" ]; then
        log INFO "Backing up existing ESRGAN installation..."
        backup_directory "${ESRGAN_DIR}"
        sudo rm -rf "${ESRGAN_DIR}"
    fi
    
    # Create directory
    sudo mkdir -p "${ESRGAN_DIR}"
    sudo chmod 755 "${ESRGAN_DIR}"
    
    # Download ESRGAN
    log INFO "Downloading ESRGAN from ${ESRGAN_URL}..."
    if ! download_with_retry "${ESRGAN_URL}" "${ESRGAN_DIR}/esrgan.zip"; then
        return ${E_DOWNLOAD}
    fi
    
    # Verify download
    if [ ! -f "${ESRGAN_DIR}/esrgan.zip" ]; then
        log ERROR "Downloaded file not found"
        return ${E_DOWNLOAD}
    fi
    
    local file_size=$(stat -c%s "${ESRGAN_DIR}/esrgan.zip")
    log INFO "Downloaded file size: $((file_size / 1024 / 1024))MB"
    
    # Extract ESRGAN
    log INFO "Extracting ESRGAN..."
    if ! sudo unzip -q -o "${ESRGAN_DIR}/esrgan.zip" -d "${ESRGAN_DIR}" 2>&1 | sudo tee -a "${LOG_FILE}"; then
        log ERROR "Failed to extract ESRGAN"
        return ${E_GENERAL}
    fi
    
    # Clean up zip file
    sudo rm -f "${ESRGAN_DIR}/esrgan.zip"
    
    # Set permissions
    sudo chmod -R 755 "${ESRGAN_DIR}"
    
    # List extracted files
    log INFO "Extracted files:"
    sudo ls -lh "${ESRGAN_DIR}" | sudo tee -a "${LOG_FILE}"
    
    log SUCCESS "ESRGAN installed to ${ESRGAN_DIR}"
    save_state "ESRGAN_INSTALL" "Completed"
}

configure_esrgan() {
    log INFO "Configuring ESRGAN..."
    save_state "ESRGAN_CONFIG" "In progress"
    
    cd "${ESRGAN_DIR}"
    
    # Find the executable
    local executable=""
    if [ -f "realesrgan-ncnn-vulkan" ]; then
        executable="realesrgan-ncnn-vulkan"
    elif [ -f "RealESRGAN-ncnn-vulkan" ]; then
        executable="RealESRGAN-ncnn-vulkan"
    else
        log ERROR "ESRGAN executable not found"
        log INFO "Available files:"
        sudo ls -la "${ESRGAN_DIR}"
        return ${E_CONFIG}
    fi
    
    log INFO "Found executable: ${executable}"
    
    # Make executable
    sudo chmod +x "${ESRGAN_DIR}/${executable}"
    
    # Create symlink
    sudo ln -sf "${ESRGAN_DIR}/${executable}" "${ESRGAN_DIR}/esrgan"
    sudo chmod +x "${ESRGAN_DIR}/esrgan"
    
    # Add to PATH
    if ! grep -q "export PATH=\$PATH:${ESRGAN_DIR}" ~/.bashrc; then
        echo "export PATH=\$PATH:${ESRGAN_DIR}" >> ~/.bashrc
        log INFO "Added ${ESRGAN_DIR} to PATH in ~/.bashrc"
    fi
    
    # Also add to system-wide PATH
    if [ ! -f "/etc/profile.d/esrgan.sh" ]; then
        echo "export PATH=\$PATH:${ESRGAN_DIR}" | sudo tee /etc/profile.d/esrgan.sh > /dev/null
        sudo chmod +x /etc/profile.d/esrgan.sh
        log INFO "Added ${ESRGAN_DIR} to system-wide PATH"
    fi
    
    # Update current session PATH
    export PATH=$PATH:${ESRGAN_DIR}
    
    log SUCCESS "ESRGAN configured for global access"
    save_state "ESRGAN_CONFIG" "Completed"
}

test_esrgan() {
    log INFO "Testing ESRGAN..."
    save_state "ESRGAN_TEST" "In progress"
    
    cd "${ESRGAN_DIR}"
    
    # Test help command
    log INFO "Running help command..."
    if ./esrgan -h > /tmp/esrgan_help.log 2>&1; then
        log SUCCESS "ESRGAN help command works"
        log INFO "Available options:"
        head -20 /tmp/esrgan_help.log | while read line; do
            log INFO "  ${line}"
        done
    else
        log WARN "ESRGAN help command failed, trying with original executable..."
        if [ -f "realesrgan-ncnn-vulkan" ]; then
            ./realesrgan-ncnn-vulkan -h > /tmp/esrgan_help.log 2>&1 || true
        fi
    fi
    
    # Test with input image
    if [ -f "input.jpg" ] || [ -f "input.png" ]; then
        local test_input=""
        [ -f "input.jpg" ] && test_input="input.jpg"
        [ -f "input.png" ] && test_input="input.png"
        
        log INFO "Testing ESRGAN with ${test_input}..."
        
        if timeout ${COMMAND_TIMEOUT} ./esrgan -i "${test_input}" -o output_test.jpg 2>&1 | tee -a "${LOG_FILE}"; then
            if [ -f "output_test.jpg" ]; then
                local input_size=$(stat -c%s "${test_input}")
                local output_size=$(stat -c%s "output_test.jpg")
                log SUCCESS "ESRGAN test completed successfully"
                log INFO "Input size: $((input_size / 1024))KB"
                log INFO "Output size: $((output_size / 1024))KB"
                save_state "ESRGAN_TEST" "Passed"
                return 0
            fi
        fi
        
        log WARN "ESRGAN test with image did not complete"
        log INFO "This may be due to missing Vulkan setup or GPU drivers"
    else
        log WARN "No test images found (input.jpg or input.png)"
    fi
    
    save_state "ESRGAN_TEST" "Incomplete"
}

################################################################################
# PYTHON PROGRAM INSTALLATION
################################################################################

install_python_program() {
    log INFO "Installing Python program (v13)..."
    save_state "V13_INSTALL" "In progress"
    
    # Backup existing installation
    if [ -d "${V13_DIR}" ]; then
        log INFO "Backing up existing v13 installation..."
        backup_directory "${V13_DIR}"
        sudo rm -rf "${V13_DIR}"
    fi
    
    # Create directory
    sudo mkdir -p "${V13_DIR}"
    sudo chmod 755 "${V13_DIR}"
    
    # Download v13
    log INFO "Downloading v13 from ${V13_URL}..."
    if ! download_with_retry "${V13_URL}" "${V13_DIR}/v13.zip"; then
        return ${E_DOWNLOAD}
    fi
    
    # Extract v13
    log INFO "Extracting v13..."
    if ! sudo unzip -q -o "${V13_DIR}/v13.zip" -d "${V13_DIR}" 2>&1 | sudo tee -a "${LOG_FILE}"; then
        log ERROR "Failed to extract v13"
        return ${E_GENERAL}
    fi
    
    # Clean up zip file
    sudo rm -f "${V13_DIR}/v13.zip"
    
    # Set permissions
    sudo chmod -R 755 "${V13_DIR}"
    
    # Make Python scripts executable
    sudo find "${V13_DIR}" -name "*.py" -exec chmod +x {} \;
    
    log SUCCESS "v13 installed to ${V13_DIR}"
    save_state "V13_INSTALL" "Completed"
}

install_python_requirements() {
    log INFO "Installing Python requirements..."
    save_state "V13_REQUIREMENTS" "In progress"
    
    cd "${V13_DIR}"
    
    # Check for requirements.txt
    if [ ! -f "requirements.txt" ]; then
        log WARN "requirements.txt not found in ${V13_DIR}"
        save_state "V13_REQUIREMENTS" "No requirements.txt"
        return 0
    fi
    
    log INFO "Found requirements.txt"
    cat requirements.txt | sudo tee -a "${LOG_FILE}"
    
    # Upgrade pip first
    log INFO "Upgrading pip..."
    sudo pip3 install --upgrade pip 2>&1 | sudo tee -a "${LOG_FILE}" || true
    
    # Try multiple installation methods
    log INFO "Installing Python packages..."
    
    if sudo pip3 install -r requirements.txt --break-system-packages 2>&1 | sudo tee -a "${LOG_FILE}"; then
        log SUCCESS "Requirements installed with --break-system-packages"
    elif pip3 install -r requirements.txt --user 2>&1 | tee -a "${LOG_FILE}"; then
        log SUCCESS "Requirements installed with --user flag"
    elif sudo pip3 install -r requirements.txt 2>&1 | sudo tee -a "${LOG_FILE}"; then
        log SUCCESS "Requirements installed with sudo"
    else
        log ERROR "Failed to install Python requirements"
        return ${E_DEPENDENCY}
    fi
    
    # Verify installation
    log INFO "Verifying Python packages..."
    pip3 list 2>&1 | grep -E "(torch|requests|pillow|numpy)" | while read line; do
        log INFO "  ${line}"
    done
    
    log SUCCESS "Python requirements installed"
    save_state "V13_REQUIREMENTS" "Completed"
}

################################################################################
# POST-INSTALLATION
################################################################################

create_system_info() {
    log INFO "Generating system information file..."
    
    local info_file="${ESRGAN_DIR}/SYSTEM_INFO.txt"
    
    {
        echo "=================================="
        echo "ESRGAN Server Setup Information"
        echo "=================================="
        echo ""
        echo "Installation Date: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Script Version: ${SCRIPT_VERSION}"
        echo "Hostname: $(hostname)"
        echo ""
        echo "=== System Information ==="
        echo "OS: $(lsb_release -d | cut -f2)"
        echo "Kernel: $(uname -r)"
        echo "Architecture: $(uname -m)"
        echo ""
        echo "=== NVIDIA Information ==="
        if command -v nvidia-smi &> /dev/null; then
            nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
        else
            echo "NVIDIA drivers not detected"
        fi
        echo ""
        echo "=== Python Information ==="
        python3 --version
        pip3 --version
        echo ""
        echo "=== Installation Paths ==="
        echo "ESRGAN: ${ESRGAN_DIR}"
        echo "v13 Program: ${V13_DIR}"
        echo "Logs: ${LOG_DIR}"
        echo "Backups: ${BACKUP_DIR}"
        echo ""
        echo "=== Usage Instructions ==="
        echo "1. ESRGAN command: esrgan -i input.jpg -o output.jpg"
        echo "2. v13 program location: ${V13_DIR}"
        echo "3. View logs: cat ${LOG_FILE}"
        echo ""
    } | sudo tee "${info_file}" > /dev/null
    
    log SUCCESS "System information saved to ${info_file}"
}

create_service_file() {
    log INFO "Creating systemd service template for v13..."
    
    local service_file="/etc/systemd/system/v13-processor.service.template"
    
    sudo tee "${service_file}" > /dev/null <<EOF
[Unit]
Description=ESRGAN Image Processor v13
After=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${V13_DIR}
ExecStart=/usr/bin/python3 ${V13_DIR}/main.py
Restart=on-failure
RestartSec=10
StandardOutput=append:${LOG_DIR}/v13-processor.log
StandardError=append:${LOG_DIR}/v13-processor.log

[Install]
WantedBy=multi-user.target
EOF
    
    log INFO "Service template created at ${service_file}"
    log INFO "To use it:"
    log INFO "  1. Copy template: sudo cp ${service_file} /etc/systemd/system/v13-processor.service"
    log INFO "  2. Edit as needed: sudo nano /etc/systemd/system/v13-processor.service"
    log INFO "  3. Enable: sudo systemctl enable v13-processor"
    log INFO "  4. Start: sudo systemctl start v13-processor"
}

generate_health_check() {
    log INFO "Creating health check script..."
    
    local health_script="${ESRGAN_DIR}/health_check.sh"
    
    sudo tee "${health_script}" > /dev/null <<'EOF'
#!/bin/bash
# ESRGAN Health Check Script

echo "=== ESRGAN Health Check ==="
echo ""

# Check ESRGAN
echo "1. ESRGAN Status:"
if [ -x /home/esrgan/esrgan ]; then
    echo "  ✓ ESRGAN executable found"
    /home/esrgan/esrgan -h > /dev/null 2>&1 && echo "  ✓ ESRGAN runs successfully"
else
    echo "  ✗ ESRGAN executable not found or not executable"
fi

echo ""
echo "2. NVIDIA Driver:"
if command -v nvidia-smi &> /dev/null; then
    echo "  ✓ NVIDIA drivers installed"
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
else
    echo "  ✗ NVIDIA drivers not found"
fi

echo ""
echo "3. Vulkan:"
if command -v vulkaninfo &> /dev/null; then
    echo "  ✓ Vulkan tools installed"
    vulkaninfo --summary | grep -i "instance" | head -1
else
    echo "  ✗ Vulkan tools not found"
fi

echo ""
echo "4. Python Environment:"
python3 --version
pip3 --version

echo ""
echo "5. Disk Space:"
df -h /home | tail -1

echo ""
echo "=== Health Check Complete ==="
EOF
    
    sudo chmod +x "${health_script}"
    log SUCCESS "Health check script created at ${health_script}"
}

################################################################################
# MAIN EXECUTION
################################################################################

show_banner() {
    cat <<'EOF'
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     ESRGAN Server Setup Script                                ║
║     Enterprise-Grade Installation                             ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
}

show_summary() {
    log INFO "=================================="
    log SUCCESS "Installation Summary"
    log INFO "=================================="
    
    if load_state; then
        log INFO "Final State: ${STATE}"
    fi
    
    log INFO ""
    log INFO "Installation Paths:"
    log INFO "  ESRGAN: ${ESRGAN_DIR}"
    log INFO "  v13 Program: ${V13_DIR}"
    log INFO "  Logs: ${LOG_DIR}"
    log INFO "  Latest Log: ${LOG_FILE}"
    log INFO ""
    log INFO "Quick Start:"
    log INFO "  1. Open new terminal or run: source ~/.bashrc"
    log INFO "  2. Test ESRGAN: esrgan -h"
    log INFO "  3. Run health check: ${ESRGAN_DIR}/health_check.sh"
    log INFO "  4. View system info: cat ${ESRGAN_DIR}/SYSTEM_INFO.txt"
    log INFO ""
    
    if grep -q "Reboot required" "${STATE_FILE}" 2>/dev/null; then
        log WARN "⚠️  SYSTEM REBOOT REQUIRED ⚠️"
        log WARN "NVIDIA drivers were installed and require a reboot"
        log WARN "Run: sudo reboot"
    fi
    
    log INFO "=================================="
}

main() {
    # Setup
    show_banner
    setup_logging
    
    log INFO "Starting ESRGAN server setup..."
    log INFO "Script version: ${SCRIPT_VERSION}"
    
    # Pre-flight checks
    pre_flight_checks
    
    # Main installation
    update_system || exit $?
    install_nvidia_drivers || exit $?
    install_python || exit $?
    
    install_vulkan || exit $?
    configure_vulkan || exit $?
    test_vulkan
    
    install_esrgan || exit $?
    configure_esrgan || exit $?
    test_esrgan
    
    install_python_program || exit $?
    install_python_requirements || exit $?
    
    # Post-installation
    create_system_info
    create_service_file
    generate_health_check
    
    # Summary
    save_state "COMPLETED" "All tasks finished successfully"
    show_summary
    
    log SUCCESS "Setup completed successfully!"
}

# Run main function
main "$@"