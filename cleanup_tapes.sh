#!/bin/bash

#==============================================================================
# AWS Virtual Tape Cleanup Shell Script
#==============================================================================
#
# This script provides a user-friendly wrapper around the Python virtual tape
# cleanup tool. It handles argument parsing, validation, dependency checking,
# and provides safety prompts for actual deletions.
#
# Features:
# - Colored output for better readability
# - Automatic dependency checking and installation
# - Safety confirmation prompts
# - Comprehensive help documentation
# - Error handling and validation
#
# Author: Generated for AWS Virtual Tape Management
# Version: 1.0
#
#==============================================================================

# Enable strict error handling
# -e: Exit immediately if any command fails
# This ensures the script stops on errors rather than continuing with invalid state
set -e

#==============================================================================
# CONFIGURATION AND DEFAULTS
#==============================================================================

# Initialize default values for all script parameters
# These can be overridden by command-line arguments
REGION=""                    # AWS region (required)
PROFILE=""                   # AWS profile (optional, uses default if empty)
EXPIRY_DAYS=30              # Default expiry threshold in days
DRY_RUN=true                # Default to safe dry-run mode
GATEWAY_ARN=""              # Specific gateway ARN (optional)
BYPASS_GOVERNANCE=false     # Default to respecting governance retention

# Operation mode flags (mutually exclusive)
LIST_ALL=false              # List all tapes mode
DELETE_EXPIRED=true         # Delete expired tapes mode (default)
DELETE_SPECIFIC=false       # Delete specific tapes mode

# Tape specification options (for delete-specific mode)
TAPE_LIST=""                # Comma-separated list of tapes
TAPE_FILE=""                # File containing tape list

# Output options
OUTPUT_FILE=""              # File to save tape list (for list-all mode)

#==============================================================================
# COLOR DEFINITIONS FOR OUTPUT FORMATTING
#==============================================================================

# ANSI color codes for enhanced terminal output
# These make the script output more readable and help users identify
# different types of messages (info, warning, error)
RED='\033[0;31m'      # Red for errors
GREEN='\033[0;32m'    # Green for informational messages
YELLOW='\033[1;33m'   # Yellow for warnings
NC='\033[0m'          # No Color - resets to default

#==============================================================================
# OUTPUT FORMATTING FUNCTIONS
#==============================================================================

# Function to print informational messages in green
# Usage: print_info "Your message here"
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# Function to print warning messages in yellow
# Usage: print_warning "Your warning message here"
print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to print error messages in red
# Usage: print_error "Your error message here"
print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

#==============================================================================
# HELP DOCUMENTATION FUNCTION
#==============================================================================

