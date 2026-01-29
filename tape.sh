#!/bin/bash
#
# Simple wrapper for AWS Virtual Tape Manager
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_usage() {
    cat << EOF
AWS Virtual Tape Manager

USAGE:
    $0 <command> [options]

COMMANDS:
    list                List all tapes
    delete-old          Delete tapes older than specified days
    delete              Delete specific tapes

OPTIONS:
    --region REGION     AWS region (required)
    --profile PROFILE   AWS profile (optional)
    --days DAYS         Age threshold in days (default: 60)
    --status STATUS     Filter by status (ARCHIVED, AVAILABLE, RETRIEVED, etc.)
    --tapes LIST        Comma-separated tape list
    --output FILE       Save tape list to file
    --format FORMAT     Output format: arn (default) or barcode
    --execute           Actually delete (default is dry-run)

EXAMPLES:
    # List all tapes
    $0 list --region us-east-1

    # List archived tapes and save ARNs to file
    $0 list --region us-east-1 --status ARCHIVED --output archived_arns.txt

    # List archived tapes and save barcodes to file
    $0 list --region us-east-1 --status ARCHIVED --output archived_barcodes.txt --format barcode

    # List retrieved tapes (case-insensitive)
    $0 list --region us-east-1 --status retrieved

    # Delete old tapes (test)
    $0 delete-old --region us-east-1 --days 60

    # Delete old tapes (actual)
    $0 delete-old --region us-east-1 --days 60 --execute

    # Delete specific tapes
    $0 delete --region us-east-1 --tapes VTL001,VTL002 --execute

NOTE:
    - Output files contain tape ARNs (default) or barcodes (with --format barcode)
    - Format: one item per line with header comments
    - Status filter is case-insensitive (RETRIEVED = retrieved = Retrieved)
    - Use --output to save full list for scripting

EOF
}

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "python3 is required but not installed"
    exit 1
fi

# Check boto3
if ! python3 -c "import boto3" &> /dev/null; then
    print_error "boto3 is required. Install with: pip3 install boto3"
    exit 1
fi

# Parse command
COMMAND=$1
shift || { show_usage; exit 1; }

case $COMMAND in
    list)
        python3 tape_cli.py --list "$@"
        ;;
    delete-old)
        python3 tape_cli.py --delete-expired "$@"
        ;;
    delete)
        python3 tape_cli.py --delete-tapes "$@"
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac
