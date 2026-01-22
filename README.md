# AWS Virtual Tape Management Script

This comprehensive script helps you manage virtual tapes in AWS Storage Gateway, providing multiple operation modes for different use cases.

## Features

- **Multiple Operation Modes:**
  - List all virtual tapes with detailed inventory information
  - Delete expired virtual tapes based on configurable age threshold
  - Delete specific virtual tapes from a provided list
- **Flexible Input Methods:**
  - Command-line tape list specification
  - File-based tape list input
  - Age-based expiry criteria
- **Safety Features:**
  - Dry-run mode to preview operations without making changes
  - Status validation before deletion attempts
  - Comprehensive error handling and reporting
- **AWS Integration:**
  - Support for specific AWS profiles and regions
  - Multi-gateway support within a region
  - Governance retention policy handling

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
                "storagegateway:ListGateways",
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

#### 1. List All Virtual Tapes (Inventory Mode)

```bash
# Get comprehensive inventory of all virtual tapes
./cleanup_tapes.sh --region us-east-1 --list-all

# List tapes and save to file for later use
./cleanup_tapes.sh --region us-east-1 --list-all --output-file all_tapes.txt

# List tapes for specific AWS profile
./cleanup_tapes.sh --region us-west-2 --profile production --list-all --output-file prod_tapes.txt

# List tapes for specific Storage Gateway
./cleanup_tapes.sh --region us-east-1 --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-12345678 --list-all --output-file gateway_tapes.txt
```

#### 2. Delete Expired Tapes (Age-Based Cleanup)

```bash
# Dry run to see what expired tapes would be deleted (default behavior)
./cleanup_tapes.sh --region us-east-1 --expiry-days 60

# Actually delete expired tapes
./cleanup_tapes.sh --region us-east-1 --expiry-days 60 --execute

# Use specific AWS profile with custom expiry threshold
./cleanup_tapes.sh --region us-west-2 --profile production --expiry-days 90 --execute
```

#### 3. Delete Specific Tapes (Targeted Cleanup)

```bash
# Delete specific tapes by barcode/ARN (dry-run)
./cleanup_tapes.sh --region us-east-1 --delete-specific --tape-list "VTL001,VTL002,VTL003"

# Actually delete specific tapes
./cleanup_tapes.sh --region us-east-1 --delete-specific --tape-list "VTL001,VTL002" --execute

# Delete tapes listed in a file
./cleanup_tapes.sh --region us-east-1 --delete-specific --tape-file tapes_to_delete.txt --execute
```

#### 4. Workflow: List Then Delete

```bash
# Step 1: List all tapes and save to file
./cleanup_tapes.sh --region us-east-1 --list-all --output-file all_tapes.txt

# Step 2: Edit the file to keep only tapes you want to delete
# (Remove lines for tapes you want to keep)

# Step 3: Delete the selected tapes
./cleanup_tapes.sh --region us-east-1 --delete-specific --tape-file all_tapes.txt --execute
```

#### 5. Advanced Options

```bash
# Target specific Storage Gateway
./cleanup_tapes.sh --region us-east-1 --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-12345678 --execute

# Override governance retention (use with extreme caution)
./cleanup_tapes.sh --region us-east-1 --expiry-days 30 --execute --bypass-governance
```

### Using the Python Script Directly

#### List All Tapes
```bash
# Basic inventory
python3 delete_expired_virtual_tapes.py --region us-east-1 --list-all

# Save tape list to file
python3 delete_expired_virtual_tapes.py --region us-east-1 --list-all --output-file tapes.txt
```

#### Delete Expired Tapes
```bash
# Dry run (default)
python3 delete_expired_virtual_tapes.py --region us-east-1 --expiry-days 30

# Execute deletion
python3 delete_expired_virtual_tapes.py --region us-east-1 --expiry-days 30 --execute
```

#### Delete Specific Tapes
```bash
# From command line list
python3 delete_expired_virtual_tapes.py --region us-east-1 --delete-specific --tape-list "VTL001,VTL002" --execute

# From file
python3 delete_expired_virtual_tapes.py --region us-east-1 --delete-specific --tape-file tapes.txt --execute
```

## Command Line Options

### Common Options
| Option | Description | Required |
|--------|-------------|----------|
| `--region` | AWS region where Storage Gateway is located | Yes |
| `--profile` | AWS profile to use (uses default if not specified) | No |
| `--gateway-arn` | Specific Storage Gateway ARN to target | No |
| `--execute` | Actually perform operations (default is dry-run) | No |
| `--bypass-governance` | Bypass governance retention for deletion | No |

### Operation Mode Options (Mutually Exclusive)
| Option | Description | Default |
|--------|-------------|---------|
| `--list-all` | List all virtual tapes with detailed information | No |
| `--delete-expired` | Delete expired tapes based on age threshold | Yes |
| `--delete-specific` | Delete specific tapes from provided list | No |

### Age-Based Deletion Options
| Option | Description | Default |
|--------|-------------|---------|
| `--expiry-days` | Number of days after which tapes are considered expired | 30 |

