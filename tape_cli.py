#!/usr/bin/env python3
"""
AWS Virtual Tape CLI

Simple command-line interface for tape management.
"""

import argparse
import logging
import sys
from tape_manager import TapeManager
from tape_operations import inventory_tapes, delete_expired_tapes, delete_specific_tapes

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='AWS Virtual Tape Management Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all tapes
  python3 tape_cli.py --region us-east-1 --list

  # List only archived tapes
  python3 tape_cli.py --region us-east-1 --list --status ARCHIVED

  # Delete expired tapes (dry-run)
  python3 tape_cli.py --region us-east-1 --delete-expired --days 60

  # Delete expired tapes (actual)
  python3 tape_cli.py --region us-east-1 --delete-expired --days 60 --execute

  # Delete specific tapes
  python3 tape_cli.py --region us-east-1 --delete-tapes VTL001,VTL002 --execute
        """
    )
    
    # Required
    parser.add_argument('--region', required=True, help='AWS region')
    parser.add_argument('--profile', help='AWS profile (optional)')
    
    # Operations (mutually exclusive)
    ops = parser.add_mutually_exclusive_group(required=True)
    ops.add_argument('--list', action='store_true', help='List all tapes')
    ops.add_argument('--delete-expired', action='store_true', help='Delete expired tapes')
    ops.add_argument('--delete-tapes', help='Delete specific tapes (comma-separated)')
    
    # Options
    parser.add_argument('--status', help='Filter by status (e.g., ARCHIVED,AVAILABLE)')
    parser.add_argument('--days', type=int, default=60, help='Expiry threshold in days (default: 60)')
    parser.add_argument('--execute', action='store_true', help='Actually delete (default is dry-run)')
    parser.add_argument('--output', help='Save tape list to file')
    
    args = parser.parse_args()
    
    # Initialize manager
    try:
        manager = TapeManager(args.region, args.profile)
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        sys.exit(1)
    
    # Parse status filter
    status_filter = None
    if args.status:
        status_filter = [s.strip().upper() for s in args.status.split(',')]
    
    # Execute operation
    if args.list:
        # Inventory
        results = inventory_tapes(manager, status_filter)
        
        print("\n" + "="*60)
        print("TAPE INVENTORY")
        print("="*60)
        
        # Show all available statuses in the system
        if results.get('all_statuses'):
            print(f"\nAvailable statuses in system: {', '.join(results['all_statuses'])}")
            print(f"(Status filter is case-insensitive)")
        
        # Show filter info
        if results['filter_applied']:
            print(f"\nFilter applied: {', '.join(status_filter)}")
            print(f"Total tapes (unfiltered): {results['total_all']}")
            print(f"Matching tapes (filtered): {results['total']}")
        else:
            print(f"\nTotal tapes: {results['total']}")
        
        if results['by_status']:
            print("\nBreakdown by status:")
            for status, tapes in sorted(results['by_status'].items()):
                print(f"  {status}: {len(tapes)}")
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                f.write("# Tape Inventory\n")
                if results['filter_applied']:
                    f.write(f"# Filter: {', '.join(status_filter)}\n")
                f.write(f"# Total: {results['total']}\n\n")
                for tape in results['tapes']:
                    f.write(f"{tape.get('TapeBarcode', 'Unknown')}\n")
            print(f"\nSaved to: {args.output}")
    
    elif args.delete_expired:
        # Delete expired
        dry_run = not args.execute
        results = delete_expired_tapes(manager, args.days, dry_run)
        
        print("\n" + "="*60)
        print("DELETE EXPIRED TAPES")
        print("="*60)
        print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
        print(f"Total tapes: {results['total_tapes']}")
        print(f"Expired tapes: {results['expired_tapes']}")
        print(f"{'Would delete' if dry_run else 'Deleted'}: {results['deleted']}")
        print(f"Failed: {results['failed']}")
        
        if results['errors']:
            print("\nErrors:")
            for error in results['errors']:
                print(f"  - {error}")
    
    elif args.delete_tapes:
        # Delete specific
        tape_list = [t.strip() for t in args.delete_tapes.split(',')]
        dry_run = not args.execute
        results = delete_specific_tapes(manager, tape_list, dry_run)
        
        print("\n" + "="*60)
        print("DELETE SPECIFIC TAPES")
        print("="*60)
        print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
        print(f"Requested: {results['requested']}")
        print(f"Found: {results['found']}")
        print(f"Not found: {results['not_found']}")
        print(f"{'Would delete' if dry_run else 'Deleted'}: {results['deleted']}")
        print(f"Failed: {results['failed']}")
        
        if results['errors']:
            print("\nErrors:")
            for error in results['errors']:
                print(f"  - {error}")


if __name__ == '__main__':
    main()
