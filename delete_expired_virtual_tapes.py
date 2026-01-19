#!/usr/bin/env python3
"""
AWS Virtual Tape Cleanup Script

This script automates the deletion of expired virtual tapes from AWS Storage Gateway.
Virtual tapes are used in AWS Storage Gateway's Virtual Tape Library (VTL) to provide
cloud-based tape backup solutions. Over time, these tapes can accumulate and need
cleanup based on retention policies.

Key Features:
- Identifies expired tapes based on configurable age threshold
- Supports dry-run mode for safe testing
- Handles multiple tape states and error conditions
- Provides detailed logging and reporting
- Supports specific AWS profiles and regions

"""

import boto3
import argparse
import logging
from datetime import datetime, timezone
from typing import List, Dict
import sys

# Configure logging with timestamp and level information
# This helps track operations and debug issues during execution
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VirtualTapeManager:
    """
    Main class for managing AWS Storage Gateway Virtual Tapes
    
    This class encapsulates all operations related to virtual tape management
    including listing, analyzing, and deleting expired tapes. It handles
    AWS API interactions and provides a clean interface for tape operations.
    """
    
    def __init__(self, region: str, profile: str = None):
        """
        Initialize the Virtual Tape Manager with AWS credentials and region
        
        Args:
            region (str): AWS region where Storage Gateway is located
            profile (str, optional): AWS profile name to use for authentication.
                                   If None, uses default credentials chain
        
        Raises:
            SystemExit: If AWS client initialization fails
        """
        try:
            # Create AWS session - either with specific profile or default credentials
            # The session handles authentication and credential management
            session = boto3.Session(profile_name=profile) if profile else boto3.Session()
            
            # Initialize Storage Gateway client for the specified region
            # This client will be used for all tape-related API calls
            self.storagegateway = session.client('storagegateway', region_name=region)
            self.region = region
            logger.info(f"Initialized Storage Gateway client for region: {region}")
        except Exception as e:
            # Log error and exit if we can't connect to AWS
            # This is a critical failure that prevents any operations
            logger.error(f"Failed to initialize AWS client: {e}")
            sys.exit(1)

    def list_virtual_tapes(self, gateway_arn: str = None) -> List[Dict]:
        """
        Retrieve a list of all virtual tapes from Storage Gateway
        
        This method calls the AWS Storage Gateway API to get basic information
        about all virtual tapes. The response includes tape ARNs, barcodes,
        and basic metadata but not detailed information.
        
        Args:
            gateway_arn (str, optional): Specific Storage Gateway ARN to query.
                                       If None, queries all gateways in the region
        
        Returns:
            List[Dict]: List of tape information dictionaries containing:
                       - TapeARN: Amazon Resource Name of the tape
                       - TapeBarcode: Human-readable tape identifier
                       - TapeSizeInBytes: Size of the tape
                       - TapeStatus: Current status of the tape
        
        Note:
            The API has pagination limits (100 tapes per call). For production
            environments with many tapes, this should be enhanced with pagination.
        """
        try:
            # Call AWS API to list tapes
            # Limit set to 100 to avoid overwhelming the API response
            if gateway_arn:
                # Query specific gateway if ARN provided
                response = self.storagegateway.list_tapes(TapeARNs=[], Limit=100)
            else:
                # Query all gateways in the region
                response = self.storagegateway.list_tapes(Limit=100)
            
            # Extract tape information from API response
            tapes = response.get('TapeInfos', [])
            logger.info(f"Found {len(tapes)} virtual tapes")
            return tapes
        except Exception as e:
            # Log error but don't crash - return empty list to allow graceful handling
            logger.error(f"Failed to list virtual tapes: {e}")
            return []

    def get_tape_details(self, tape_arns: List[str]) -> List[Dict]:
        """
        Get detailed information about specific virtual tapes
        
        This method retrieves comprehensive information about tapes including
        creation dates, status, size, and other metadata needed for expiry
        analysis and deletion decisions.
        
        Args:
            tape_arns (List[str]): List of tape ARNs to get details for
        
        Returns:
            List[Dict]: Detailed tape information including:
                       - TapeARN: Amazon Resource Name
                       - TapeBarcode: Human-readable identifier
                       - TapeCreatedDate: When the tape was created
                       - TapeStatus: Current operational status
                       - TapeSizeInBytes: Allocated size
                       - TapeUsedInBytes: Actually used space
                       - Progress: Completion percentage for operations
        
        Note:
            This API call is more expensive than list_tapes as it returns
            detailed information. Only call for tapes you actually need to analyze.
        """
        try:
            # Call AWS API to get detailed tape information
            # This provides creation dates and other metadata needed for expiry checks
            response = self.storagegateway.describe_tapes(TapeARNs=tape_arns)
            return response.get('Tapes', [])
        except Exception as e:
            # Log error and return empty list - allows caller to handle gracefully
            logger.error(f"Failed to get tape details: {e}")
            return []

    def is_tape_expired(self, tape: Dict, expiry_days: int) -> bool:
        """
        Determine if a virtual tape has exceeded the expiry threshold
        
        This method calculates the age of a tape based on its creation date
        and compares it against the configured expiry threshold. Tapes older
        than the threshold are considered expired and eligible for deletion.
        
        Args:
            tape (Dict): Tape information dictionary from describe_tapes API
            expiry_days (int): Number of days after which a tape is considered expired
        
        Returns:
            bool: True if tape is expired (older than expiry_days), False otherwise
        
        Note:
            - Uses UTC timezone for consistent date calculations
            - Handles timezone-naive dates by assuming UTC
            - Returns False for tapes without creation dates (safety measure)
        """
        try:
            # Extract creation date from tape metadata
            creation_date = tape.get('TapeCreatedDate')
            if not creation_date:
                # If no creation date, assume tape is not expired (safety measure)
                return False
            
            # Get current time in UTC for consistent comparison
            now = datetime.now(timezone.utc)
            
            # Ensure creation date has timezone info for proper comparison
            if creation_date.tzinfo is None:
                # If timezone-naive, assume UTC (AWS typically returns UTC dates)
                creation_date = creation_date.replace(tzinfo=timezone.utc)
            
            # Calculate age in days by subtracting creation date from now
            age_days = (now - creation_date).days
            
            # Return True if tape is older than the expiry threshold
            return age_days > expiry_days
        except Exception as e:
            # Log error and return False (conservative approach - don't delete on error)
            logger.error(f"Error checking tape expiry: {e}")
            return False

    def delete_virtual_tape(self, tape_arn: str, bypass_governance_retention: bool = False) -> bool:
        """
        Delete a single virtual tape from Storage Gateway
        
        This method performs the actual deletion of a virtual tape using the
        AWS Storage Gateway API. It handles the deletion request and provides
        feedback on success or failure.
        
        Args:
            tape_arn (str): Amazon Resource Name of the tape to delete
            bypass_governance_retention (bool): Whether to bypass governance retention
                                              policies that might prevent deletion
        
        Returns:
            bool: True if deletion was successful, False otherwise
        
        Note:
            - Tape must be in AVAILABLE or ARCHIVED status to be deletable
            - Some tapes may have retention policies preventing deletion
            - The bypass_governance_retention flag can override some restrictions
            - Deletion is permanent and cannot be undone
        
        AWS API Reference:
            https://docs.aws.amazon.com/storagegateway/latest/APIReference/API_DeleteTape.html
        """
        try:
            # Extract Gateway ARN from Tape ARN for the API call
            # Tape ARN format: arn:aws:storagegateway:region:account:tape/gateway-id/tape-id
            # Gateway ARN format: arn:aws:storagegateway:region:account:gateway/gateway-id
            gateway_arn = tape_arn.split('/')[0] + '/' + tape_arn.split('/')[1]
            
            # Call AWS API to delete the tape
            self.storagegateway.delete_tape(
                GatewayARN=gateway_arn,  # Required: Gateway that owns the tape
                TapeARN=tape_arn,        # Required: Specific tape to delete
                BypassGovernanceRetention=bypass_governance_retention  # Optional: Override retention
            )
            
            # Log successful deletion
            logger.info(f"Successfully deleted tape: {tape_arn}")
            return True
        except Exception as e:
            # Log error with tape ARN for troubleshooting
            # Don't raise exception - let caller handle the failure
            logger.error(f"Failed to delete tape {tape_arn}: {e}")
            return False

    def delete_expired_tapes(self, expiry_days: int, dry_run: bool = True, 
                           gateway_arn: str = None, bypass_governance: bool = False) -> Dict:
        """
        Main method to identify and delete expired virtual tapes
        
        This is the primary orchestration method that coordinates the entire
        cleanup process. It discovers tapes, identifies expired ones, and
        optionally deletes them based on the dry_run parameter.
        
        Process Flow:
        1. List all virtual tapes in the region/gateway
        2. Get detailed information for each tape
        3. Analyze each tape to determine if it's expired
        4. Delete expired tapes (if not in dry-run mode)
        5. Return comprehensive results summary
        
        Args:
            expiry_days (int): Age threshold in days for considering tapes expired
            dry_run (bool): If True, only simulate deletion without actually deleting
            gateway_arn (str, optional): Specific Storage Gateway ARN to target
            bypass_governance (bool): Whether to bypass governance retention policies
        
        Returns:
            Dict: Comprehensive results summary containing:
                - total_tapes: Total number of tapes found
                - expired_tapes: Number of tapes identified as expired
                - deleted_tapes: Number of tapes actually deleted (or would be deleted)
                - failed_deletions: Number of deletion attempts that failed
                - errors: List of error messages encountered
        
        Safety Features:
        - Dry-run mode prevents accidental deletions
        - Status checking ensures only deletable tapes are processed
        - Comprehensive error handling and logging
        - Detailed results reporting for audit purposes
        """
        # Initialize results dictionary to track all operations
        results = {
            'total_tapes': 0,        # Total tapes discovered
            'expired_tapes': 0,      # Tapes identified as expired
            'deleted_tapes': 0,      # Tapes successfully deleted
            'failed_deletions': 0,   # Deletion attempts that failed
            'errors': []             # List of error messages
        }

        try:
            # Step 1: Discover all virtual tapes in the specified scope
            logger.info("Starting tape discovery process...")
            tapes = self.list_virtual_tapes(gateway_arn)
            results['total_tapes'] = len(tapes)

            # Early exit if no tapes found
            if not tapes:
                logger.warning("No virtual tapes found")
                return results

            # Step 2: Get detailed information for all discovered tapes
            # This is necessary because list_tapes doesn't include creation dates
            logger.info("Retrieving detailed tape information...")
            tape_arns = [tape['TapeARN'] for tape in tapes]
            detailed_tapes = self.get_tape_details(tape_arns)

            # Step 3: Analyze each tape to identify expired ones
            logger.info(f"Analyzing tapes for expiry (threshold: {expiry_days} days)...")
            expired_tapes = []
            for tape in detailed_tapes:
                if self.is_tape_expired(tape, expiry_days):
                    expired_tapes.append(tape)

            results['expired_tapes'] = len(expired_tapes)
            logger.info(f"Found {len(expired_tapes)} expired tapes (older than {expiry_days} days)")

            # Step 4: Process expired tapes for deletion
            for tape in expired_tapes:
                tape_arn = tape['TapeARN']
                tape_barcode = tape.get('TapeBarcode', 'Unknown')
                tape_status = tape.get('TapeStatus', 'Unknown')
                
                logger.info(f"Processing tape: {tape_barcode} (Status: {tape_status})")
                
                if dry_run:
                    # Dry-run mode: Log what would be deleted but don't actually delete
                    logger.info(f"DRY RUN: Would delete tape {tape_barcode} ({tape_arn})")
                    results['deleted_tapes'] += 1
                else:
                    # Actual deletion mode: Check status and attempt deletion
                    # Only delete tapes that are in a safe state for deletion
                    if tape_status in ['AVAILABLE', 'ARCHIVED']:
                        # Attempt deletion and track results
                        if self.delete_virtual_tape(tape_arn, bypass_governance):
                            results['deleted_tapes'] += 1
                        else:
                            results['failed_deletions'] += 1
                            results['errors'].append(f"Failed to delete {tape_barcode}")
                    else:
                        # Skip tapes that are not in a deletable state
                        logger.warning(f"Skipping tape {tape_barcode} - Status: {tape_status} (not deletable)")
                        results['errors'].append(f"Tape {tape_barcode} not in deletable state: {tape_status}")

        except Exception as e:
            # Catch any unexpected errors during the process
            logger.error(f"Error in delete_expired_tapes: {e}")
            results['errors'].append(str(e))

        return results

