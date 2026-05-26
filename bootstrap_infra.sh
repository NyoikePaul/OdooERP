#!/bin/bash

# Define the enterprise infrastructure structure
DIRS=(
    "addons"
    "custom_modules"
    "docker"
    "k8s"
    "terraform"
    "nginx"
    "monitoring"
    "backup"
    ".github/workflows"
    "docs"
)

echo "--- Initializing OdooERP Enterprise Infrastructure ---"

for dir in "${DIRS[@]}"; do
    # Create directory
    mkdir -p "$dir"
    
    # Add .gitkeep to ensure the directory is tracked by Git
    touch "$dir/.gitkeep"
    
    echo "Created: $dir/"
done

echo "--- Infrastructure Scaffolding Complete ---"
