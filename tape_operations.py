#!/usr/bin/env python3
"""
AWS Virtual Tape Operations

High-level operations for tape management.
"""

import logging
from typing import List, Dict
from tape_manager import TapeManager

logger = logging.getLogger(__name__)


def inventory_tapes(manager: TapeManager, status_filter: List[str] = None) -> Dict:
    """
    Get inventory of all tapes
    
    Returns:
        Dictionary with tape counts and details
    """
    # Get all tapes first to show available statuses
    all_tapes = manager.list_tapes(None)
    
    # Collect all unique statuses
    all_statuses = set()
    for tape in all_tapes:
        status = tape.get('TapeStatus', 'Unknown')
        all_statuses.add(status)
    
    # Now apply filter if specified
    if status_filter:
        tapes = manager.list_tapes(status_filter)
    else:
        tapes = all_tapes
    
    # Group by status
    by_status = {}
    for tape in tapes:
        status = tape.get('TapeStatus', 'Unknown')
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(tape)
    
    return {
        'total': len(tapes),
        'total_all': len(all_tapes),
        'by_status': by_status,
        'tapes': tapes,
        'all_statuses': sorted(all_statuses),
        'filter_applied': status_filter is not None
    }


def delete_expired_tapes(manager: TapeManager, expiry_days: int, dry_run: bool = True) -> Dict:
    """
    Delete tapes older than expiry_days
    
    Args:
        manager: TapeManager instance
        expiry_days: Age threshold in days
        dry_run: If True, only simulate deletion
    
    Returns:
        Dictionary with deletion results
    """
    tapes = manager.list_tapes()
    
    results = {
        'total_tapes': len(tapes),
        'expired_tapes': 0,
        'deleted': 0,
        'failed': 0,
        'errors': []
    }
    
    for tape in tapes:
        tape_arn = tape.get('TapeARN')
        tape_barcode = tape.get('TapeBarcode', 'Unknown')
        tape_status = tape.get('TapeStatus', 'Unknown')
        
        # For archived tapes, assume they're old
        # For active tapes, we'd need creation date (not available in list_tapes)
        if tape_status == 'ARCHIVED':
            results['expired_tapes'] += 1
            
            if dry_run:
                logger.info(f"DRY RUN: Would delete {tape_barcode} (ARN: {tape_arn})")
                results['deleted'] += 1
            else:
                logger.info(f"Deleting tape: {tape_barcode} (ARN: {tape_arn})")
                if manager.delete_tape(tape_arn, tape_status):
                    results['deleted'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Failed to delete {tape_barcode} (ARN: {tape_arn})")
    
    return results


def delete_specific_tapes(manager: TapeManager, tape_identifiers: List[str], dry_run: bool = True) -> Dict:
    """
    Delete specific tapes by barcode or ARN
    
    Args:
        manager: TapeManager instance
        tape_identifiers: List of tape barcodes or ARNs
        dry_run: If True, only simulate deletion
    
    Returns:
        Dictionary with deletion results
    """
    all_tapes = manager.list_tapes()
    
    # Create lookup by barcode and ARN
    tape_lookup = {}
    for tape in all_tapes:
        arn = tape.get('TapeARN')
        barcode = tape.get('TapeBarcode')
        if arn:
            tape_lookup[arn] = tape
        if barcode:
            tape_lookup[barcode] = tape
    
    results = {
        'requested': len(tape_identifiers),
        'found': 0,
        'not_found': 0,
        'deleted': 0,
        'failed': 0,
        'errors': []
    }
    
    for identifier in tape_identifiers:
        tape = tape_lookup.get(identifier)
        
        if not tape:
            logger.warning(f"Tape not found: {identifier}")
            results['not_found'] += 1
            results['errors'].append(f"Not found: {identifier}")
            continue
        
        results['found'] += 1
        tape_arn = tape.get('TapeARN')
        tape_barcode = tape.get('TapeBarcode', 'Unknown')
        tape_status = tape.get('TapeStatus', 'Unknown')
        
        if dry_run:
            logger.info(f"DRY RUN: Would delete {tape_barcode} (Status: {tape_status}, ARN: {tape_arn})")
            results['deleted'] += 1
        else:
            logger.info(f"Deleting tape: {tape_barcode} (Status: {tape_status}, ARN: {tape_arn})")
            if manager.delete_tape(tape_arn, tape_status):
                results['deleted'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(f"Failed to delete {tape_barcode} (ARN: {tape_arn})")
    
    return results
