#!/bin/bash

set -e

echo "========================================"
echo "ESRGAN Server Setup Script v2.0"
echo "========================================"
echo ""

# Update system
echo "📦 Updating system..."
apt update
apt upgrade -y

# Install essential packages
echo "📦 Installing essential packages..."
apt install -y curl wget unzip build-essential

# Check NVIDIA drivers
echo "🔍 Checking NVIDIA drivers..."
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA drivers found"
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
else
    echo "⚠️  NVIDIA drivers not found, installing..."
    apt install -y nvidia-driver-525 nvidia-utils-525
    echo "⚠️  Reboot required after script completes"
fi

# Install Python
echo "📦 Installing Python..."
apt install -y python3 python3-pip python3-venv python3-dev
echo "✅ Python $(python3 --version) installed"

# Install Vulkan (using proven vulkan.sh method)
echo "📦 Installing Vulkan..."
apt install -y vulkan-tools libvulkan1 libvulkan-dev mesa-vulkan-drivers vulkan-validationlayers

echo "📦 Installing X11 libraries..."
apt install -y xvfb x11-utils libx11-6 libxext6 libxrandr2 libxrender1 libxxf86vm1 libxfixes3

echo "🔧 Configuring NVIDIA Vulkan ICD..."
mkdir -p /etc/vulkan/icd.d/
cat > /etc/vulkan/icd.d/nvidia_icd.json <<'EOF'
{
    "file_format_version": "1.0.0",
    "ICD": {
        "library_path": "libEGL_nvidia.so.0",
        "api_version": "1.3.289"
    }
}
EOF
echo "✅ NVIDIA ICD configured"

# Test Vulkan
echo "🧪 Testing Vulkan..."
if vulkaninfo --summary | grep -q "Vulkan Instance"; then
    echo "✅ Vulkan is working!"
else
    echo "⚠️  Vulkan test incomplete (may need reboot)"
fi

# Install ESRGAN
echo "📦 Installing ESRGAN..."
mkdir -p /home/esrgan
cd /home/esrgan

echo "⬇️  Downloading ESRGAN..."
wget -O esrgan.zip "https://raw.githubusercontent.com/rahxosp/storage/refs/heads/main/esgan.zip"
unzip -o esrgan.zip
rm esrgan.zip

# Configure ESRGAN
if [ -f "realesrgan-ncnn-vulkan" ]; then
    chmod +x realesrgan-ncnn-vulkan
    ln -sf realesrgan-ncnn-vulkan esrgan
    chmod +x esrgan
    echo "✅ ESRGAN installed"
else
    echo "❌ ESRGAN executable not found"
    ls -la /home/esrgan/
fi

# Add to PATH
if ! grep -q "export PATH=\$PATH:/home/esrgan" ~/.bashrc; then
    echo 'export PATH=$PATH:/home/esrgan' >> ~/.bashrc
fi
echo "export PATH=\$PATH:/home/esrgan" > /etc/profile.d/esrgan.sh
chmod +x /etc/profile.d/esrgan.sh

# Test ESRGAN
cd /home/esrgan
if [ -f "input.jpg" ]; then
    echo "🧪 Testing ESRGAN..."
    ./esrgan -h || echo "⚠️  Help command failed"
    if ./esrgan -i input.jpg -o test_output.jpg 2>&1; then
        echo "✅ ESRGAN test successful!"
    else
        echo "⚠️  ESRGAN test failed (may need reboot for GPU)"
    fi
fi

# Install v13 Python program
echo "📦 Installing v13 Python program..."
mkdir -p /home/v13
cd /home/v13

echo "⬇️  Downloading v13..."
wget -O v13.zip "https://raw.githubusercontent.com/rahxosp/storage/refs/heads/main/v13.zip"
unzip -o v13.zip
rm v13.zip

chmod -R 755 /home/v13
find /home/v13 -name "*.py" -exec chmod +x {} \;

# Install Python requirements
if [ -f "requirements.txt" ]; then
    echo "📦 Installing Python packages..."
    pip3 install --upgrade pip
    if pip3 install -r requirements.txt --break-system-packages 2>/dev/null; then
        echo "✅ Python packages installed"
    elif pip3 install -r requirements.txt --user; then
        echo "✅ Python packages installed (user mode)"
    else
        pip3 install -r requirements.txt
        echo "✅ Python packages installed"
    fi
else
    echo "⚠️  No requirements.txt found"
fi

# Summary
echo ""
echo "========================================"
echo "✅ Installation Complete!"
echo "========================================"
echo ""
echo "📍 Locations:"
echo "  - ESRGAN: /home/esrgan"
echo "  - v13 Program: /home/v13"
echo ""
echo "🚀 Next Steps:"
echo "  1. Run: source ~/.bashrc"
echo "  2. Test: esrgan -h"
echo "  3. v13 is ready at /home/v13"
echo ""
echo "⚠️  If NVIDIA drivers were installed, reboot now: sudo reboot"
echo "========================================"