### Specific Tape Deletion Options
| Option | Description | Required for --delete-specific |
|--------|-------------|-------------------------------|
| `--tape-list` | Comma-separated list of tape ARNs or barcodes | One of tape-list or tape-file |
| `--tape-file` | File containing list of tape ARNs or barcodes (one per line) | One of tape-list or tape-file |

### Output Options
| Option | Description | Used with |
|--------|-------------|-----------|
| `--output-file` | Save tape list to file (one barcode per line) | `--list-all` |

## Generated Tape List File Format

When using `--output-file` with `--list-all`, the generated file contains:

```
# Virtual Tape List
# Generated on: 2024-01-22 15:30:45
# Region: us-east-1
# Gateway: all gateways
# Total tapes: 25
#
# Format: One tape barcode per line
# Use this file with --delete-specific --tape-file
#

VTL001
VTL002
VTL003
TAPE004
VTL005
```

**File Creation Behavior:**
- **Always Created**: The output file is created regardless of whether tapes are found
- **Empty Results**: If no tapes are found, the file contains header comments and a "No tapes found" note
- **With Results**: If tapes are found, each tape barcode is listed on a separate line
- **Ready to Use**: The file format is immediately compatible with `--delete-specific --tape-file`

This file can be:
- **Edited** to remove tapes you want to keep
- **Used directly** with `--delete-specific --tape-file`
- **Shared** for review and approval processes
- **Archived** for audit and compliance purposes

## Manual Tape List File Format

When manually creating a tape list file for `--tape-file`, use this format:

```
# This is a comment - lines starting with # are ignored
VTL001
VTL002
arn:aws:storagegateway:us-east-1:123456789012:tape/sgw-12345678/VTL003
VTL004
# Another comment
VTL005
```

Tape identifiers can be either:
- **Barcodes**: Human-readable identifiers like `VTL001`, `TAPE001`
- **ARNs**: Full Amazon Resource Names like `arn:aws:storagegateway:us-east-1:123456789012:tape/sgw-12345678/VTL001`

## Safety Features

1. **Dry Run by Default**: All operations run in dry-run mode unless `--execute` is specified
2. **Operation Mode Validation**: Mutually exclusive operation modes prevent conflicting actions
3. **Status Checking**: Only deletes tapes in `AVAILABLE` or `ARCHIVED` status
4. **Input Validation**: Validates tape lists and file formats before processing
5. **Confirmation Prompts**: Shell script asks for confirmation before actual deletion
6. **Detailed Logging**: Comprehensive logging of all operations and decisions
7. **Error Handling**: Graceful handling of errors with detailed reporting
8. **Tape Verification**: Verifies tape existence before attempting operations

## Output Examples

### Inventory Mode Output
```
==============================================================
VIRTUAL TAPE INVENTORY
==============================================================
Total tapes found: 25
Total allocated size: 2,684,354,560 bytes (2.50 GB)
Total used size: 1,073,741,824 bytes (1.00 GB)

Tapes by status:
  AVAILABLE: 15 tapes
  ARCHIVED: 8 tapes
  IN_TRANSIT_TO_VTS: 2 tapes

Detailed tape information:
Barcode         Status       Age (days) Size (GB)  Used (GB) 
----------------------------------------------------------------------
VTL001          AVAILABLE    45         0.10       0.05      
VTL002          ARCHIVED     120        0.10       0.08      
VTL003          AVAILABLE    15         0.10       0.02      
```

### Expired Tape Cleanup Output
```
==================================================
EXPIRED TAPE CLEANUP RESULTS
==================================================
Total tapes found: 25
Expired tapes: 8
Would delete: 8
Failed deletions: 0

To actually delete the tapes, run with --execute flag
```

### Specific Tape Deletion Output
```
============================================================
SPECIFIC TAPE DELETION RESULTS
============================================================
Tapes requested for deletion: 3
Tapes found: 2
Tapes not found: 1
Would delete: 2
Failed deletions: 0

Detailed processing results:
Identifier           Barcode         Status       Action              
---------------------------------------------------------------------------
VTL001              VTL001          AVAILABLE    would_delete        
VTL002              VTL002          ARCHIVED     would_delete        

Tapes not found:
  - VTL999
```

## Use Cases

### 1. Regular Maintenance
- **Inventory Audits**: Use `--list-all` to generate comprehensive tape inventories
- **Automated Cleanup**: Schedule expired tape deletion with `--delete-expired`
- **Compliance Reporting**: Generate reports showing tape usage and retention
- **Tape List Generation**: Save tape lists to files for approval workflows

### 2. Targeted Operations
- **Emergency Cleanup**: Remove specific problematic tapes with `--delete-specific`
- **Migration Support**: Clean up tapes during Storage Gateway migrations
- **Cost Optimization**: Remove unused or redundant tapes to reduce storage costs
- **Selective Deletion**: Use generated tape lists to delete only approved tapes

