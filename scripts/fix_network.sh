#!/bin/bash

# 1. Update docker-compose.yml to include DNS settings
echo "Updating docker-compose.yml with DNS resolvers..."
if ! grep -q "dns:" docker-compose.yml; then
    sed -i '/web:/a \    dns:\n      - 8.8.8.8\n      - 1.1.1.1' docker-compose.yml
else
    echo "DNS settings already exist."
fi

# 2. Restart the web container to apply changes
echo "Restarting web container..."
docker compose up -d web

# 3. Wait for the container to stabilize
echo "Waiting for container to come online..."
sleep 5

# 4. Final verification: Test DNS resolution inside the container
echo "Verifying DNS resolution for KRA eTIMS API..."
docker compose exec web python3 -c "import socket; print(f'Successfully resolved KRA API to: {socket.gethostbyname(\"api.etims-sandbox.kra.go.ke\")}')"

if [ $? -eq 0 ]; then
    echo "SUCCESS: Network is configured and KRA API is reachable."
else
    echo "ERROR: Still unable to resolve the API. Check your host machine's firewall or VPN."
fi
