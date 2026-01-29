# Migration Guide: Old Scripts → New Modular Tool

## What Changed?

The tool has been refactored into a cleaner, more maintainable structure.

### Old Structure
```
delete_expired_virtual_tapes.py  (1500+ lines, monolithic)
cleanup_tapes.sh                 (700+ lines, complex)
README.md                        (500+ lines, overwhelming)
```

### New Structure
```
tape_manager.py       (150 lines) - Core AWS operations
tape_operations.py    (120 lines) - Business logic
tape_cli.py           (100 lines) - CLI interface
tape.sh               (70 lines)  - Simple wrapper
README.md             (200 lines) - Technical docs
README_SIMPLE.md      (150 lines) - User-friendly guide
```

## Command Migration

### List Operations

**Old:**
```bash
./cleanup_tapes.sh --region us-east-1 --list-all
./cleanup_tapes.sh --region us-east-1 --list-all --status-filter ARCHIVED
./cleanup_tapes.sh --region us-east-1 --list-all --output-file tapes.txt
```

**New:**
```bash
./tape.sh list --region us-east-1
./tape.sh list --region us-east-1 --status ARCHIVED
./tape.sh list --region us-east-1 --output tapes.txt
```

### Delete Expired

**Old:**
```bash
./cleanup_tapes.sh --region us-east-1 --expiry-days 60
./cleanup_tapes.sh --region us-east-1 --expiry-days 60 --execute
```

**New:**
```bash
./tape.sh delete-old --region us-east-1 --days 60
./tape.sh delete-old --region us-east-1 --days 60 --execute
```

### Delete Specific

**Old:**
```bash
./cleanup_tapes.sh --region us-east-1 --delete-specific --tape-list "VTL001,VTL002"
./cleanup_tapes.sh --region us-east-1 --delete-specific --tape-file tapes.txt --execute
```

**New:**
```bash
./tape.sh delete --region us-east-1 --tapes VTL001,VTL002
# For file input, read file and pass to --tapes
./tape.sh delete --region us-east-1 --tapes $(cat tapes.txt | tr '\n' ',') --execute
```

## What Was Removed?

### Removed Features
- ❌ `--retrieve-archived` - No longer needed (direct deletion works)
- ❌ `--limit` - Simplified to focus on core operations
- ❌ `--gateway-arn` - Auto-discovered when needed
- ❌ `--bypass-governance` - Simplified permissions model

### Why Removed?
1. **Retrieval** - DeleteTapeArchive API makes retrieval unnecessary
2. **Complexity** - Removed rarely-used options
3. **Auto-discovery** - Gateway ARN found automatically
4. **Simplification** - Focus on core use cases

## What Stayed the Same?

### Core Functionality
- ✅ List all tapes
- ✅ Delete expired tapes
- ✅ Delete specific tapes
- ✅ Dry-run mode
- ✅ Status filtering
- ✅ Output to file
- ✅ Direct deletion of archived tapes

### Behavior
- ✅ Dry-run by default
- ✅ Automatic retry on rate limits
- ✅ Detailed error reporting
- ✅ Same AWS permissions required

## Benefits of New Structure

### For Developers
- **Modular** - Easy to understand and modify
- **Testable** - Each module can be tested independently
- **Maintainable** - Clear separation of concerns
- **Extensible** - Easy to add new features

### For Users
- **Simpler** - Fewer options to remember
- **Clearer** - Better documentation
- **Faster** - Streamlined operations
- **Safer** - Same safety features, less complexity

## Migration Checklist

- [ ] Install new scripts
- [ ] Test with `--list` command
- [ ] Test delete operations in dry-run mode
- [ ] Update any automation scripts
- [ ] Archive old scripts
- [ ] Update documentation references

## Backward Compatibility

The old scripts still work but are deprecated. Key differences:

| Feature | Old | New | Notes |
|---------|-----|-----|-------|
| List tapes | `--list-all` | `--list` | Simpler name |
| Delete old | `--delete-expired --expiry-days` | `--delete-old --days` | Clearer naming |
| Delete specific | `--delete-specific --tape-list` | `--delete-tapes` | Simplified |
| Status filter | `--status-filter` | `--status` | Shorter |
| Output file | `--output-file` | `--output` | Shorter |

## Troubleshooting Migration

### "Command not found"
- Old: `./cleanup_tapes.sh`
- New: `./tape.sh`

### "Unknown option"
- Check command migration table above
- Run `./tape.sh help` for current options

### "Different output format"
- New tool has cleaner output
- Functionality is the same
- File output format unchanged

## Rollback Plan

If you need to use old scripts:
```bash
# Old scripts are still present
./cleanup_tapes.sh --help
python3 delete_expired_virtual_tapes.py --help
```

## Questions?

- See `README.md` for technical details
- See `README_SIMPLE.md` for user guide
- Check old scripts for reference