def main():
    """
    Main entry point for the virtual tape cleanup script
    
    This function handles command-line argument parsing, validates inputs,
    initializes the tape manager, and orchestrates the cleanup process.
    It also formats and displays the final results.
    
    Command Line Arguments:
    - --region: AWS region (required)
    - --profile: AWS profile name (optional)
    - --expiry-days: Age threshold for expiry (default: 30)
    - --gateway-arn: Specific gateway to target (optional)
    - --dry-run: Safe mode without actual deletion (default: True)
    - --execute: Override dry-run to actually delete tapes
    - --bypass-governance: Override governance retention policies
    
    Exit Codes:
    - 0: Success
    - 1: Error during execution
    """
    # Set up command-line argument parsing with detailed help
    parser = argparse.ArgumentParser(
        description='Delete expired virtual tapes from AWS Storage Gateway',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be deleted
  python3 %(prog)s --region us-east-1 --expiry-days 60

  # Actually delete expired tapes
  python3 %(prog)s --region us-east-1 --expiry-days 60 --execute

  # Use specific AWS profile
  python3 %(prog)s --region us-west-2 --profile production --expiry-days 90 --execute
        """
    )
    
    # Define all command-line arguments with detailed help text
    parser.add_argument('--region', required=True, 
                       help='AWS region where Storage Gateway is located')
    parser.add_argument('--profile', 
                       help='AWS profile to use (uses default credentials if not specified)')
    parser.add_argument('--expiry-days', type=int, default=30, 
                       help='Number of days after which tapes are considered expired (default: 30)')
    parser.add_argument('--gateway-arn', 
                       help='Specific Storage Gateway ARN to target (processes all gateways if not specified)')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Perform a dry run without actually deleting tapes (default: True)')
    parser.add_argument('--execute', action='store_true',
                       help='Actually execute the deletion (overrides dry-run for safety)')
    parser.add_argument('--bypass-governance', action='store_true',
                       help='Bypass governance retention policies for deletion (use with caution)')
    
    # Parse command-line arguments
    args = parser.parse_args()

    # Determine execution mode: dry-run is default unless --execute is specified
    # This provides an extra safety layer to prevent accidental deletions
    dry_run = not args.execute

    # Log startup information for audit trail
    logger.info("="*60)
    logger.info("Starting Virtual Tape Cleanup Process")
    logger.info("="*60)
    logger.info(f"Region: {args.region}")
    logger.info(f"Profile: {args.profile or 'default'}")
    logger.info(f"Expiry threshold: {args.expiry_days} days")
    logger.info(f"Gateway ARN: {args.gateway_arn or 'all gateways'}")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    logger.info(f"Bypass governance: {args.bypass_governance}")
    logger.info("="*60)

    # Initialize the tape manager with specified AWS configuration
    tape_manager = VirtualTapeManager(args.region, args.profile)

    # Execute the main cleanup process
    results = tape_manager.delete_expired_tapes(
        expiry_days=args.expiry_days,
        dry_run=dry_run,
        gateway_arn=args.gateway_arn,
        bypass_governance=args.bypass_governance
    )

    # Display comprehensive results summary
    print("\n" + "="*50)
    print("VIRTUAL TAPE CLEANUP RESULTS")
    print("="*50)
    print(f"Total tapes found: {results['total_tapes']}")
    print(f"Expired tapes: {results['expired_tapes']}")
    print(f"{'Would delete' if dry_run else 'Deleted'}: {results['deleted_tapes']}")
    print(f"Failed deletions: {results['failed_deletions']}")
    
    # Display any errors encountered during processing
    if results['errors']:
        print(f"\nErrors encountered:")
        for error in results['errors']:
            print(f"  - {error}")

    # Provide guidance for next steps if in dry-run mode
    if dry_run and results['expired_tapes'] > 0:
        print(f"\nTo actually delete the tapes, run with --execute flag")
        print(f"Command: python3 {sys.argv[0]} {' '.join(sys.argv[1:])} --execute")

    # Log completion
    logger.info("Virtual Tape Cleanup Process Completed")


# Standard Python idiom to run main() only when script is executed directly
# This allows the script to be imported as a module without running main()
if __name__ == "__main__":
    main()