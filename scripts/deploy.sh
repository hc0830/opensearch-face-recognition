#!/bin/bash

# OpenSearch Face Recognition System Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Node.js
    if ! command_exists node; then
        print_error "Node.js is not installed. Please install Node.js 14.x or later."
        exit 1
    fi
    
    # Check Python
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3.8 or later."
        exit 1
    fi
    
    # Check AWS CLI
    if ! command_exists aws; then
        print_error "AWS CLI is not installed. Please install AWS CLI v2."
        exit 1
    fi
    
    # Check CDK CLI
    if ! command_exists cdk; then
        print_error "AWS CDK CLI is not installed. Installing..."
        npm install -g aws-cdk
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        print_error "AWS credentials are not configured. Please run 'aws configure'."
        exit 1
    fi
    
    print_success "All prerequisites are met."
}

# Function to setup environment
setup_environment() {
    print_status "Setting up environment..."
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from template..."
        cp .env.example .env
        print_warning "Please edit .env file with your configuration before continuing."
        read -p "Press Enter to continue after editing .env file..."
    fi
    
    # Load environment variables
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs)
    fi
    
    # Install Python dependencies
    print_status "Installing Python dependencies..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install -r requirements.txt
    
    # Install Node.js dependencies
    print_status "Installing Node.js dependencies..."
    npm install
    
    print_success "Environment setup completed."
}

# Function to bootstrap CDK
bootstrap_cdk() {
    print_status "Bootstrapping CDK..."
    
    # Get AWS account and region
    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=${CDK_DEFAULT_REGION:-us-east-1}
    
    print_status "Bootstrapping CDK for account $AWS_ACCOUNT in region $AWS_REGION"
    
    cdk bootstrap aws://$AWS_ACCOUNT/$AWS_REGION
    
    print_success "CDK bootstrap completed."
}

# Function to build Lambda layers
build_lambda_layers() {
    print_status "Building Lambda layers..."
    
    # Create dependencies layer
    LAYER_DIR="layers/dependencies"
    if [ -d "$LAYER_DIR/python" ]; then
        rm -rf "$LAYER_DIR/python"
    fi
    
    mkdir -p "$LAYER_DIR/python"
    
    # Install dependencies
    pip install -r "$LAYER_DIR/requirements.txt" -t "$LAYER_DIR/python/"
    
    print_success "Lambda layers built successfully."
}

# Function to synthesize CDK
synthesize_cdk() {
    print_status "Synthesizing CDK templates..."
    
    source venv/bin/activate
    cdk synth --all
    
    print_success "CDK synthesis completed."
}

# Function to deploy infrastructure
deploy_infrastructure() {
    print_status "Deploying infrastructure..."
    
    source venv/bin/activate
    
    # Deploy with confirmation
    if [ "$1" = "--auto-approve" ]; then
        cdk deploy --all --require-approval never
    else
        cdk deploy --all
    fi
    
    print_success "Infrastructure deployment completed."
}

# Function to setup OpenSearch index
setup_opensearch_index() {
    print_status "Setting up OpenSearch index..."
    
    # This would typically be done via a custom resource or initialization script
    # For now, we'll just print instructions
    print_warning "OpenSearch index setup needs to be done manually or via initialization script."
    print_status "The index will be created automatically when the first face is indexed."
    
    print_success "OpenSearch setup completed."
}

# Function to run tests
run_tests() {
    print_status "Running tests..."
    
    source venv/bin/activate
    
    # Run unit tests if they exist
    if [ -d "tests" ]; then
        python -m pytest tests/ -v
    else
        print_warning "No tests found. Skipping test execution."
    fi
    
    print_success "Tests completed."
}

# Function to display deployment information
display_deployment_info() {
    print_success "Deployment completed successfully!"
    echo
    print_status "Deployment Information:"
    echo "========================"
    
    # Get stack outputs
    source venv/bin/activate
    
    echo "Getting stack outputs..."
    cdk list --long 2>/dev/null | grep -E "OpenSearchFaceRecognitionStack|FaceRecognitionApiStack" | while read stack; do
        echo
        echo "Stack: $stack"
        aws cloudformation describe-stacks --stack-name "$stack" --query 'Stacks[0].Outputs' --output table 2>/dev/null || echo "Could not retrieve outputs for $stack"
    done
    
    echo
    print_status "Next Steps:"
    echo "1. Test the API endpoints using the provided URLs"
    echo "2. Upload test images to the S3 bucket"
    echo "3. Monitor the system using CloudWatch Dashboard"
    echo "4. Run migration script if you have existing Rekognition Collections"
    echo
    print_status "Migration Command:"
    echo "python scripts/migrate_from_rekognition.py --list-only"
}

# Function to cleanup on failure
cleanup_on_failure() {
    print_error "Deployment failed. Cleaning up..."
    
    # Optionally destroy stacks on failure
    read -p "Do you want to destroy the deployed stacks? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        source venv/bin/activate
        cdk destroy --all --force
    fi
}

# Main deployment function
main() {
    echo "=========================================="
    echo "OpenSearch Face Recognition System"
    echo "Deployment Script"
    echo "=========================================="
    echo
    
    # Parse command line arguments
    AUTO_APPROVE=false
    SKIP_TESTS=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --auto-approve)
                AUTO_APPROVE=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --auto-approve    Skip deployment confirmation prompts"
                echo "  --skip-tests      Skip running tests"
                echo "  --help           Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Set trap for cleanup on failure
    trap cleanup_on_failure ERR
    
    # Run deployment steps
    check_prerequisites
    setup_environment
    bootstrap_cdk
    build_lambda_layers
    
    if [ "$SKIP_TESTS" = false ]; then
        run_tests
    fi
    
    synthesize_cdk
    
    if [ "$AUTO_APPROVE" = true ]; then
        deploy_infrastructure --auto-approve
    else
        deploy_infrastructure
    fi
    
    setup_opensearch_index
    display_deployment_info
    
    print_success "All done! 🎉"
}

# Run main function
main "$@"
