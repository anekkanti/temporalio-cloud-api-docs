# API Documentation Generator Justfile

# Default recipe - shows available commands
default:
    @just --list

# Clone the cloud-api repository
clone-repo:
    #!/usr/bin/env bash
    if [ ! -d "../cloud-api" ]; then
        echo "Cloning temporalio/cloud-api repository..."
        git clone https://github.com/temporalio/cloud-api.git ../cloud-api
        echo "Repository cloned successfully!"
    else
        echo "Repository already exists at ../cloud-api"
        echo "Use 'just update-repo' to pull latest changes"
    fi

# Update the existing cloud-api repository
update-repo:
    #!/usr/bin/env bash
    if [ -d "../cloud-api" ]; then
        echo "Updating cloud-api repository..."
        cd ../cloud-api && git pull origin main
        echo "Repository updated successfully!"
    else
        echo "Repository not found. Run 'just clone-repo' first."
        exit 1
    fi

# Generate HTML documentation
generate-docs:
    #!/usr/bin/env bash
    if [ ! -d "../cloud-api" ]; then
        echo "Cloud-api repository not found. Cloning first..."
        just clone-repo
    fi
    echo "Generating API documentation..."
    python3 api_docs_generator.py ../cloud-api/temporal/api/cloud/cloudservice/v1 --output cloudservice_api.html
    echo "Documentation generated: cloudservice_api.html"



# Clean generated files
clean:
    rm -f *.html
    rm -rf ../cloud-api
    echo "Cleaned all files and cloned repository"

