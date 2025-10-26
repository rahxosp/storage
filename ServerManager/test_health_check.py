"""Quick test to verify health check feature implementation."""
from models import ServerConfig

# Test 1: Create config with health checks
print("Test 1: Creating ServerConfig with health checks...")
config = ServerConfig(
    name="test-server",
    host="1.2.3.4",
    port=22,
    username="root",
    auth={"type": "key", "key_path": "/path/to/key", "passphrase": None},
    health_check_enabled=True,
    health_check_cpu_enabled=True,
    health_check_cpu_threshold=30.0,
    health_check_cpu_duration=120,
    health_check_gpu_enabled=True,
    health_check_gpu_threshold=10.0,
    health_check_gpu_duration=100
)
print(f"✓ Config created: {config.name}")
print(f"  Health checks enabled: {config.health_check_enabled}")
print(f"  CPU monitoring: {config.health_check_cpu_enabled} (threshold: {config.health_check_cpu_threshold}%, duration: {config.health_check_cpu_duration}s)")
print(f"  GPU monitoring: {config.health_check_gpu_enabled} (threshold: {config.health_check_gpu_threshold}%, duration: {config.health_check_gpu_duration}s)")

# Test 2: Convert to dict
print("\nTest 2: Converting to dict...")
config_dict = config.to_dict()
assert "health_check_enabled" in config_dict
assert "health_check_cpu_enabled" in config_dict
assert "health_check_cpu_threshold" in config_dict
assert "health_check_cpu_duration" in config_dict
assert "health_check_gpu_enabled" in config_dict
assert "health_check_gpu_threshold" in config_dict
assert "health_check_gpu_duration" in config_dict
print("✓ All health check fields present in dict")

# Test 3: Default values
print("\nTest 3: Testing default values...")
config_default = ServerConfig(
    name="default-server",
    host="1.2.3.4",
    port=22,
    username="root",
    auth={"type": "key", "key_path": "/path/to/key", "passphrase": None}
)
assert config_default.health_check_enabled == False
assert config_default.health_check_cpu_enabled == False
assert config_default.health_check_cpu_threshold == 50.0
assert config_default.health_check_cpu_duration == 100
assert config_default.health_check_gpu_enabled == False
assert config_default.health_check_gpu_threshold == 50.0
assert config_default.health_check_gpu_duration == 100
print("✓ Default values are correct")

# Test 4: Load from config (backward compatibility)
print("\nTest 4: Testing backward compatibility...")
from config import load_servers
servers = load_servers()
print(f"✓ Loaded {len(servers)} servers from config")
for server in servers:
    print(f"  - {server.name}: health_check_enabled={server.health_check_enabled}")

print("\n✅ All tests passed!")
