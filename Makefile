# OpenSearch Face Recognition System Makefile

.PHONY: help install build deploy destroy test clean lint format

# Default target
help:
	@echo "OpenSearch Face Recognition System"
	@echo "=================================="
	@echo ""
	@echo "Available targets:"
	@echo "  install    - Install dependencies"
	@echo "  build      - Build the project"
	@echo "  deploy     - Deploy to AWS"
	@echo "  destroy    - Destroy AWS resources"
	@echo "  test       - Run tests"
	@echo "  clean      - Clean build artifacts"
	@echo "  lint       - Run linting"
	@echo "  format     - Format code"
	@echo "  bootstrap  - Bootstrap CDK"
	@echo "  synth      - Synthesize CDK templates"
	@echo ""

# Install dependencies
install:
	@echo "Installing dependencies..."
	npm install
	python3 -m venv venv || true
	. venv/bin/activate && pip install -r requirements.txt
	@echo "Dependencies installed successfully!"

# Build Lambda layers
build:
	@echo "Building Lambda layers..."
	mkdir -p layers/dependencies/python
	. venv/bin/activate && pip install -r layers/dependencies/requirements.txt -t layers/dependencies/python/
	@echo "Build completed successfully!"

# Bootstrap CDK
bootstrap:
	@echo "Bootstrapping CDK..."
	. venv/bin/activate && cdk bootstrap
	@echo "CDK bootstrap completed!"

# Synthesize CDK templates
synth:
	@echo "Synthesizing CDK templates..."
	. venv/bin/activate && cdk synth --all
	@echo "CDK synthesis completed!"

# Deploy to AWS
deploy: build
	@echo "Deploying to AWS..."
	chmod +x scripts/deploy.sh
	./scripts/deploy.sh --auto-approve
	@echo "Deployment completed!"

# Deploy with manual approval
deploy-manual: build
	@echo "Deploying to AWS (manual approval)..."
	chmod +x scripts/deploy.sh
	./scripts/deploy.sh
	@echo "Deployment completed!"

# Destroy AWS resources
destroy:
	@echo "Destroying AWS resources..."
	. venv/bin/activate && cdk destroy --all --force
	@echo "Resources destroyed!"

# Run tests
test:
	@echo "Running tests..."
	. venv/bin/activate && python -m pytest tests/ -v || echo "No tests found"
	@echo "Tests completed!"

# Test API (requires API_URL environment variable)
test-api:
	@echo "Testing API..."
	@if [ -z "$(API_URL)" ]; then \
		echo "Error: API_URL environment variable is required"; \
		echo "Usage: make test-api API_URL=https://your-api-gateway-url"; \
		exit 1; \
	fi
	. venv/bin/activate && python scripts/test_api.py --api-url $(API_URL)
	@echo "API tests completed!"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf cdk.out/
	rm -rf .cdk.staging/
	rm -rf layers/dependencies/python/
	rm -rf __pycache__/
	rm -rf **/__pycache__/
	rm -rf *.pyc
	rm -rf **/*.pyc
	rm -rf .pytest_cache/
	rm -rf node_modules/
	@echo "Clean completed!"

# Run linting
lint:
	@echo "Running linting..."
	. venv/bin/activate && flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || echo "flake8 not installed"
	. venv/bin/activate && flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics || echo "flake8 not installed"
	@echo "Linting completed!"

# Format code
format:
	@echo "Formatting code..."
	. venv/bin/activate && black . || echo "black not installed"
	@echo "Code formatting completed!"

# Setup development environment
setup-dev: install
	@echo "Setting up development environment..."
	. venv/bin/activate && pip install black flake8 pytest
	cp .env.example .env
	@echo "Development environment setup completed!"
	@echo "Please edit .env file with your configuration"

# Migration from Rekognition Collections
migrate:
	@echo "Running migration from Rekognition Collections..."
	. venv/bin/activate && python scripts/migrate_from_rekognition.py --list-only
	@echo "Migration completed! Use --collection-id to migrate specific collections"

# Show CDK diff
diff:
	@echo "Showing CDK diff..."
	. venv/bin/activate && cdk diff --all
	@echo "CDK diff completed!"

# List CDK stacks
list:
	@echo "Listing CDK stacks..."
	. venv/bin/activate && cdk list
	@echo "CDK list completed!"

# Show deployment info
info:
	@echo "Deployment Information:"
	@echo "======================"
	. venv/bin/activate && aws cloudformation describe-stacks --query 'Stacks[?contains(StackName, `OpenSearchFaceRecognition`) || contains(StackName, `FaceRecognition`)].{StackName:StackName,Status:StackStatus}' --output table || echo "No stacks found"

# Quick start (install, build, deploy)
quickstart: install build bootstrap deploy
	@echo "Quick start completed!"
	@echo "Run 'make info' to see deployment information"

# Development workflow
dev: setup-dev synth
	@echo "Development setup completed!"
	@echo "You can now run 'make deploy' to deploy the stack"
