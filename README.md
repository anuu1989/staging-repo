# AWS Virtual Tape Manager

Simple, modular tool for managing AWS Storage Gateway virtual tapes.

## Features

- ✅ **List tapes** - Inventory all virtual tapes with status filtering
- ✅ **Delete expired tapes** - Remove tapes older than specified days
- ✅ **Delete specific tapes** - Remove chosen tapes by barcode/ARN
- ✅ **Direct archive deletion** - Delete archived tapes without retrieval
- ✅ **Dry-run mode** - Test operations safely before executing
- ✅ **Auto-retry** - Handles AWS rate limits automatically

## Quick Start

### Installation

```bash
# Install dependencies
pip3 install boto3

# Make scripts executable
chmod +x tape.sh
```

### Basic Usage

```bash
# List all tapes
./tape.sh list --region us-east-1

# Delete old tapes (dry-run)
./tape.sh delete-old --region us-east-1 --days 60

# Delete old tapes (execute)
./tape.sh delete-old --region us-east-1 --days 60 --execute

# Delete specific tapes
./tape.sh delete --region us-east-1 --tapes VTL001,VTL002 --execute
```

## Architecture

The tool is modular and consists of:

```
tape_manager.py      - Core AWS API interactions
tape_operations.py   - High-level operations (inventory, delete)
tape_cli.py          - Command-line interface
tape.sh              - Simple shell wrapper
```

### Module Overview

**tape_manager.py**
- Handles AWS Storage Gateway API calls
- Manages authentication and retries
- Provides low-level tape operations

**tape_operations.py**
- Implements business logic
- Inventory, delete-expired, delete-specific operations
- Returns structured results

**tape_cli.py**
- Command-line argument parsing
- User-friendly output formatting
- Main entry point

**tape.sh**
- Simplified wrapper script
- Easy-to-remember commands
- Prerequisite checking

## Detailed Usage

### 1. Inventory Operations

**List all tapes:**
```bash
python3 tape_cli.py --region us-east-1 --list
```

**Filter by status:**
```bash
python3 tape_cli.py --region us-east-1 --list --status ARCHIVED
python3 tape_cli.py --region us-east-1 --list --status AVAILABLE,RETRIEVED
```

**Save to file:**
```bash
python3 tape_cli.py --region us-east-1 --list --output tapes.txt
```

### 2. Delete Expired Tapes

**Dry-run (safe):**
```bash
python3 tape_cli.py --region us-east-1 --delete-expired --days 60
```

**Execute deletion:**
```bash
python3 tape_cli.py --region us-east-1 --delete-expired --days 60 --execute
```

### 3. Delete Specific Tapes

**By barcode:**
```bash
python3 tape_cli.py --region us-east-1 --delete-tapes VTL001,VTL002,VTL003
```

**Execute deletion:**
```bash
python3 tape_cli.py --region us-east-1 --delete-tapes VTL001,VTL002 --execute
```

## AWS Permissions Required

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "storagegateway:ListGateways",
                "storagegateway:ListTapes",
                "storagegateway:DescribeTapes",
                "storagegateway:DeleteTape",
                "storagegateway:DeleteTapeArchive"
            ],
            "Resource": "*"
        }
    ]
}
```

## How It Works

### Tape Deletion Logic

The tool automatically handles both active and archived tapes:

1. **Active tapes** (AVAILABLE, RETRIEVED):
   - Uses `DeleteTape` API
   - Requires gateway ARN (auto-discovered)

2. **Archived tapes** (ARCHIVED):
   - Uses `DeleteTapeArchive` API
   - Direct deletion from VTS (no retrieval needed)

### Error Handling

- Automatic retry with exponential backoff for rate limits
- Graceful handling of missing tapes
- Detailed error reporting
- Non-critical errors don't stop batch operations

## Common Workflows

### Workflow 1: Clean Up Archived Tapes

```bash
# Step 1: See what you have
./tape.sh list --region ap-southeast-2 --status ARCHIVED

# Step 2: Test deletion
./tape.sh delete-old --region ap-southeast-2 --days 60

# Step 3: Execute if results look good
./tape.sh delete-old --region ap-southeast-2 --days 60 --execute
```

### Workflow 2: Selective Deletion

```bash
# Step 1: Get full inventory
./tape.sh list --region us-east-1 --output all_tapes.txt

# Step 2: Review and select tapes to delete

# Step 3: Delete selected tapes
./tape.sh delete --region us-east-1 --tapes VTL001,VTL002,VTL003 --execute
```

## Configuration

### AWS Profile

Use a specific AWS profile:
```bash
python3 tape_cli.py --region us-east-1 --profile production --list
```

### Logging

Adjust log level by editing the scripts:
```python
logging.basicConfig(level=logging.DEBUG)  # More verbose
logging.basicConfig(level=logging.WARNING)  # Less verbose
```

## Troubleshooting

### Common Issues

**"Failed to connect to AWS"**
- Check AWS credentials: `aws sts get-caller-identity`
- Verify region is correct
- Ensure IAM permissions are configured

**"Rate limit exceeded"**
- Tool automatically retries
- If persistent, reduce batch size or wait

**"Tape not found"**
- Verify tape barcode/ARN is correct
- Check you're using the correct region
- Tape may have been already deleted

### Debug Mode

Enable detailed logging:
```bash
# Edit tape_cli.py and change:
logging.basicConfig(level=logging.DEBUG)
```

## Performance

- **List operations**: ~1 second per 100 tapes
- **Delete operations**: ~1 second per tape
- **Rate limits**: Automatically handled with retry
- **Batch processing**: Processes tapes sequentially for reliability

## Safety Features

1. **Dry-run by default** - Must explicitly use `--execute`
2. **Clear output** - Shows exactly what will be deleted
3. **Error isolation** - One failure doesn't stop the batch
4. **Detailed logging** - Full audit trail of operations

## Limitations

- Cannot retrieve creation dates for archived tapes
- Assumes archived tapes are old (safe for deletion)
- Sequential processing (not parallel)
- No undo functionality (AWS limitation)

## For ap-prod Environment (2943 Archived Tapes)

```bash
# Quick inventory
./tape.sh list --region ap-southeast-2 --status ARCHIVED

# Delete all archived tapes (test first!)
./tape.sh delete-old --region ap-southeast-2 --days 1

# If test looks good, execute
./tape.sh delete-old --region ap-southeast-2 --days 1 --execute
```

## Support

- See `README_SIMPLE.md` for non-technical guide
- Run `./tape.sh help` for quick reference
- Check AWS Storage Gateway documentation for API details

## License

Internal tool for AWS Storage Gateway management.
