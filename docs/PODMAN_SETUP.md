# Podman Setup Guide for GINI

This guide covers setting up Podman as the container runtime for GINI, with special emphasis on **rootless Podman** for campus environments where users lack sudo access.

## Why Podman?

Podman is a daemonless container engine that is particularly well-suited for educational and campus environments:

- **Rootless by default**: Runs without root privileges, perfect for shared lab machines
- **No central daemon**: Each user runs their own Podman instance, avoiding conflicts
- **Drop-in Docker compatibility**: Most Docker commands work unchanged
- **Better security**: Rootless containers provide stronger isolation
- **Campus-friendly**: Works on machines where users cannot install or run Docker Desktop

## Rootless vs Rootful Podman

### Rootless Podman (Recommended for Campus)

**Advantages:**
- No sudo required for everyday operations
- Each user has their own container namespace
- Better security isolation
- Perfect for shared lab environments
- No conflicts between users

**Limitations:**
- Some advanced networking features may require rootful mode
- Port numbers below 1024 require additional configuration
- Slightly different container storage paths

### Rootful Podman

**When to use:**
- You have sudo/admin access
- Need advanced networking features
- Running on personal development machine

**Setup requires sudo access and system-wide installation.**

## Platform-Specific Setup

### Linux (Ubuntu/Debian)

#### Rootless Podman (Recommended)

```bash
# Install Podman (no sudo needed for package installation on most systems)
sudo apt update
sudo apt install podman

# Install a Compose provider
sudo apt install podman-compose

# Enable rootless Podman socket (runs as your user, no sudo needed)
systemctl --user enable --now podman.socket

# Verify rootless mode
podman info --format {{.Host.Security.Rootless}}
# Should print: true
```

#### Rootful Podman

```bash
# Install Podman system-wide
sudo apt update
sudo apt install podman

# Start the Podman service (requires sudo)
sudo systemctl start podman
sudo systemctl enable podman

# Install Compose provider
sudo apt install podman-compose
```

### Linux (Fedora/RHEL)

#### Rootless Podman

```bash
# Install Podman
sudo dnf install podman

# Install Compose provider
sudo dnf install podman-compose

# Enable rootless socket
systemctl --user enable --now podman.socket

# Verify
podman info --format {{.Host.Security.Rootless}}
```

### macOS

#### Podman Desktop (Recommended)

```bash
# Install via Homebrew
brew install podman

# Initialize a Podman machine (rootless VM)
podman machine init --cpus 2 --memory 4096 --disk 30
podman machine start

# Verify
podman info
```

#### Podman Desktop Application