# Function to display comprehensive usage information
# This provides users with all the information they need to use the script
# including examples, parameter descriptions, and common use cases
show_usage() {
    cat << EOF
#==============================================================================
# AWS Virtual Tape Cleanup Script
#==============================================================================

DESCRIPTION:
    Delete expired virtual tapes from AWS Storage Gateway based on age threshold.
    Provides safe dry-run mode by default with optional execution mode.

USAGE: 
    $0 [OPTIONS]

REQUIRED OPTIONS:
    -r, --region REGION         AWS region where Storage Gateway is located
                               Example: us-east-1, eu-west-1, ap-southeast-2

OPTIONAL PARAMETERS:
    -p, --profile PROFILE       AWS profile to use for authentication
                               Uses default AWS credentials if not specified
                               
    -d, --expiry-days DAYS      Number of days after which tapes are considered expired
                               Default: 30 days (only used with --delete-expired)
                               
    -g, --gateway-arn ARN       Specific Storage Gateway ARN to target
                               If not specified, processes all gateways in region
                               
    -e, --execute               Actually delete expired tapes
                               Default behavior is dry-run (safe mode)
                               
    --bypass-governance         Bypass governance retention policies
                               Use with caution - may override compliance controls

OPERATION MODE OPTIONS (mutually exclusive):
    --list-all                  List all virtual tapes with detailed information
                               Provides comprehensive inventory report
                               
    --delete-expired            Delete expired tapes based on age threshold
                               This is the default operation mode
                               
    --delete-specific           Delete specific tapes from a provided list
                               Requires --tape-list or --tape-file

TAPE SPECIFICATION OPTIONS (for --delete-specific):
    --tape-list "tape1,tape2"   Comma-separated list of tape ARNs or barcodes
                               Example: "VTL001,VTL002,arn:aws:storagegateway:..."
                               
    --tape-file FILE            File containing tape ARNs or barcodes (one per line)
                               Lines starting with # are treated as comments

OUTPUT OPTIONS (for --list-all):
    --output-file FILE          Save tape list to file (one barcode per line)
                               Can be used later with --delete-specific --tape-file
                               
    -h, --help                  Show this help message and exit

SAFETY FEATURES:
    • Dry-run mode by default - shows what would be deleted without actual deletion
    • Confirmation prompt before actual deletions
    • Only processes tapes in deletable states (AVAILABLE, ARCHIVED)
    • Comprehensive logging and error reporting
    • Validates all prerequisites before execution

EXAMPLES:
    # List all virtual tapes (inventory mode)
    $0 --region us-east-1 --list-all

    # List all tapes and save to file for later use
    $0 --region us-east-1 --list-all --output-file all_tapes.txt

    # Safe dry-run to preview what expired tapes would be deleted (default mode)
    $0 --region us-east-1 --expiry-days 60

    # Actually delete expired tapes after reviewing dry-run results
    $0 --region us-east-1 --expiry-days 60 --execute

    # Delete specific tapes by barcode/ARN (dry-run)
    $0 --region us-east-1 --delete-specific --tape-list "VTL001,VTL002,VTL003"

    # Delete specific tapes from file (actual deletion)
    $0 --region us-east-1 --delete-specific --tape-file tapes_to_delete.txt --execute

    # Workflow: List all tapes, then delete specific ones
    $0 --region us-east-1 --list-all --output-file all_tapes.txt
    # Edit all_tapes.txt to keep only tapes you want to delete
    $0 --region us-east-1 --delete-specific --tape-file all_tapes.txt --execute

    # Use specific AWS profile for multi-account environments
    $0 --region us-west-2 --profile production --expiry-days 90 --execute

    # Target specific Storage Gateway
    $0 --region us-east-1 --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-12345678 --execute

    # Override governance retention (use with extreme caution)
    $0 --region us-east-1 --expiry-days 30 --execute --bypass-governance

PREREQUISITES:
    • Python 3.6 or higher
    • boto3 Python library
    • AWS CLI configured with appropriate credentials
    • IAM permissions for Storage Gateway operations

REQUIRED IAM PERMISSIONS:
    • storagegateway:ListGateways
    • storagegateway:ListTapes
    • storagegateway:DescribeTapes  
    • storagegateway:DeleteTape

For more information, see the README.md file.

EOF
}

#==============================================================================
# COMMAND LINE ARGUMENT PARSING
#==============================================================================

# Parse all command-line arguments using a while loop
# This approach handles both short (-r) and long (--region) format options
# and provides flexible argument processing
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--region)
            # AWS region specification (required parameter)
            REGION="$2"
            shift 2  # Move past both the flag and its value
            ;;
        -p|--profile)
            # AWS profile for authentication (optional parameter)
            PROFILE="$2"
            shift 2
            ;;
        -d|--expiry-days)
            # Age threshold for tape expiry (optional, defaults to 30)
            EXPIRY_DAYS="$2"
            shift 2
            ;;
        -g|--gateway-arn)
            # Specific Storage Gateway ARN to target (optional)
            GATEWAY_ARN="$2"
            shift 2
            ;;
        -e|--execute)
            # Override dry-run mode to actually delete tapes
            DRY_RUN=false
            shift 1  # This is a flag without a value
            ;;
        --bypass-governance)
            # Override governance retention policies (use with caution)
            BYPASS_GOVERNANCE=true
            shift 1
            ;;
        --list-all)
            # List all tapes mode
            LIST_ALL=true
            DELETE_EXPIRED=false
            DELETE_SPECIFIC=false
            shift 1
            ;;
        --delete-expired)
            # Delete expired tapes mode (default, but can be explicit)
            DELETE_EXPIRED=true
            LIST_ALL=false
            DELETE_SPECIFIC=false
            shift 1
            ;;
        --delete-specific)
            # Delete specific tapes mode
            DELETE_SPECIFIC=true
            LIST_ALL=false
            DELETE_EXPIRED=false
            shift 1
            ;;
        --tape-list)
            # Comma-separated list of tapes to delete
            TAPE_LIST="$2"
            shift 2
            ;;
        --tape-file)
            # File containing list of tapes to delete
            TAPE_FILE="$2"
            shift 2
            ;;
        --output-file)
            # File to save tape list (for list-all mode)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            # Display help information and exit
            show_usage
            exit 0
            ;;
        *)
            # Handle unknown/invalid arguments
            print_error "Unknown option: $1"
            echo ""  # Add blank line for readability
            show_usage
            exit 1
            ;;
    esac
done

#==============================================================================
# INPUT VALIDATION AND PREREQUISITE CHECKING
#==============================================================================

