#!/bin/bash
#
# Vulkan Setup Script for Headless VPS (vast.ai)
# Configures Vulkan to work with NVIDIA GPU on headless servers
#
# Usage: bash setup-vulkan.sh
#

set -e  # Exit on error

echo "=========================================="
echo "  Vulkan Setup for Headless NVIDIA VPS"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Check if NVIDIA driver is loaded
echo "🔍 Checking NVIDIA driver..."
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ nvidia-smi not found. Please install NVIDIA drivers first."
    exit 1
fi

DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
echo "✅ NVIDIA Driver: $DRIVER_VERSION"
echo ""

# Step 1: Update and install Vulkan packages
echo "📦 Installing Vulkan packages..."
apt update -qq
apt install -y vulkan-tools libvulkan1 mesa-vulkan-drivers vulkan-validationlayers > /dev/null 2>&1
echo "✅ Vulkan packages installed"
echo ""

# Step 2: Install X11 libraries (required dependencies)
echo "📦 Installing X11 libraries..."
apt install -y xvfb x11-utils libx11-6 libxext6 libxrandr2 libxrender1 libxxf86vm1 libxfixes3 > /dev/null 2>&1
echo "✅ X11 libraries installed"
echo ""

# Step 3: Fix NVIDIA ICD configuration
echo "🔧 Configuring NVIDIA Vulkan ICD..."

# Get API version from driver (default to 1.3.289 if not available)
API_VERSION="1.3.289"

# Create proper ICD configuration for headless (EGL instead of GLX)
cat > /etc/vulkan/icd.d/nvidia_icd.json << 'EOF'
{
    "file_format_version" : "1.0.0",
    "ICD": {
        "library_path": "libEGL_nvidia.so.0",
        "api_version" : "1.3.289"
    }
}
EOF

echo "✅ NVIDIA ICD configured for headless operation (EGL)"
echo ""

# Step 4: Verify installation
echo "🧪 Verifying Vulkan installation..."
ldconfig

# Run vulkaninfo and capture output
if VULKAN_OUTPUT=$(vulkaninfo --summary 2>&1); then
    # Check if NVIDIA GPU is detected
    if echo "$VULKAN_OUTPUT" | grep -q "NVIDIA GeForce"; then
        GPU_NAME=$(echo "$VULKAN_OUTPUT" | grep "deviceName" | head -1 | awk '{print $3, $4, $5, $6}')
        DRIVER_INFO=$(echo "$VULKAN_OUTPUT" | grep "driverInfo" | head -1 | awk '{print $3}')
        
        echo ""
        echo "=========================================="
        echo "  ✅ SUCCESS! Vulkan is configured!"
        echo "=========================================="
        echo "GPU Detected: $GPU_NAME"
        echo "Driver: $DRIVER_INFO"
        echo ""
        echo "You can now use Vulkan for GPU-accelerated"
        echo "image processing (ESRGAN, etc.) via SSH/CLI"
        echo "=========================================="
        exit 0
    else
        echo ""
        echo "⚠️  Vulkan installed but NVIDIA GPU not detected."
        echo "    Detected devices:"
        echo "$VULKAN_OUTPUT" | grep "deviceName" | head -5
        echo ""
        echo "Troubleshooting:"
        echo "  1. Check NVIDIA driver: nvidia-smi"
        echo "  2. Check ICD config: cat /etc/vulkan/icd.d/nvidia_icd.json"
        echo "  3. Check logs: VK_LOADER_DEBUG=all vulkaninfo --summary"
        exit 1
    fi
else
    echo "❌ Vulkan installation failed"
    echo "$VULKAN_OUTPUT"
    exit 1
fi
