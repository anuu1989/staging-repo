# AWS Virtual Tape Manager - Simple Guide

A tool to manage and delete virtual tapes in AWS Storage Gateway.

## What Does This Do?

This tool helps you:
1. **See all your tapes** - Get a list of all virtual tapes
2. **Delete old tapes** - Remove tapes older than a certain age
3. **Delete specific tapes** - Remove tapes you choose

## Before You Start

You need:
- Python 3.6 or newer
- AWS credentials configured
- Permission to manage Storage Gateway tapes

### Install Requirements

```bash
pip3 install boto3
```

## How to Use

### 1. See All Your Tapes

```bash
python3 tape_cli.py --region us-east-1 --list
```

**Save the list to a file:**
```bash
python3 tape_cli.py --region us-east-1 --list --output my_tapes.txt
```

**See only archived tapes:**
```bash
python3 tape_cli.py --region us-east-1 --list --status ARCHIVED
```

### 2. Delete Old Tapes

**Test first (safe mode):**
```bash
python3 tape_cli.py --region us-east-1 --delete-expired --days 60
```

This shows what would be deleted without actually deleting anything.

**Actually delete:**
```bash
python3 tape_cli.py --region us-east-1 --delete-expired --days 60 --execute
```

⚠️ **Warning**: `--execute` actually deletes tapes. This cannot be undone!

### 3. Delete Specific Tapes

**Test first:**
```bash
python3 tape_cli.py --region us-east-1 --delete-tapes VTL001,VTL002,VTL003
```

**Actually delete:**
```bash
python3 tape_cli.py --region us-east-1 --delete-tapes VTL001,VTL002,VTL003 --execute
```

## Common Workflows

### Workflow 1: Clean Up Old Archived Tapes

```bash
# Step 1: See all archived tapes
python3 tape_cli.py --region us-east-1 --list --status ARCHIVED --output archived.txt

# Step 2: Review the list (open archived.txt)

# Step 3: Test deletion
python3 tape_cli.py --region us-east-1 --delete-expired --days 60

# Step 4: Actually delete
python3 tape_cli.py --region us-east-1 --delete-expired --days 60 --execute
```

### Workflow 2: Delete Specific Tapes

```bash
# Step 1: Get list of all tapes
python3 tape_cli.py --region us-east-1 --list --output all_tapes.txt

# Step 2: Edit all_tapes.txt - keep only tapes you want to delete

# Step 3: Delete them (replace with your tape names)
python3 tape_cli.py --region us-east-1 --delete-tapes VTL001,VTL002 --execute
```

## Important Notes

### Safety Features
- **Dry-run by default**: Commands show what would happen without actually doing it
- **Use --execute to actually delete**: You must add `--execute` to delete tapes
- **Deletion is permanent**: Deleted tapes cannot be recovered

### Tape Types
- **Active tapes** (AVAILABLE): Tapes in your gateway
- **Archived tapes** (ARCHIVED): Tapes in long-term storage (VTS)
- **Both can be deleted directly** - no need to retrieve archived tapes first

### AWS Regions
Common regions:
- `us-east-1` - US East (N. Virginia)
- `us-west-2` - US West (Oregon)
- `ap-southeast-2` - Asia Pacific (Sydney)
- `eu-west-1` - Europe (Ireland)

## Troubleshooting

### "Permission denied" error
- Check your AWS credentials
- Make sure you have Storage Gateway permissions

### "No tapes found"
- Check you're using the correct region
- Verify tapes exist in that region

### "Rate limit exceeded"
- The tool will automatically retry
- If it persists, wait a few minutes and try again

## Need Help?

1. Run with `--help` to see all options:
   ```bash
   python3 tape_cli.py --help
   ```

2. Check the detailed README.md for advanced options

3. Contact your AWS administrator

## Quick Reference

| Command | What it does |
|---------|-------------|
| `--list` | Show all tapes |
| `--list --status ARCHIVED` | Show only archived tapes |
| `--delete-expired --days 60` | Test deleting tapes older than 60 days |
| `--delete-expired --days 60 --execute` | Actually delete old tapes |
| `--delete-tapes VTL001,VTL002` | Test deleting specific tapes |
| `--delete-tapes VTL001,VTL002 --execute` | Actually delete specific tapes |
| `--output file.txt` | Save results to a file |

## Examples for ap-prod (2943 Archived Tapes)

```bash
# See all archived tapes
python3 tape_cli.py --region ap-southeast-2 --list --status ARCHIVED

# Delete all archived tapes older than 60 days (test first)
python3 tape_cli.py --region ap-southeast-2 --delete-expired --days 60

# If the test looks good, actually delete
python3 tape_cli.py --region ap-southeast-2 --delete-expired --days 60 --execute
```

Remember: Always test without `--execute` first!