### 3. Operational Workflows
- **Pre-Migration**: List all tapes before system changes
- **Post-Incident**: Clean up tapes after backup/restore operations
- **Capacity Planning**: Analyze tape usage patterns and storage requirements
- **Approval Process**: Generate tape lists for management review before deletion

### 4. Common Workflow Pattern
```bash
# Step 1: Generate inventory and save to file
./cleanup_tapes.sh --region us-east-1 --list-all --output-file inventory.txt

# Step 2: Review and edit the file (remove tapes to keep)
# Edit inventory.txt to contain only tapes you want to delete

# Step 3: Test deletion with dry-run
./cleanup_tapes.sh --region us-east-1 --delete-specific --tape-file inventory.txt

# Step 4: Execute actual deletion
./cleanup_tapes.sh --region us-east-1 --delete-specific --tape-file inventory.txt --execute
```

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure your AWS credentials have the required Storage Gateway permissions
2. **Region Not Found**: Verify the region name is correct and Storage Gateway exists in that region
3. **No Virtual Tapes Found**: The region may not contain any virtual tapes or Storage Gateways
4. **Tape Not Deletable**: Some tapes may be in use or have retention policies preventing deletion
5. **File Not Found**: When using `--tape-file`, ensure the file path is correct and accessible
6. **Invalid Tape Identifier**: Verify tape barcodes/ARNs are correct and exist in the system
7. **Archived Tapes Cannot Be Deleted**: Tapes with ARCHIVED status are in VTS and cannot be deleted directly
8. **Limited Metadata for Archived Tapes**: Archived tapes have reduced information available (no creation dates)

### Archived Tapes (VTS) Limitations

**What are Archived Tapes?**
- Tapes with status "ARCHIVED" are stored in AWS Virtual Tape Shelf (VTS)
- These tapes are moved to long-term storage for cost optimization
- Archived tapes cannot be accessed via regular Storage Gateway APIs

**Script Behavior with Archived Tapes:**
- **Inventory**: Shows archived tapes with available basic information
- **Deletion**: Cannot delete archived tapes directly (they must be retrieved first)
- **Metadata**: Limited information available (no creation dates, detailed status)

**To Delete Archived Tapes:**
1. Use AWS Console or CLI to retrieve tapes from VTS back to the gateway
2. Wait for retrieval to complete (can take several hours)
3. Once retrieved, tapes can be deleted using this script

### API Requirements Note

The AWS Storage Gateway APIs have specific requirements and limitations:

**Regular vs Archived Tapes:**
- `list_tapes` API lists all tapes (both active and archived) across all gateways in a region
- `describe_tapes` API only works for **active tapes** and requires a `GatewayARN` parameter
- **Archived tapes** (status: ARCHIVED) are stored in Virtual Tape Shelf (VTS) and cannot be queried via `describe_tapes`

**How This Script Handles Different Tape States:**
1. **Active Tapes**: Uses gateway discovery to find the correct gateway, then calls `describe_tapes`
2. **Archived Tapes**: Uses basic information from `list_tapes` since detailed info is not available
3. **Mixed Environments**: Automatically detects and handles both types appropriately

**Important Notes for Archived Tapes:**
- Archived tapes have limited metadata available (no creation dates, detailed status, etc.)
- Archived tapes **cannot be deleted** via the regular Storage Gateway APIs
- To delete archived tapes, they must first be retrieved from VTS back to the gateway
- The script will identify archived tapes but cannot delete them directly

This approach ensures compatibility with all tape states while providing the best available information for each type.

### Debug Steps

1. **Start with Inventory**: Always run `--list-all` first to understand your tape landscape
2. **Use Dry-Run**: Test operations with dry-run mode before actual execution
3. **Check Logs**: Review detailed logs for specific error messages
4. **Verify Permissions**: Ensure IAM permissions include all required Storage Gateway actions (ListTapes, DescribeTapes, DeleteTape)
5. **Test Connectivity**: Verify AWS CLI access and region connectivity
6. **Validate Region**: Confirm the region contains Storage Gateway resources with virtual tapes

## Important Notes

- **Operation Modes**: Only one operation mode can be used at a time (list-all, delete-expired, or delete-specific)
- **Tape Identification**: The system accepts both tape barcodes and full ARNs as identifiers
- **Status Requirements**: Virtual tapes must be in `AVAILABLE` or `ARCHIVED` status to be deletable
- **Governance Retention**: Some tapes may have governance policies preventing deletion without the bypass flag
- **Dry-Run Safety**: Always test with dry-run first to understand what operations will be performed
- **File Format**: Tape list files support comments (lines starting with #) and ignore empty lines
- **AWS Limits**: Be aware of AWS API rate limits when processing large numbers of tapes
- **Backup Considerations**: Ensure you have proper backups before deleting any tapes
- **Cost Impact**: Consider the cost implications of tape deletion and storage optimization

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review AWS Storage Gateway documentation
3. Verify IAM permissions and AWS CLI configuration
4. Test with dry-run mode to identify issues
5. Contact AWS support for Storage Gateway-specific problems