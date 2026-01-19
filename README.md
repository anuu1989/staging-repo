# AWS Virtual Tape Cleanup Script

This script helps you delete expired virtual tapes from AWS Storage Gateway in a specific AWS account.

## Features

- List and identify expired virtual tapes based on age
- Dry-run mode to preview what would be deleted
- Support for specific AWS profiles and regions
- Configurable expiry threshold
- Safe deletion with status checks
- Detailed logging and error handling

## Prerequisites

- Python 3.6+
- AWS CLI configured with appropriate credentials
- boto3 Python library
- Appropriate IAM permissions for Storage Gateway operations

## Required IAM Permissions

Your AWS credentials need the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "storagegateway:ListTapes",
                "storagegateway:DescribeTapes",
                "storagegateway:DeleteTape"
            ],
            "Resource": "*"
        }
    ]
}
```

## Installation

1. Clone or download the script files
2. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

## Usage

### Using the Shell Script (Recommended)

```bash
# Dry run to see what would be deleted (default behavior)
./cleanup_tapes.sh --region us-east-1 --expiry-days 60

# Actually delete expired tapes
./cleanup_tapes.sh --region us-east-1 --expiry-days 60 --execute

# Use specific AWS profile
./cleanup_tapes.sh --region us-west-2 --profile production --expiry-days 90 --execute

# Target specific Storage Gateway
./cleanup_tapes.sh --region us-east-1 --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-12345678 --execute
```

### Using the Python Script Directly

```bash
# Dry run (default)
python3 delete_expired_virtual_tapes.py --region us-east-1 --expiry-days 30

# Execute deletion
python3 delete_expired_virtual_tapes.py --region us-east-1 --expiry-days 30 --execute

# Use specific profile
python3 delete_expired_virtual_tapes.py --region us-east-1 --profile myprofile --expiry-days 60 --execute
```

## Command Line Options

| Option | Description | Required |
|--------|-------------|----------|
| `--region` | AWS region where Storage Gateway is located | Yes |
| `--profile` | AWS profile to use (uses default if not specified) | No |
| `--expiry-days` | Number of days after which tapes are considered expired (default: 30) | No |
| `--gateway-arn` | Specific Storage Gateway ARN to target | No |
| `--execute` | Actually delete tapes (default is dry-run) | No |
| `--bypass-governance` | Bypass governance retention for deletion | No |

## Safety Features

1. **Dry Run by Default**: The script runs in dry-run mode unless `--execute` is specified
2. **Status Checking**: Only deletes tapes in `AVAILABLE` or `ARCHIVED` status
3. **Confirmation Prompt**: Shell script asks for confirmation before actual deletion
4. **Detailed Logging**: Comprehensive logging of all operations
5. **Error Handling**: Graceful handling of errors with detailed reporting

## Output

The script provides detailed output including:
- Total number of tapes found
- Number of expired tapes identified
- Number of tapes deleted (or would be deleted in dry-run)
- Any errors encountered during the process

## Example Output

```
2024-01-17 10:30:15,123 - INFO - Initialized Storage Gateway client for region: us-east-1
2024-01-17 10:30:16,456 - INFO - Found 25 virtual tapes
2024-01-17 10:30:17,789 - INFO - Found 8 expired tapes (older than 60 days)
2024-01-17 10:30:18,012 - INFO - Processing tape: VTL001 (Status: AVAILABLE)
2024-01-17 10:30:18,345 - INFO - DRY RUN: Would delete tape VTL001 (arn:aws:storagegateway:...)

==================================================
VIRTUAL TAPE CLEANUP RESULTS
==================================================
Total tapes found: 25
Expired tapes: 8
Would delete: 8
Failed deletions: 0
```

## Troubleshooting

1. **Permission Denied**: Ensure your AWS credentials have the required Storage Gateway permissions
2. **Region Not Found**: Verify the region name is correct and Storage Gateway exists in that region
3. **Tape Not Deletable**: Some tapes may be in use or have retention policies preventing deletion

## Important Notes

- Virtual tapes that are currently being used by applications cannot be deleted
- Tapes with governance retention may require the `--bypass-governance` flag
- Always test with dry-run first to understand what will be deleted
- Consider your backup and retention policies before deleting tapes

## Support

For issues or questions, check the AWS Storage Gateway documentation or AWS support resources.