# Validate that all required parameters are provided
if [[ -z "$REGION" ]]; then
    print_error "AWS region is required but not provided"
    echo ""
    print_info "Use --region to specify the AWS region (e.g., --region us-east-1)"
    echo ""
    show_usage
    exit 1
fi

# Validate operation mode specific requirements
if [[ "$DELETE_SPECIFIC" == "true" ]]; then
    if [[ -z "$TAPE_LIST" && -z "$TAPE_FILE" ]]; then
        print_error "--delete-specific requires either --tape-list or --tape-file"
        echo ""
        show_usage
        exit 1
    fi
    
    if [[ -n "$TAPE_LIST" && -n "$TAPE_FILE" ]]; then
        print_error "Cannot specify both --tape-list and --tape-file"
        echo ""
        show_usage
        exit 1
    fi
fi

# Validate that tape list/file options are only used with delete-specific mode
if [[ -n "$TAPE_LIST" || -n "$TAPE_FILE" ]] && [[ "$DELETE_SPECIFIC" != "true" ]]; then
    print_error "--tape-list and --tape-file can only be used with --delete-specific"
    echo ""
    show_usage
    exit 1
fi

# Validate that output file is only used with list-all mode
if [[ -n "$OUTPUT_FILE" && "$LIST_ALL" != "true" ]]; then
    print_error "--output-file can only be used with --list-all"
    echo ""
    show_usage
    exit 1
fi

# Validate that the expiry days is a positive number
if [[ ! "$EXPIRY_DAYS" =~ ^[0-9]+$ ]] || [[ "$EXPIRY_DAYS" -le 0 ]]; then
    print_error "Expiry days must be a positive integer, got: $EXPIRY_DAYS"
    exit 1
fi

# Validate tape file exists if specified
if [[ -n "$TAPE_FILE" && ! -f "$TAPE_FILE" ]]; then
    print_error "Tape file not found: $TAPE_FILE"
    exit 1
fi

print_info "Starting prerequisite checks..."

# Check if the Python script exists in the current directory
# This is critical as the shell script is just a wrapper
if [[ ! -f "delete_expired_virtual_tapes.py" ]]; then
    print_error "delete_expired_virtual_tapes.py not found in current directory"
    print_info "Please ensure the Python script is in the same directory as this shell script"
    exit 1
fi

# Verify Python 3 is installed and accessible
if ! command -v python3 &> /dev/null; then
    print_error "python3 is required but not installed or not in PATH"
    print_info "Please install Python 3.6 or higher to continue"
    exit 1
fi

# Check if boto3 is available, install if missing
# boto3 is the AWS SDK for Python and is required for all AWS operations
print_info "Checking for boto3 Python library..."
if ! python3 -c "import boto3" &> /dev/null; then
    print_warning "boto3 not found. Attempting to install from requirements.txt..."
    
    # Check if requirements.txt exists
    if [[ ! -f "requirements.txt" ]]; then
        print_error "requirements.txt not found. Cannot install boto3 automatically."
        print_info "Please install boto3 manually: pip3 install boto3"
        exit 1
    fi
    
    # Attempt to install dependencies
    if ! pip3 install -r requirements.txt; then
        print_error "Failed to install required dependencies"
        print_info "Please install boto3 manually: pip3 install boto3"
        exit 1
    fi
    
    print_info "Successfully installed boto3"
else
    print_info "boto3 is available"
fi

print_info "All prerequisites satisfied"

#==============================================================================
# COMMAND CONSTRUCTION AND EXECUTION
#==============================================================================

# Build the Python command with all specified parameters
# Start with the base command and region (which is always required)
CMD="python3 delete_expired_virtual_tapes.py --region $REGION"

# Add operation mode flags
if [[ "$LIST_ALL" == "true" ]]; then
    CMD="$CMD --list-all"
    print_info "Operation mode: List all tapes (inventory)"
    
    # Add output file if specified
    if [[ -n "$OUTPUT_FILE" ]]; then
        CMD="$CMD --output-file \"$OUTPUT_FILE\""
        print_info "Output file: $OUTPUT_FILE"
    fi
elif [[ "$DELETE_SPECIFIC" == "true" ]]; then
    CMD="$CMD --delete-specific"
    print_info "Operation mode: Delete specific tapes"
else
    CMD="$CMD --delete-expired"
    print_info "Operation mode: Delete expired tapes"
fi

# Add common optional parameters only if they were specified
if [[ -n "$PROFILE" ]]; then
    CMD="$CMD --profile $PROFILE"
    print_info "Using AWS profile: $PROFILE"
fi

if [[ -n "$GATEWAY_ARN" ]]; then
    CMD="$CMD --gateway-arn $GATEWAY_ARN"
    print_info "Targeting specific gateway: $GATEWAY_ARN"