Download and install [Podman Desktop](https://podman-desktop.io/) for a GUI experience similar to Docker Desktop.

### Windows

#### Podman Desktop

```powershell
# Install via winget
winget install -e --id RedHat.Podman-Desktop

# Start Podman Desktop and initialize a machine
# The GUI will guide you through machine setup
```

## GINI Configuration

### Method 1: Settings Dialog (Recommended)

1. Launch gBuilder
2. Go to **Settings → Networking**
3. Set **Container engine** to **Podman**
4. Restart gBuilder for changes to take effect

### Method 2: Environment Variable

```bash
# Set for current session
export GINI_ENGINE=podman
gbuilder

# Set permanently (add to ~/.bashrc or ~/.zshrc)
echo 'export GINI_ENGINE=podman' >> ~/.bashrc
source ~/.bashrc
```

### Method 3: Configuration File

Edit `~/.gini/config.json`:

```json
{
  "container_engine": "podman"
}
```

## Priority Order

GINI uses the following priority for engine selection:

1. **GINI_ENGINE environment variable** (highest priority)
2. **Settings preference** from `~/.gini/config.json`
3. **Auto-detection** (Docker first, then Podman)

## Verifying Podman Setup

### Check Podman is Running

```bash
# Check Podman info
podman info

# Check rootless mode
podman info --format {{.Host.Security.Rootless}}

# Test a simple container
podman run --rm hello-world
```

### Check Compose Support

```bash
# Verify podman-compose is installed
podman-compose version

# Test compose
podman-compose up
```

### Verify GINI Detection

```bash
# Check what GINI detects
python3 -c "
from gini.setup.runtime import detect_engine, engine_name, docker_state
print(f'Engine: {detect_engine()}')
print(f'Name: {engine_name()}')
print(f'State: {docker_state()}')
"
```

## Common Issues and Solutions

### Issue: "permission denied" with rootless Podman

**Cause**: User namespaces not properly configured.

**Solution**:
```bash
# Check if user namespaces are enabled
cat /proc/sys/user/max_user_namespaces

# If 0, enable them (requires sudo)
echo "user.max_user_namespaces=15000" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Issue: Podman machine not started on macOS

**Cause**: Podman VM not initialized or running.

**Solution**:
```bash
# Initialize machine
podman machine init --cpus 2 --memory 4096 --disk 30

# Start machine
podman machine start

# Check status
podman machine list
```

### Issue: Cannot bind ports below 1024 (rootless)

**Cause**: Rootless containers cannot bind privileged ports.

**Solution**: Use ports above 1024, or configure port forwarding:
```bash
# Map container port 80 to host port 8080
podman run -p 8080:80 nginx
```

### Issue: GINI still detects Docker

**Cause**: Docker binary takes precedence in auto-detection.

**Solution**: Explicitly set Podman preference:
```bash
export GINI_ENGINE=podman
# Or use Settings dialog
```

### Issue: podman-compose not found

**Cause**: Compose provider not installed.

**Solution**:
```bash
# Ubuntu/Debian
sudo apt install podman-compose

# Fedora/RHEL
sudo dnf install podman-compose

# Or use Docker Compose v2 (Podman 4+ supports it)
sudo apt install docker-compose-plugin
```

## Network Configuration

### Rootless Podman Networking

Rootless Podman uses `slirp4netns` for user networking by default. This works well for most GINI scenarios.

### Custom Network Configuration

If you need custom networking:

```bash
# Create a custom network (may require additional setup for rootless)
podman network create gini-net

# Use the network in your containers
podman run --network gini-net ...
```

## Storage and Volumes

### Rootless Storage Location

Rootless Podman stores containers in:
- Linux: `~/.local/share/containers/`
- macOS: Inside the Podman VM
- Windows: Inside the Podman WSL distribution

### Volume Mounts

Rootless Podman can mount directories from your home directory without issues:

```bash
# Mount a directory from your home
podman run -v ~/myproject:/workspace myimage
```

## Performance Tips

### Rootless Podman Performance

Rootless Podman may have slightly different performance characteristics:

- **CPU**: Similar to Docker for most workloads
- **I/O**: May be slightly slower due to user namespace overhead
- **Network**: slirp4netns adds some overhead compared to bridge networks

### Optimizing for GINI

For best performance with GINI:

```bash
# Allocate sufficient resources to Podman machine (macOS)
podman machine init --cpus 4 --memory 8192 --disk 50

# Use local volumes instead of bind mounts where possible
# Pre-pull images to avoid download delays
podman pull ghcr.io/gini-toolkit/gini-xv6:latest
```

## Migration from Docker

### Switching Existing Setups

If you're migrating from Docker to Podman:

1. **Export Docker images** (if you have custom images):
   ```bash
   docker save -o myimage.tar myimage:latest
   podman load -i myimage.tar
   ```

2. **Update GINI settings** to use Podman
3. **Verify your topologies work** with Podman

### Docker Compose Compatibility

Podman-compose is compatible with most docker-compose.yml files:

```bash
# Use podman-compose instead of docker-compose
podman-compose up -d
```

## Security Considerations

### Rootless Security Benefits

- Containers run as your user, not root
- No privilege escalation to host system
- Better isolation between users on shared machines
- No central daemon that could be compromised

### Best Practices

- Keep Podman updated: `sudo apt update && sudo apt upgrade podman`
- Use official images from trusted registries
- Review container images before running
- Don't run containers with `--privileged` unless necessary

## Troubleshooting Commands

```bash
# Check Podman version
podman version

# Check system information
podman info

# Check running containers
podman ps

# Check container logs
podman logs <container_id>

# Check rootless status
podman info --format {{.Host.Security.Rootless}}

# Check available networks
podman network ls

# Check volume mounts
podman volume ls

# Reset Podman (last resort)
podman system reset -f
```

## Getting Help

If you encounter issues:

1. Check the [Podman documentation](https://docs.podman.io/)
2. Search existing [GINI issues](https://github.com/citelab/gini/issues)
3. Enable verbose logging in GINI for more diagnostics
4. Check Podman logs: `podman logs` or journalctl (for rootful)

## Advanced Configuration

### Podman Systemd Services

For rootless Podman, you can create user systemd services:

```bash
# Create a user service
~/.config/systemd/user/gini-lab.service

# Enable and start
systemctl --user enable --now gini-lab.service
```

### Custom Registries

Configure Podman to use custom registries:

```bash
# Edit registries.conf
~/.config/containers/registries.conf

# Add your registry
[[registry]]
location = "my-registry.example.com"
insecure = false
```

## Summary

Rootless Podman is the recommended container runtime for GINI in campus environments:

- ✅ No sudo required for students
- ✅ Better security and isolation
- ✅ Drop-in Docker compatibility
- ✅ Works on shared lab machines
- ✅ Configurable via GINI settings

For personal development machines, Docker Desktop or Colima may still be preferred, but Podman provides a robust alternative that works especially well in educational settings.