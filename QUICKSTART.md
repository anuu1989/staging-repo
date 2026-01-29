# Quick Start Guide

Get started with AWS Virtual Tape Manager in 5 minutes.

## 1. Install (30 seconds)

```bash
pip3 install boto3
chmod +x tape.sh
```

## 2. Test Connection (10 seconds)

```bash
./tape.sh list --region us-east-1
```

If this works, you're ready to go!

## 3. Common Tasks

### See All Your Tapes
```bash
./tape.sh list --region us-east-1
```

### See Only Archived Tapes
```bash
./tape.sh list --region us-east-1 --status ARCHIVED
```

### Delete Old Tapes (Safe Test)
```bash
./tape.sh delete-old --region us-east-1 --days 60
```

### Delete Old Tapes (Actually Delete)
```bash
./tape.sh delete-old --region us-east-1 --days 60 --execute
```

### Delete Specific Tapes
```bash
./tape.sh delete --region us-east-1 --tapes VTL001,VTL002 --execute
```

## 4. For ap-prod (2943 Archived Tapes)

```bash
# See what you have
./tape.sh list --region ap-southeast-2 --status ARCHIVED

# Test deletion
./tape.sh delete-old --region ap-southeast-2 --days 60

# If test looks good, execute
./tape.sh delete-old --region ap-southeast-2 --days 60 --execute
```

## Important Notes

⚠️ **Always test first** - Commands without `--execute` are safe (dry-run)

⚠️ **Deletion is permanent** - Deleted tapes cannot be recovered

✅ **Archived tapes** - Can be deleted directly (no retrieval needed)

## Need Help?

- **Simple guide**: See `README_SIMPLE.md`
- **Technical docs**: See `README.md`
- **Command help**: Run `./tape.sh help`

## Troubleshooting

**"Permission denied"**
```bash
chmod +x tape.sh
```

**"boto3 not found"**
```bash
pip3 install boto3
```

**"AWS credentials not found"**
```bash
aws configure
# or
export AWS_PROFILE=your-profile
```

That's it! You're ready to manage your tapes.