fi

# Add mode-specific parameters
if [[ "$DELETE_EXPIRED" == "true" ]]; then
    CMD="$CMD --expiry-days $EXPIRY_DAYS"
    print_info "Expiry threshold: $EXPIRY_DAYS days"
fi

if [[ "$DELETE_SPECIFIC" == "true" ]]; then
    if [[ -n "$TAPE_LIST" ]]; then
        CMD="$CMD --tape-list \"$TAPE_LIST\""
        print_info "Using tape list: $TAPE_LIST"
    elif [[ -n "$TAPE_FILE" ]]; then
        CMD="$CMD --tape-file \"$TAPE_FILE\""
        print_info "Using tape file: $TAPE_FILE"
    fi
fi

# Add execution mode flag if not in dry-run (only for deletion operations)
if [[ "$LIST_ALL" != "true" ]]; then
    if [[ "$DRY_RUN" == "false" ]]; then
        CMD="$CMD --execute"
    fi
    
    # Add governance bypass flag if specified
    if [[ "$BYPASS_GOVERNANCE" == "true" ]]; then
        CMD="$CMD --bypass-governance"
        print_warning "Governance retention bypass enabled - use with caution"
    fi
fi

#==============================================================================
# SAFETY CHECKS AND USER CONFIRMATION
#==============================================================================

# Display execution summary for user review
echo ""
print_info "=== EXECUTION SUMMARY ==="
print_info "Region: $REGION"
print_info "Profile: ${PROFILE:-default}"

if [[ "$LIST_ALL" == "true" ]]; then
    print_info "Operation: List all virtual tapes"
    if [[ -n "$OUTPUT_FILE" ]]; then
        print_info "Output file: $OUTPUT_FILE"
    fi
elif [[ "$DELETE_SPECIFIC" == "true" ]]; then
    print_info "Operation: Delete specific tapes"
    if [[ -n "$TAPE_LIST" ]]; then
        print_info "Tape list: $TAPE_LIST"
    else
        print_info "Tape file: $TAPE_FILE"
    fi
else
    print_info "Operation: Delete expired tapes"
    print_info "Expiry threshold: $EXPIRY_DAYS days"
fi

print_info "Gateway ARN: ${GATEWAY_ARN:-all gateways in region}"

if [[ "$LIST_ALL" != "true" ]]; then
    print_info "Mode: $(if [[ "$DRY_RUN" == "true" ]]; then echo "DRY RUN"; else echo "EXECUTE"; fi)"
    print_info "Bypass governance: $BYPASS_GOVERNANCE"
fi
echo ""

# Show the exact command that will be executed for transparency
print_info "Executing command: $CMD"
echo ""

# Provide appropriate warnings based on operation mode
if [[ "$LIST_ALL" == "true" ]]; then
    print_info "Listing all virtual tapes (read-only operation)"
    echo ""
elif [[ "$DRY_RUN" == "true" ]]; then
    print_warning "This is a DRY RUN. No tapes will actually be deleted."
    print_warning "Use --execute flag to actually delete tapes."
    echo ""
else
    # For actual execution, provide strong warnings and require confirmation
    print_warning "⚠️  DANGER: This will ACTUALLY DELETE virtual tapes! ⚠️"
    print_warning "This action is PERMANENT and CANNOT be undone!"
    print_warning "Deleted tapes cannot be recovered!"
    echo ""
    
    # Require explicit user confirmation for destructive operations
    # Use -n 1 to read just one character, -r to prevent backslash escaping
    read -p "Are you absolutely sure you want to continue? (y/N): " -n 1 -r
    echo ""  # Add newline after user input
    
    # Check if user confirmed with 'y' or 'Y'
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Operation cancelled by user. No changes made."
        exit 0
    fi
    
    print_warning "Proceeding with tape deletion..."
    echo ""
fi

#==============================================================================
# SCRIPT EXECUTION
#==============================================================================

# Execute the constructed Python command
# The 'eval' command allows us to execute the dynamically built command string
print_info "Starting virtual tape management process..."
eval $CMD

# Capture the exit code from the Python script
PYTHON_EXIT_CODE=$?

# Provide final status message based on execution result
echo ""
if [[ $PYTHON_EXIT_CODE -eq 0 ]]; then
    if [[ "$LIST_ALL" == "true" ]]; then
        print_info "Virtual tape inventory completed successfully"
    else
        print_info "Virtual tape management completed successfully"
    fi
else
    print_error "Virtual tape management failed with exit code: $PYTHON_EXIT_CODE"
    exit $PYTHON_EXIT_CODE
fi