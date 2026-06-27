# Production deployment templates for AmillionTechies

These files are intended to be installed with sudo into the host operating system.

## Files
- `deployment/systemd/amilliontechies-backend.service.example`
- `deployment/nginx/amilliontechies.conf.example`
- `deployment/scripts/install.sh`
- `deployment/scripts/build-frontend.sh`
- `deployment/scripts/deploy-backend.sh`
- `deployment/scripts/setup-ssl.sh`

## Installation
1. Ensure Nginx and Python system packages are installed.
2. Run the installer from the project root:

```bash
bash deployment/scripts/install.sh
```

The installer will copy the templates into the appropriate system locations:
- `/etc/systemd/system/amilliontechies-backend.service`
- `/etc/nginx/conf.d/amilliontechies.conf`

## Build and deploy steps
- Build the React frontend:

```bash
bash deployment/scripts/build-frontend.sh
```

- Run Django migrations and collect static files:

```bash
bash deployment/scripts/deploy-backend.sh
```

- Request and install HTTPS certificates with Certbot:

```bash
sudo bash deployment/scripts/setup-ssl.sh
```

If you prefer to install manually, copy the files yourself and adjust the paths for your host.
