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
from botocore.exceptions import ClientError, BotoCoreError, EndpointConnectionError
import argparse
import logging
from datetime import datetime, timezone
from typing import List, Dict
import sys
import time

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
    
    # AWS API retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    
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
            logger.error("Please check your AWS credentials and region configuration")
            sys.exit(1)
    
    def _handle_aws_error(self, error: Exception, operation: str, critical: bool = False) -> bool:
        """
        Handle AWS API errors with appropriate logging and retry logic
        
        Args:
            error: The exception that was raised
            operation: Description of the operation that failed
            critical: If True, exit the script on error
        
        Returns:
            bool: True if the error is retryable, False otherwise
        """
        if isinstance(error, ClientError):
            error_code = error.response.get('Error', {}).get('Code', 'Unknown')
            error_message = error.response.get('Error', {}).get('Message', str(error))
            
            # Handle specific AWS error codes
            if error_code == 'ThrottlingException' or error_code == 'RequestLimitExceeded':
                logger.warning(f"AWS API rate limit exceeded during {operation}")
                logger.warning(f"Error: {error_message}")
                logger.info("The script will retry with exponential backoff...")
                return True  # Retryable
                
            elif error_code == 'LimitExceededException':
                logger.error(f"AWS service limit exceeded during {operation}")
                logger.error(f"Error: {error_message}")
                logger.error("Please check your AWS service quotas and limits")
                if critical:
                    logger.error("This is a critical operation. Exiting...")
                    sys.exit(1)
                return False  # Not retryable
                
            elif error_code == 'InvalidGatewayRequestException':
                logger.error(f"Invalid gateway request during {operation}")
                logger.error(f"Error: {error_message}")
                logger.error("The gateway may not exist or may not be accessible")
                if critical:
                    sys.exit(1)
                return False
                
            elif error_code == 'InternalServerError' or error_code == 'ServiceUnavailableException':
                logger.warning(f"AWS service error during {operation}")
                logger.warning(f"Error: {error_message}")
                logger.info("This is usually temporary. The script will retry...")
                return True  # Retryable
                
            elif error_code == 'AccessDeniedException' or error_code == 'UnauthorizedOperation':
                logger.error(f"Access denied during {operation}")
                logger.error(f"Error: {error_message}")
                logger.error("Please check your IAM permissions for Storage Gateway operations")
                logger.error("Required permissions: storagegateway:ListGateways, ListTapes, DescribeTapes, DeleteTape, DeleteTapeArchive")
                if critical:
                    sys.exit(1)
                return False
                
            elif error_code == 'ResourceNotFoundException':
                logger.error(f"Resource not found during {operation}")
                logger.error(f"Error: {error_message}")
                if critical:
                    sys.exit(1)
                return False
                
            else:
                logger.error(f"AWS API error during {operation}")
                logger.error(f"Error Code: {error_code}")
                logger.error(f"Error Message: {error_message}")
                if critical:
                    logger.error("Critical operation failed. Exiting...")
                    sys.exit(1)
                return False
                
        elif isinstance(error, EndpointConnectionError):
            logger.error(f"Cannot connect to AWS endpoint during {operation}")
            logger.error(f"Error: {str(error)}")
            logger.error("Please check your internet connection and AWS region configuration")
            if critical:
                sys.exit(1)
            return False
            
        elif isinstance(error, BotoCoreError):
            logger.error(f"AWS SDK error during {operation}")
            logger.error(f"Error: {str(error)}")
            if critical:
                sys.exit(1)
            return False
            
        else:
            logger.error(f"Unexpected error during {operation}")
            logger.error(f"Error: {str(error)}")
            if critical:
                sys.exit(1)
            return False
    
    def _retry_with_backoff(self, func, *args, operation: str = "operation", critical: bool = False, **kwargs):
        """
        Execute a function with exponential backoff retry logic
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            operation: Description of the operation for logging
            critical: If True, exit on non-retryable errors
            **kwargs: Keyword arguments for the function
        
        Returns:
            The result of the function call
        
        Raises:
            Exception: Re-raises the last exception if all retries fail
        """
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                return func(*args, **kwargs)
                
            except Exception as e:
                last_error = e
                is_retryable = self._handle_aws_error(e, operation, critical=False)
                
                if not is_retryable:
                    if critical:
                        logger.error(f"Non-retryable error in critical operation: {operation}")
                        sys.exit(1)
                    raise
                
                if attempt < self.MAX_RETRIES - 1:
                    # Calculate exponential backoff delay
                    delay = self.RETRY_DELAY * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds... (Attempt {attempt + 1}/{self.MAX_RETRIES})")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.MAX_RETRIES} retry attempts failed for {operation}")
                    if critical:
                        logger.error("Critical operation failed after all retries. Exiting...")
                        sys.exit(1)
                    raise last_error
        
        # Should not reach here, but just in case
        if last_error:
            raise last_error

    def list_virtual_tapes(self, gateway_arn: str = None) -> List[Dict]:
        """
        Retrieve a list of all virtual tapes from Storage Gateway
        
        This method calls the AWS Storage Gateway API to get basic information
        about all virtual tapes. The list_tapes API returns all tapes across
        all gateways in the region, so we filter by gateway if specified.
        
        Args:
            gateway_arn (str, optional): Specific Storage Gateway ARN to query.
                                       If None, returns all tapes in the region
        
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
            all_tapes = []
            marker = None
            
            # The list_tapes API returns all tapes across all gateways in the region
            # We'll paginate through all results and filter by gateway if needed
            while True:
                logger.info("Retrieving virtual tapes from Storage Gateway...")
                
                # Build API call parameters
                params = {'Limit': 100}
                if marker:
                    params['Marker'] = marker
                
                # Call AWS API to list tapes with retry logic
                response = self._retry_with_backoff(
                    self.storagegateway.list_tapes,
                    **params,
                    operation="list_tapes",
                    critical=True
                )
                
                # Extract tape information from API response
                tapes = response.get('TapeInfos', [])
                
                # Filter by gateway if specified
                if gateway_arn:
                    # We need to get detailed info to check which gateway owns each tape
                    if tapes:
                        tape_arns = [tape['TapeARN'] for tape in tapes]
                        detailed_tapes = self.get_tape_details(tape_arns)
                        
                        # Filter tapes that belong to the specified gateway
                        filtered_tapes = []
                        for detailed_tape in detailed_tapes:
                            if detailed_tape.get('GatewayARN') == gateway_arn:
                                # Find the corresponding basic tape info
                                for basic_tape in tapes:
                                    if basic_tape['TapeARN'] == detailed_tape['TapeARN']:
                                        filtered_tapes.append(basic_tape)
                                        break
                        
                        all_tapes.extend(filtered_tapes)
                else:
                    # No filtering needed, add all tapes
                    all_tapes.extend(tapes)
                
                # Check if there are more results to fetch
                marker = response.get('Marker')
                if not marker:
                    break
                    
                logger.info(f"Retrieved {len(tapes)} tapes, continuing pagination...")
            
            if gateway_arn:
                logger.info(f"Found {len(all_tapes)} virtual tapes for gateway {gateway_arn}")
            else:
                logger.info(f"Found {len(all_tapes)} virtual tapes across all gateways")
            
            return all_tapes
            
        except Exception as e:
            # Log error but don't crash - return empty list to allow graceful handling
            logger.error(f"Failed to list virtual tapes: {e}")
            return []

    def get_tape_details(self, tape_arns: List[str], gateway_arn: str = None) -> List[Dict]:
        """
        Get detailed information about specific virtual tapes
        
        This method retrieves comprehensive information about tapes including
        creation dates, status, size, and other metadata needed for expiry
        analysis and deletion decisions.
        
        Args:
            tape_arns (List[str]): List of tape ARNs to get details for
            gateway_arn (str, optional): Specific gateway ARN if known
        
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
            This method handles both regular tapes (via Storage Gateway) and
            archived tapes (via VTS - Virtual Tape Shelf). Archived tapes
            require different API calls.
        """
        if not tape_arns:
            return []
            
        try:
            all_detailed_tapes = []
            
            # First, try to get details for archived tapes using describe_vtl_devices
            # This works for tapes that are in ARCHIVED status
            logger.info("Checking for archived tapes in Virtual Tape Shelf (VTS)...")
            try:
                # For archived tapes, we can use describe_vtl_devices or list_tapes with more details
                # Let's try a different approach - use the basic tape info and enhance it
                
                # Get basic tape information first to determine status
                basic_tapes = self.list_virtual_tapes(gateway_arn)
                basic_tape_dict = {tape['TapeARN']: tape for tape in basic_tapes}
                
                # Separate tapes by status
                archived_tape_arns = []
                active_tape_arns = []
                
                for tape_arn in tape_arns:
                    basic_tape = basic_tape_dict.get(tape_arn)
                    if basic_tape and basic_tape.get('TapeStatus') == 'ARCHIVED':
                        archived_tape_arns.append(tape_arn)
                    else:
                        active_tape_arns.append(tape_arn)
                
                logger.info(f"Found {len(archived_tape_arns)} archived tapes and {len(active_tape_arns)} active tapes")
                
                # For archived tapes, we'll use the basic information and enhance it
                # since describe_tapes doesn't work for archived tapes
                for tape_arn in archived_tape_arns:
                    basic_tape = basic_tape_dict.get(tape_arn)
                    if basic_tape:
                        # Create a detailed tape record from basic information
                        # For archived tapes, we may not have all the detailed info
                        detailed_tape = {
                            'TapeARN': basic_tape.get('TapeARN', ''),
                            'TapeBarcode': basic_tape.get('TapeBarcode', 'Unknown'),
                            'TapeStatus': basic_tape.get('TapeStatus', 'Unknown'),
                            'TapeSizeInBytes': basic_tape.get('TapeSizeInBytes', 0),
                            'TapeUsedInBytes': basic_tape.get('TapeUsedInBytes', 0),
                            'TapeCreatedDate': None,  # Not available in basic info
                            'GatewayARN': gateway_arn or '',
                            'PoolId': basic_tape.get('PoolId', ''),
                            'RetentionStartDate': None,
                            'PoolEntryDate': None,
                            'Progress': basic_tape.get('Progress', 0)
                        }
                        all_detailed_tapes.append(detailed_tape)
                        
                logger.info(f"Processed {len(archived_tape_arns)} archived tapes using basic information")
                
            except Exception as e:
                logger.warning(f"Failed to process archived tapes: {e}")
            
            # For active tapes, try the regular Storage Gateway approach
            if active_tape_arns:
                logger.info(f"Processing {len(active_tape_arns)} active tapes via Storage Gateway...")
                
                if gateway_arn:
                    # If we have a specific gateway ARN, use it directly
                    try:
                        logger.info(f"Getting details for {len(active_tape_arns)} active tapes from specified gateway {gateway_arn}")
                        response = self._retry_with_backoff(
                            self.storagegateway.describe_tapes,
                            GatewayARN=gateway_arn,
                            TapeARNs=active_tape_arns,
                            operation=f"describe_tapes for gateway {gateway_arn}",
                            critical=False
                        )
                        detailed_tapes = response.get('Tapes', [])
                        all_detailed_tapes.extend(detailed_tapes)
                        logger.info(f"Retrieved details for {len(detailed_tapes)} active tapes")
                    except Exception as e:
                        logger.error(f"Failed to get active tape details for gateway {gateway_arn}: {e}")
                        self._handle_aws_error(e, f"describe_tapes for gateway {gateway_arn}", critical=False)
                else:
                    # We need to discover gateways and try each one for active tapes
                    logger.info("Discovering Storage Gateways for active tapes...")
                    
                    try:
                        # Get all gateways in the region with retry logic
                        gateways_response = self._retry_with_backoff(
                            self.storagegateway.list_gateways,
                            Limit=100,
                            operation="list_gateways",
                            critical=False
                        )
                        gateways = gateways_response.get('Gateways', [])
                        
                        if not gateways:
                            logger.warning("No Storage Gateways found in the region")
                        else:
                            logger.info(f"Found {len(gateways)} Storage Gateway(s), checking each for active tapes")
                            
                            # Try each gateway to find our active tapes
                            remaining_tape_arns = set(active_tape_arns)
                            
                            for gateway in gateways:
                                if not remaining_tape_arns:
                                    break  # Found all tapes
                                    
                                current_gateway_arn = gateway.get('GatewayARN')
                                gateway_name = gateway.get('GatewayName', 'Unknown')
                                
                                if not current_gateway_arn:
                                    continue
                                    
                                try:
                                    logger.info(f"Checking gateway: {gateway_name} ({current_gateway_arn})")
                                    
                                    # Batch the requests to avoid API limits
                                    remaining_list = list(remaining_tape_arns)
                                    batch_size = 100
                                    
                                    for i in range(0, len(remaining_list), batch_size):
                                        batch_arns = remaining_list[i:i + batch_size]
                                        
                                        try:
                                            response = self._retry_with_backoff(
                                                self.storagegateway.describe_tapes,
                                                GatewayARN=current_gateway_arn,
                                                TapeARNs=batch_arns,
                                                operation=f"describe_tapes for gateway {gateway_name}",
                                                critical=False
                                            )
                                            
                                            detailed_tapes = response.get('Tapes', [])
                                            if detailed_tapes:
                                                all_detailed_tapes.extend(detailed_tapes)
                                                
                                                # Remove found tapes from remaining list
                                                found_tape_arns = {tape['TapeARN'] for tape in detailed_tapes}
                                                remaining_tape_arns -= found_tape_arns
                                                
                                                logger.info(f"Found {len(detailed_tapes)} active tapes in gateway {gateway_name}")
                                                
                                        except Exception as batch_e:
                                            logger.debug(f"Gateway {gateway_name} doesn't have active tapes in this batch: {batch_e}")
                                            continue
                                    
                                except Exception as e:
                                    logger.debug(f"Gateway {gateway_name} error: {e}")
                                    continue
                            
                            if remaining_tape_arns:
                                logger.warning(f"Could not find details for {len(remaining_tape_arns)} active tapes")
                                        
                    except Exception as e:
                        logger.error(f"Failed to discover gateways for active tapes: {e}")
            
            logger.info(f"Successfully retrieved details for {len(all_detailed_tapes)} total tapes")
            return all_detailed_tapes
            
        except Exception as e:
            # Log error and return empty list - allows caller to handle gracefully
            logger.error(f"Failed to get tape details: {e}")
            return []

    def is_tape_expired(self, tape: Dict, expiry_days: int) -> bool:
        """
        Determine if a virtual tape has exceeded the expiry threshold
        
        This method calculates the age of a tape based on its creation date
        and compares it against the configured expiry threshold. For archived
        tapes without creation dates, it uses alternative logic.
        
        Args:
            tape (Dict): Tape information dictionary from describe_tapes API
            expiry_days (int): Number of days after which a tape is considered expired
        
        Returns:
            bool: True if tape is expired (older than expiry_days), False otherwise
        
        Note:
            - Uses UTC timezone for consistent date calculations
            - Handles timezone-naive dates by assuming UTC
            - For archived tapes without creation dates, considers them expired if expiry_days > 0
            - Returns False for tapes without creation dates only if expiry_days is very large (> 3650 days / 10 years)
        """
        try:
            # Extract creation date from tape metadata
            creation_date = tape.get('TapeCreatedDate')
            tape_status = tape.get('TapeStatus', 'Unknown')
            
            if creation_date:
                # We have a creation date - use normal age calculation
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
            else:
                # No creation date available - this is common for archived tapes
                logger.debug(f"No creation date for tape {tape.get('TapeBarcode', 'Unknown')} (Status: {tape_status})")
                
                if tape_status == 'ARCHIVED':
                    # For archived tapes, we assume they are old since archiving typically happens
                    # to older tapes. We'll consider them expired unless the expiry threshold
                    # is very conservative (> 10 years)
                    if expiry_days > 3650:  # More than 10 years
                        logger.info(f"Archived tape {tape.get('TapeBarcode', 'Unknown')} not considered expired due to very long expiry threshold ({expiry_days} days)")
                        return False
                    else:
                        logger.info(f"Archived tape {tape.get('TapeBarcode', 'Unknown')} considered expired (no creation date, expiry threshold: {expiry_days} days)")
                        return True
                else:
                    # For non-archived tapes without creation dates, be conservative
                    logger.warning(f"Non-archived tape {tape.get('TapeBarcode', 'Unknown')} has no creation date - assuming not expired")
                    return False
                    
        except Exception as e:
            # Log error and return False (conservative approach - don't delete on error)
            logger.error(f"Error checking tape expiry for {tape.get('TapeBarcode', 'Unknown')}: {e}")
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
            - Tape must be in AVAILABLE status to be deletable via Storage Gateway
            - ARCHIVED tapes cannot be deleted directly - they must be retrieved from VTS first
            - Some tapes may have retention policies preventing deletion
            - The bypass_governance_retention flag can override some restrictions
            - Deletion is permanent and cannot be undone
        
        AWS API Reference:
            https://docs.aws.amazon.com/storagegateway/latest/APIReference/API_DeleteTape.html
        """
        try:
            # Check if this is an archived tape first
            # We need to get the tape status to determine if it can be deleted
            basic_tapes = self.list_virtual_tapes()
            tape_info = None
            for tape in basic_tapes:
                if tape.get('TapeARN') == tape_arn:
                    tape_info = tape
                    break
            
            if not tape_info:
                logger.error(f"Tape not found: {tape_arn}")
                return False
            
            tape_status = tape_info.get('TapeStatus', 'Unknown')
            tape_barcode = tape_info.get('TapeBarcode', 'Unknown')
            
            if tape_status == 'ARCHIVED':
                logger.warning(f"Tape {tape_barcode} is ARCHIVED. Attempting to delete from Virtual Tape Shelf (VTS)...")
                # For archived tapes, use DeleteTapeArchive API instead
                try:
                    self._retry_with_backoff(
                        self.storagegateway.delete_tape_archive,
                        TapeARN=tape_arn,
                        BypassGovernanceRetention=bypass_governance_retention,
                        operation=f"delete_tape_archive for {tape_barcode}",
                        critical=False
                    )
                    logger.info(f"Successfully deleted archived tape from VTS: {tape_barcode} ({tape_arn})")
                    return True
                except Exception as e:
                    logger.error(f"Failed to delete archived tape {tape_barcode} from VTS: {e}")
                    self._handle_aws_error(e, f"delete_tape_archive for {tape_barcode}", critical=False)
                    return False
            
            # For non-archived tapes, we need to find the gateway that owns this tape
            # Try to get the gateway ARN by querying all gateways
            try:
                gateways_response = self._retry_with_backoff(
                    self.storagegateway.list_gateways,
                    Limit=100,
                    operation="list_gateways for tape deletion",
                    critical=False
                )
                gateways = gateways_response.get('Gateways', [])
            except Exception as e:
                logger.error(f"Failed to list gateways: {e}")
                self._handle_aws_error(e, "list_gateways for tape deletion", critical=False)
                return False
            
            gateway_arn = None
            for gateway in gateways:
                current_gateway_arn = gateway.get('GatewayARN')
                if not current_gateway_arn:
                    continue
                    
                try:
                    # Try to get details for this tape from this gateway
                    response = self._retry_with_backoff(
                        self.storagegateway.describe_tapes,
                        GatewayARN=current_gateway_arn,
                        TapeARNs=[tape_arn],
                        operation=f"describe_tapes for tape {tape_barcode}",
                        critical=False
                    )
                    
                    detailed_tapes = response.get('Tapes', [])
                    if detailed_tapes:
                        # Found the gateway that owns this tape
                        gateway_arn = current_gateway_arn
                        break
                        
                except Exception:
                    # This gateway doesn't have this tape, try next
                    continue
            
            if not gateway_arn:
                logger.error(f"Could not find gateway for tape {tape_barcode} ({tape_arn})")
                return False
            
            # Call AWS API to delete the tape with retry logic
            try:
                self._retry_with_backoff(
                    self.storagegateway.delete_tape,
                    GatewayARN=gateway_arn,  # Required: Gateway that owns the tape
                    TapeARN=tape_arn,        # Required: Specific tape to delete
                    BypassGovernanceRetention=bypass_governance_retention,  # Optional: Override retention
                    operation=f"delete_tape for {tape_barcode}",
                    critical=False
                )
                
                # Log successful deletion
                logger.info(f"Successfully deleted tape: {tape_barcode} ({tape_arn})")
                return True
            except Exception as e:
                logger.error(f"Failed to delete tape {tape_barcode}: {e}")
                self._handle_aws_error(e, f"delete_tape for {tape_barcode}", critical=False)
                return False
            
        except Exception as e:
            # Log error with tape ARN for troubleshooting
            # Don't raise exception - let caller handle the failure
            logger.error(f"Failed to delete tape {tape_arn}: {e}")
            return False

    def list_all_tapes_detailed(self, gateway_arn: str = None, status_filter: List[str] = None) -> Dict:
        """
        List all virtual tapes with detailed information for inventory purposes
        
        This method provides a comprehensive inventory of all virtual tapes
        including their status, creation dates, sizes, and other metadata.
        Useful for auditing, reporting, and understanding tape usage patterns.
        
        Args:
            gateway_arn (str, optional): Specific Storage Gateway ARN to target
            status_filter (List[str], optional): List of tape statuses to include (e.g., ['AVAILABLE', 'RETRIEVED'])
                                                If None, includes all tapes regardless of status
        
        Returns:
            Dict: Comprehensive tape inventory containing:
                - total_tapes: Total number of tapes found (before filtering)
                - filtered_tapes: Number of tapes after status filtering
                - tapes_by_status: Dictionary grouping tapes by their status
                - tape_details: List of all tape information (filtered)
                - total_size_bytes: Total allocated size across filtered tapes
                - total_used_bytes: Total used space across filtered tapes
                - status_filter_applied: List of statuses used for filtering (or None)
        """
        results = {
            'total_tapes': 0,
            'filtered_tapes': 0,
            'tapes_by_status': {},
            'tape_details': [],
            'total_size_bytes': 0,
            'total_used_bytes': 0,
            'errors': [],
            'status_filter_applied': status_filter
        }

        try:
            # Step 1: Get basic tape information
            logger.info("Retrieving all virtual tapes...")
            tapes = self.list_virtual_tapes(gateway_arn)
            results['total_tapes'] = len(tapes)

            if not tapes:
                logger.warning("No virtual tapes found")
                return results

            # Step 2: Get detailed information for all tapes
            logger.info("Retrieving detailed tape information...")
            tape_arns = [tape['TapeARN'] for tape in tapes]
            logger.info(f"Requesting details for {len(tape_arns)} tapes")
            detailed_tapes = self.get_tape_details(tape_arns, gateway_arn)
            logger.info(f"Received details for {len(detailed_tapes)} tapes")

            # Step 3: Process and categorize tape information
            for tape in detailed_tapes:
                # Extract key information
                tape_status = tape.get('TapeStatus', 'Unknown')
                tape_size = tape.get('TapeSizeInBytes', 0)
                tape_used = tape.get('TapeUsedInBytes', 0)
                creation_date = tape.get('TapeCreatedDate')
                
                # Apply status filter if specified
                if status_filter and tape_status not in status_filter:
                    continue  # Skip tapes that don't match the filter
                
                # Calculate age if creation date is available
                age_days = None
                if creation_date:
                    try:
                        now = datetime.now(timezone.utc)
                        if creation_date.tzinfo is None:
                            creation_date = creation_date.replace(tzinfo=timezone.utc)
                        age_days = (now - creation_date).days
                    except Exception as e:
                        logger.warning(f"Could not calculate age for tape {tape.get('TapeBarcode', 'Unknown')}: {e}")

                # Build detailed tape record
                tape_record = {
                    'arn': tape.get('TapeARN', ''),
                    'barcode': tape.get('TapeBarcode', 'Unknown'),
                    'status': tape_status,
                    'size_bytes': tape_size,
                    'used_bytes': tape_used,
                    'creation_date': creation_date.isoformat() if creation_date else None,
                    'age_days': age_days,
                    'gateway_arn': tape.get('GatewayARN', ''),
                    'pool_id': tape.get('PoolId', ''),
                    'retention_start_date': tape.get('RetentionStartDate').isoformat() if tape.get('RetentionStartDate') else None,
                    'pool_entry_date': tape.get('PoolEntryDate').isoformat() if tape.get('PoolEntryDate') else None
                }
                
                results['tape_details'].append(tape_record)
                
                # Group by status for summary
                if tape_status not in results['tapes_by_status']:
                    results['tapes_by_status'][tape_status] = []
                results['tapes_by_status'][tape_status].append(tape_record)
                
                # Accumulate size statistics
                results['total_size_bytes'] += tape_size
                results['total_used_bytes'] += tape_used

            results['filtered_tapes'] = len(results['tape_details'])
            
            if status_filter:
                logger.info(f"Successfully processed {len(detailed_tapes)} tapes, {results['filtered_tapes']} match status filter {status_filter}")
            else:
                logger.info(f"Successfully processed {len(detailed_tapes)} tapes")

        except Exception as e:
            logger.error(f"Error in list_all_tapes_detailed: {e}")
            results['errors'].append(str(e))

        return results

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
            detailed_tapes = self.get_tape_details(tape_arns, gateway_arn)

            # Step 3: Analyze each tape to identify expired ones
            logger.info(f"Analyzing tapes for expiry (threshold: {expiry_days} days)...")
            expired_tapes = []
            for tape in detailed_tapes:
                if self.is_tape_expired(tape, expiry_days):
                    expired_tapes.append(tape)

            results['expired_tapes'] = len(expired_tapes)
            logger.info(f"Found {len(expired_tapes)} expired tapes (older than {expiry_days} days)")

            # Step 4: Process expired tapes for deletion
            archived_tapes_count = 0
            active_expired_tapes = []
            
            for tape in expired_tapes:
                tape_arn = tape['TapeARN']
                tape_barcode = tape.get('TapeBarcode', 'Unknown')
                tape_status = tape.get('TapeStatus', 'Unknown')
                
                logger.info(f"Processing expired tape: {tape_barcode} (Status: {tape_status})")
                
                if tape_status == 'ARCHIVED':
                    archived_tapes_count += 1
                    logger.warning(f"Skipping archived tape {tape_barcode} - cannot delete directly (must retrieve from VTS first)")
                    results['errors'].append(f"Archived tape {tape_barcode} cannot be deleted directly")
                else:
                    active_expired_tapes.append(tape)
            
            logger.info(f"Found {archived_tapes_count} archived expired tapes and {len(active_expired_tapes)} active expired tapes")
            
            # Process active expired tapes for deletion
            for tape in active_expired_tapes:
                tape_arn = tape['TapeARN']
                tape_barcode = tape.get('TapeBarcode', 'Unknown')
                tape_status = tape.get('TapeStatus', 'Unknown')
                
                if dry_run:
                    # Dry-run mode: Log what would be deleted but don't actually delete
                    logger.info(f"DRY RUN: Would delete tape {tape_barcode} ({tape_arn})")
                    results['deleted_tapes'] += 1
                else:
                    # Actual deletion mode: Check status and attempt deletion
                    if tape_status in ['AVAILABLE', 'RETRIEVED']:  # Only AVAILABLE/RETRIEVED tapes can be deleted via gateway
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
            
            # Process archived expired tapes for deletion
            if not dry_run:
                logger.info(f"Processing {archived_tapes_count} archived expired tapes for deletion from VTS...")
                for tape in expired_tapes:
                    if tape.get('TapeStatus') != 'ARCHIVED':
                        continue
                    
                    tape_arn = tape['TapeARN']
                    tape_barcode = tape.get('TapeBarcode', 'Unknown')
                    
                    logger.info(f"Deleting archived tape from VTS: {tape_barcode}")
                    if self.delete_virtual_tape(tape_arn, bypass_governance):
                        results['deleted_tapes'] += 1
                    else:
                        results['failed_deletions'] += 1
                        results['errors'].append(f"Failed to delete archived tape {tape_barcode}")
            else:
                # Dry-run mode for archived tapes
                for tape in expired_tapes:
                    if tape.get('TapeStatus') != 'ARCHIVED':
                        continue
                    tape_barcode = tape.get('TapeBarcode', 'Unknown')
                    tape_arn = tape['TapeARN']
                    logger.info(f"DRY RUN: Would delete archived tape from VTS: {tape_barcode} ({tape_arn})")
                    results['deleted_tapes'] += 1
            
            # Update summary information
            if archived_tapes_count > 0:
                logger.info(f"Note: {archived_tapes_count} expired tapes are archived in VTS")
                if not dry_run:
                    logger.info("Archived tapes are deleted directly from VTS using DeleteTapeArchive API")
                else:
                    logger.info("Archived tapes would be deleted directly from VTS using DeleteTapeArchive API")

        except Exception as e:
            # Catch any unexpected errors during the process
            logger.error(f"Error in delete_expired_tapes: {e}")
            results['errors'].append(str(e))

        return results

    def delete_specific_tapes(self, tape_list: List[str], dry_run: bool = True, 
                            bypass_governance: bool = False) -> Dict:
        """
        Delete specific virtual tapes provided in a list
        
        This method allows deletion of specific tapes identified by their ARNs
        or barcodes, rather than using age-based expiry criteria. Useful for
        targeted cleanup or when specific tapes need to be removed.
        
        Args:
            tape_list (List[str]): List of tape ARNs or barcodes to delete
            dry_run (bool): If True, only simulate deletion without actually deleting
            bypass_governance (bool): Whether to bypass governance retention policies
        
        Returns:
            Dict: Results summary containing:
                - total_tapes_requested: Number of tapes in the input list
                - tapes_found: Number of requested tapes that were found
                - tapes_not_found: Number of requested tapes that were not found
                - deleted_tapes: Number of tapes successfully deleted
                - failed_deletions: Number of deletion attempts that failed
                - errors: List of error messages encountered
        
        Note:
            - Input can be either tape ARNs or barcodes
            - Only tapes in deletable states will be processed
            - Provides detailed reporting on each tape's processing status
        """
        results = {
            'total_tapes_requested': len(tape_list),
            'tapes_found': 0,
            'tapes_not_found': 0,
            'deleted_tapes': 0,
            'failed_deletions': 0,
            'errors': [],
            'not_found_tapes': [],
            'processed_tapes': []
        }

        try:
            logger.info(f"Processing {len(tape_list)} specific tapes for deletion")
            
            # Step 1: Get all available tapes to match against the provided list
            all_tapes = self.list_virtual_tapes()
            if not all_tapes:
                logger.warning("No virtual tapes found in the system")
                results['errors'].append("No virtual tapes found in the system")
                return results

            # Step 2: Get detailed information for all tapes
            tape_arns = [tape['TapeARN'] for tape in all_tapes]
            detailed_tapes = self.get_tape_details(tape_arns)

            # Step 3: Create lookup dictionaries for both ARNs and barcodes
            tape_by_arn = {tape['TapeARN']: tape for tape in detailed_tapes}
            tape_by_barcode = {tape.get('TapeBarcode', ''): tape for tape in detailed_tapes}

            # Step 4: Process each tape in the provided list
            for tape_identifier in tape_list:
                tape_identifier = tape_identifier.strip()
                logger.info(f"Processing tape identifier: {tape_identifier}")
                
                # Try to find the tape by ARN first, then by barcode
                target_tape = None
                if tape_identifier in tape_by_arn:
                    target_tape = tape_by_arn[tape_identifier]
                elif tape_identifier in tape_by_barcode:
                    target_tape = tape_by_barcode[tape_identifier]
                
                if not target_tape:
                    # Tape not found
                    logger.warning(f"Tape not found: {tape_identifier}")
                    results['tapes_not_found'] += 1
                    results['not_found_tapes'].append(tape_identifier)
                    results['errors'].append(f"Tape not found: {tape_identifier}")
                    continue

                # Tape found - extract information
                results['tapes_found'] += 1
                tape_arn = target_tape['TapeARN']
                tape_barcode = target_tape.get('TapeBarcode', 'Unknown')
                tape_status = target_tape.get('TapeStatus', 'Unknown')
                
                tape_info = {
                    'identifier': tape_identifier,
                    'arn': tape_arn,
                    'barcode': tape_barcode,
                    'status': tape_status,
                    'action_taken': None,
                    'success': False
                }
                
                logger.info(f"Found tape: {tape_barcode} (Status: {tape_status})")
                
                if dry_run:
                    # Dry-run mode: Log what would be deleted
                    logger.info(f"DRY RUN: Would delete tape {tape_barcode} ({tape_arn})")
                    tape_info['action_taken'] = 'would_delete'
                    tape_info['success'] = True
                    results['deleted_tapes'] += 1
                else:
                    # Actual deletion mode: Check status and attempt deletion
                    if tape_status in ['AVAILABLE', 'ARCHIVED']:
                        if self.delete_virtual_tape(tape_arn, bypass_governance):
                            tape_info['action_taken'] = 'deleted'
                            tape_info['success'] = True
                            results['deleted_tapes'] += 1
                        else:
                            tape_info['action_taken'] = 'delete_failed'
                            tape_info['success'] = False
                            results['failed_deletions'] += 1
                            results['errors'].append(f"Failed to delete {tape_barcode}")
                    else:
                        # Skip tapes that are not in a deletable state
                        logger.warning(f"Skipping tape {tape_barcode} - Status: {tape_status} (not deletable)")
                        tape_info['action_taken'] = 'skipped_not_deletable'
                        tape_info['success'] = False
                        results['errors'].append(f"Tape {tape_barcode} not in deletable state: {tape_status}")

                results['processed_tapes'].append(tape_info)

        except Exception as e:
            logger.error(f"Error in delete_specific_tapes: {e}")
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
    
    # Operation mode flags - mutually exclusive group
    operation_group = parser.add_mutually_exclusive_group(required=False)
    operation_group.add_argument('--list-all', action='store_true',
                               help='List all virtual tapes with detailed information (inventory mode)')
    operation_group.add_argument('--delete-expired', action='store_true', default=True,
                               help='Delete expired tapes based on age threshold (default mode)')
    operation_group.add_argument('--delete-specific', action='store_true',
                               help='Delete specific tapes from a provided list')
    
    # Tape list specification options
    parser.add_argument('--tape-list', 
                       help='Comma-separated list of tape ARNs or barcodes to delete (use with --delete-specific)')
    parser.add_argument('--tape-file', 
                       help='File containing list of tape ARNs or barcodes (one per line, use with --delete-specific)')
    
    # Output options
    parser.add_argument('--output-file', 
                       help='Save results to file. For --list-all: tape barcodes (one per line). For other modes: detailed results summary')
    
    # Status filter options
    parser.add_argument('--status-filter', 
                       help='Filter tapes by status (use with --list-all). Comma-separated list. Valid values: AVAILABLE, RETRIEVED, ARCHIVED, CREATING, IN_TRANSIT_TO_VTS, DELETING, DELETED, IRRECOVERABLE, RECOVERING. Example: --status-filter AVAILABLE,RETRIEVED')
    
    # Parse command-line arguments
    args = parser.parse_args()

    # Validate operation mode and required parameters
    if args.delete_specific and not args.tape_list and not args.tape_file:
        logger.error("--delete-specific requires either --tape-list or --tape-file")
        sys.exit(1)
    
    if (args.tape_list or args.tape_file) and not args.delete_specific:
        logger.error("--tape-list and --tape-file can only be used with --delete-specific")
        sys.exit(1)
    
    if args.status_filter and not args.list_all:
        logger.error("--status-filter can only be used with --list-all")
        sys.exit(1)

    # Determine execution mode: dry-run is default unless --execute is specified
    # This provides an extra safety layer to prevent accidental deletions
    dry_run = not args.execute

    # Determine operation mode
    if args.list_all:
        operation_mode = "list_all"
        if args.output_file:
            logger.info(f"Output file: {args.output_file}")
    elif args.delete_specific:
        operation_mode = "delete_specific"
    else:
        operation_mode = "delete_expired"  # Default mode

    # Parse status filter if provided
    status_filter = None
    if args.status_filter:
        status_filter = [status.strip().upper() for status in args.status_filter.split(',') if status.strip()]
        # Validate status values
        valid_statuses = ['AVAILABLE', 'RETRIEVED', 'ARCHIVED', 'CREATING', 'IN_TRANSIT_TO_VTS', 'DELETING', 'DELETED', 'IRRECOVERABLE', 'RECOVERING']
        invalid_statuses = [s for s in status_filter if s not in valid_statuses]
        if invalid_statuses:
            logger.error(f"Invalid status values: {', '.join(invalid_statuses)}")
            logger.error(f"Valid statuses: {', '.join(valid_statuses)}")
            sys.exit(1)
        logger.info(f"Status filter: {', '.join(status_filter)}")
    
    # Parse tape list if provided
    tape_list = []
    if args.delete_specific:
        if args.tape_list:
            # Parse comma-separated list
            tape_list = [tape.strip() for tape in args.tape_list.split(',') if tape.strip()]
        elif args.tape_file:
            # Read from file
            try:
                with open(args.tape_file, 'r') as f:
                    tape_list = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
            except FileNotFoundError:
                logger.error(f"Tape file not found: {args.tape_file}")
                sys.exit(1)
            except Exception as e:
                logger.error(f"Error reading tape file {args.tape_file}: {e}")
                sys.exit(1)
        
        if not tape_list:
            logger.error("No tapes specified for operation")
            sys.exit(1)

    # Log startup information for audit trail
    logger.info("="*60)
    logger.info("Starting Virtual Tape Management Process")
    logger.info("="*60)
    logger.info(f"Operation mode: {operation_mode}")
    logger.info(f"Region: {args.region}")
    logger.info(f"Profile: {args.profile or 'default'}")
    if operation_mode == "list_all" and status_filter:
        logger.info(f"Status filter: {', '.join(status_filter)}")
    if operation_mode == "delete_expired":
        logger.info(f"Expiry threshold: {args.expiry_days} days")
    elif operation_mode == "delete_specific":
        logger.info(f"Tapes to process: {len(tape_list)}")
    logger.info(f"Gateway ARN: {args.gateway_arn or 'all gateways'}")
    if operation_mode != "list_all":
        logger.info(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
        logger.info(f"Bypass governance: {args.bypass_governance}")
    logger.info("="*60)

    # Initialize the tape manager with specified AWS configuration
    tape_manager = VirtualTapeManager(args.region, args.profile)

    # Execute the appropriate operation based on mode
    if operation_mode == "list_all":
        # List all tapes mode
        results = tape_manager.list_all_tapes_detailed(args.gateway_arn, status_filter)
        
        # Save tape list to file if requested
        if args.output_file:
            try:
                with open(args.output_file, 'w') as f:
                    f.write("# Virtual Tape List\n")
                    f.write(f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# Region: {args.region}\n")
                    f.write(f"# Gateway: {args.gateway_arn or 'all gateways'}\n")
                    if status_filter:
                        f.write(f"# Status filter: {', '.join(status_filter)}\n")
                        f.write(f"# Total tapes (before filter): {results['total_tapes']}\n")
                        f.write(f"# Filtered tapes: {len(results.get('tape_details', []))}\n")
                    else:
                        f.write(f"# Total tapes: {len(results.get('tape_details', []))}\n")
                    f.write("#\n")
                    f.write("# Format: One tape barcode per line\n")
                    f.write("# Use this file with --delete-specific --tape-file\n")
                    f.write("#\n\n")
                    
                    # Write tape barcodes, one per line
                    if results.get('tape_details'):
                        for tape in results['tape_details']:
                            f.write(f"{tape['barcode']}\n")
                    else:
                        if status_filter:
                            f.write(f"# No tapes found matching status filter: {', '.join(status_filter)}\n")
                        else:
                            f.write("# No tapes found\n")
                
                logger.info(f"Tape list saved to: {args.output_file}")
                print(f"\nTape list saved to: {args.output_file}")
                
                if results.get('tape_details'):
                    print(f"Use with: python3 {sys.argv[0]} --region {args.region} --delete-specific --tape-file {args.output_file}")
                else:
                    if status_filter:
                        print(f"File created but contains no tapes matching status filter: {', '.join(status_filter)}")
                    else:
                        print("File created but contains no tapes (none were found)")
                
            except Exception as e:
                logger.error(f"Failed to save tape list to file: {e}")
                print(f"Error: Failed to save tape list to {args.output_file}: {e}")
        
        # Display comprehensive tape inventory
        print("\n" + "="*60)
        print("VIRTUAL TAPE INVENTORY")
        print("="*60)
        
        if results['total_tapes'] == 0:
            print("No virtual tapes found.")
            print("\nPossible reasons:")
            print("  - No Storage Gateways exist in this region")
            print("  - No virtual tapes have been created")
            print("  - Insufficient IAM permissions")
            print("  - Incorrect region specified")
        else:
            print(f"Total tapes found: {results['total_tapes']}")
            if status_filter:
                print(f"Status filter applied: {', '.join(status_filter)}")
                print(f"Tapes matching filter: {results['filtered_tapes']}")
                if results['filtered_tapes'] == 0:
                    print(f"\nNo tapes found with status: {', '.join(status_filter)}")
                    print("\nAvailable statuses in this region:")
                    all_tapes_result = tape_manager.list_all_tapes_detailed(args.gateway_arn, None)
                    if all_tapes_result.get('tapes_by_status'):
                        for status in all_tapes_result['tapes_by_status'].keys():
                            print(f"  - {status}")
            
            if results['filtered_tapes'] > 0:
                print(f"Total allocated size: {results['total_size_bytes']:,} bytes ({results['total_size_bytes'] / (1024**3):.2f} GB)")
                print(f"Total used size: {results['total_used_bytes']:,} bytes ({results['total_used_bytes'] / (1024**3):.2f} GB)")
                
                # Display tapes by status
                if results['tapes_by_status']:
                    print(f"\nTapes by status:")
                    for status, tapes in results['tapes_by_status'].items():
                        print(f"  {status}: {len(tapes)} tapes")
                
                # Display detailed tape information
                if results['tape_details']:
                    print(f"\nDetailed tape information:")
                    print(f"{'Barcode':<15} {'Status':<12} {'Age (days)':<10} {'Size (GB)':<10} {'Used (GB)':<10}")
                    print("-" * 70)
                    for tape in results['tape_details']:
                        size_gb = tape['size_bytes'] / (1024**3) if tape['size_bytes'] else 0
                        used_gb = tape['used_bytes'] / (1024**3) if tape['used_bytes'] else 0
                        age_str = str(tape['age_days']) if tape['age_days'] is not None else 'Unknown'
                        print(f"{tape['barcode']:<15} {tape['status']:<12} {age_str:<10} {size_gb:<10.2f} {used_gb:<10.2f}")
        
        # Display any errors
        if results['errors']:
            print(f"\nErrors encountered:")
            for error in results['errors']:
                print(f"  - {error}")
                
    elif operation_mode == "delete_specific":
        # Delete specific tapes mode
        results = tape_manager.delete_specific_tapes(
            tape_list=tape_list,
            dry_run=dry_run,
            bypass_governance=args.bypass_governance
        )
        
        # Display specific tape deletion results
        print("\n" + "="*60)
        print("SPECIFIC TAPE DELETION RESULTS")
        print("="*60)
        print(f"Tapes requested for deletion: {results['total_tapes_requested']}")
        print(f"Tapes found: {results['tapes_found']}")
        print(f"Tapes not found: {results['tapes_not_found']}")
        print(f"{'Would delete' if dry_run else 'Deleted'}: {results['deleted_tapes']}")
        print(f"Failed deletions: {results['failed_deletions']}")
        
        # Display detailed processing results
        if results['processed_tapes']:
            print(f"\nDetailed processing results:")
            print(f"{'Identifier':<20} {'Barcode':<15} {'Status':<12} {'Action':<20}")
            print("-" * 75)
            for tape in results['processed_tapes']:
                print(f"{tape['identifier']:<20} {tape['barcode']:<15} {tape['status']:<12} {tape['action_taken']:<20}")
        
        # Display not found tapes
        if results['not_found_tapes']:
            print(f"\nTapes not found:")
            for tape_id in results['not_found_tapes']:
                print(f"  - {tape_id}")
        
        # Display errors
        if results['errors']:
            print(f"\nErrors encountered:")
            for error in results['errors']:
                print(f"  - {error}")
        
        # Save results to file if requested
        if args.output_file:
            try:
                with open(args.output_file, 'w') as f:
                    f.write("# Specific Tape Deletion Results\n")
                    f.write(f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# Region: {args.region}\n")
                    f.write(f"# Mode: {'DRY RUN' if dry_run else 'EXECUTE'}\n")
                    f.write("#\n")
                    f.write(f"# Tapes requested: {results['total_tapes_requested']}\n")
                    f.write(f"# Tapes found: {results['tapes_found']}\n")
                    f.write(f"# Tapes not found: {results['tapes_not_found']}\n")
                    f.write(f"# {'Would delete' if dry_run else 'Deleted'}: {results['deleted_tapes']}\n")
                    f.write(f"# Failed deletions: {results['failed_deletions']}\n")
                    f.write("#\n\n")
                    
                    # Write processed tapes
                    if results['processed_tapes']:
                        f.write("# Processed Tapes:\n")
                        f.write("# Identifier\tBarcode\tStatus\tAction\tSuccess\n")
                        for tape in results['processed_tapes']:
                            f.write(f"{tape['identifier']}\t{tape['barcode']}\t{tape['status']}\t{tape['action_taken']}\t{tape['success']}\n")
                        f.write("\n")
                    
                    # Write not found tapes
                    if results['not_found_tapes']:
                        f.write("# Tapes Not Found:\n")
                        for tape_id in results['not_found_tapes']:
                            f.write(f"# {tape_id}\n")
                        f.write("\n")
                    
                    # Write errors
                    if results['errors']:
                        f.write("# Errors:\n")
                        for error in results['errors']:
                            f.write(f"# {error}\n")
                
                logger.info(f"Deletion results saved to: {args.output_file}")
                print(f"\nDeletion results saved to: {args.output_file}")
                
            except Exception as e:
                logger.error(f"Failed to save deletion results to file: {e}")
                print(f"Error: Failed to save results to {args.output_file}: {e}")
                
    else:
        # Delete expired tapes mode (default)
        results = tape_manager.delete_expired_tapes(
            expiry_days=args.expiry_days,
            dry_run=dry_run,
            gateway_arn=args.gateway_arn,
            bypass_governance=args.bypass_governance
        )
        
        # Display expired tape deletion results
        print("\n" + "="*50)
        print("EXPIRED TAPE CLEANUP RESULTS")
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
        
        # Save results to file if requested
        if args.output_file:
            try:
                with open(args.output_file, 'w') as f:
                    f.write("# Expired Tape Cleanup Results\n")
                    f.write(f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# Region: {args.region}\n")
                    f.write(f"# Gateway: {args.gateway_arn or 'all gateways'}\n")
                    f.write(f"# Expiry threshold: {args.expiry_days} days\n")
                    f.write(f"# Mode: {'DRY RUN' if dry_run else 'EXECUTE'}\n")
                    f.write("#\n")
                    f.write(f"# Total tapes found: {results['total_tapes']}\n")
                    f.write(f"# Expired tapes: {results['expired_tapes']}\n")
                    f.write(f"# {'Would delete' if dry_run else 'Deleted'}: {results['deleted_tapes']}\n")
                    f.write(f"# Failed deletions: {results['failed_deletions']}\n")
                    f.write("#\n\n")
                    
                    # Write errors
                    if results['errors']:
                        f.write("# Errors:\n")
                        for error in results['errors']:
                            f.write(f"# {error}\n")
                        f.write("\n")
                    
                    # Write summary
                    f.write("# Summary:\n")
                    f.write(f"# Operation completed successfully\n")
                    if dry_run and results['expired_tapes'] > 0:
                        f.write(f"# To execute deletion, run with --execute flag\n")
                
                logger.info(f"Cleanup results saved to: {args.output_file}")
                print(f"\nCleanup results saved to: {args.output_file}")
                
            except Exception as e:
                logger.error(f"Failed to save cleanup results to file: {e}")
                print(f"Error: Failed to save results to {args.output_file}: {e}")

    # Log completion
    logger.info("Virtual Tape Cleanup Process Completed")


# Standard Python idiom to run main() only when script is executed directly
# This allows the script to be imported as a module without running main()
if __name__ == "__main__":
    main()