#!/usr/bin/env python3
"""
AWS Virtual Tape Manager - Core Module

Handles all AWS Storage Gateway tape operations.
"""

import boto3
from botocore.exceptions import ClientError, BotoCoreError, EndpointConnectionError
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
import time

logger = logging.getLogger(__name__)


class TapeManager:
    """Manages AWS Storage Gateway Virtual Tapes"""
    
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    
    def __init__(self, region: str, profile: Optional[str] = None):
        """Initialize tape manager with AWS credentials"""
        try:
            session = boto3.Session(profile_name=profile) if profile else boto3.Session()
            self.storagegateway = session.client('storagegateway', region_name=region)
            self.region = region
            logger.info(f"Connected to AWS Storage Gateway in {region}")
        except Exception as e:
            logger.error(f"Failed to connect to AWS: {e}")
            raise
    
    def list_tapes(self, status_filter: Optional[List[str]] = None) -> List[Dict]:
        """
        List all virtual tapes
        
        Args:
            status_filter: Optional list of statuses to filter (e.g., ['AVAILABLE', 'ARCHIVED'])
        
        Returns:
            List of tape dictionaries with barcode, status, size info
        """
        try:
            all_tapes = []
            marker = None
            
            while True:
                params = {'Limit': 100}
                if marker:
                    params['Marker'] = marker
                
                response = self._retry_api_call(
                    self.storagegateway.list_tapes,
                    **params
                )
                
                tapes = response.get('TapeInfos', [])
                
                # Apply status filter if specified
                if status_filter:
                    tapes = [t for t in tapes if t.get('TapeStatus') in status_filter]
                
                all_tapes.extend(tapes)
                
                marker = response.get('Marker')
                if not marker:
                    break
            
            logger.info(f"Found {len(all_tapes)} tapes")
            return all_tapes
            
        except Exception as e:
            logger.error(f"Failed to list tapes: {e}")
            return []
    
    def delete_tape(self, tape_arn: str, tape_status: str) -> bool:
        """
        Delete a single tape (active or archived)
        
        Args:
            tape_arn: ARN of the tape to delete
            tape_status: Current status of the tape
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if tape_status == 'ARCHIVED':
                # Delete from VTS
                self._retry_api_call(
                    self.storagegateway.delete_tape_archive,
                    TapeARN=tape_arn
                )
                logger.info(f"Deleted archived tape: {tape_arn}")
            else:
                # Delete from gateway
                gateway_arn = self._find_gateway_for_tape(tape_arn)
                if not gateway_arn:
                    logger.error(f"Could not find gateway for tape: {tape_arn}")
                    return False
                
                self._retry_api_call(
                    self.storagegateway.delete_tape,
                    GatewayARN=gateway_arn,
                    TapeARN=tape_arn
                )
                logger.info(f"Deleted active tape: {tape_arn}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete tape {tape_arn}: {e}")
            return False
    
    def _find_gateway_for_tape(self, tape_arn: str) -> Optional[str]:
        """Find which gateway owns a tape"""
        try:
            response = self._retry_api_call(
                self.storagegateway.list_gateways,
                Limit=100
            )
            
            for gateway in response.get('Gateways', []):
                gateway_arn = gateway.get('GatewayARN')
                if not gateway_arn:
                    continue
                
                try:
                    tape_response = self.storagegateway.describe_tapes(
                        GatewayARN=gateway_arn,
                        TapeARNs=[tape_arn]
                    )
                    if tape_response.get('Tapes'):
                        return gateway_arn
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding gateway: {e}")
            return None
    
    def _retry_api_call(self, func, **kwargs):
        """Retry API calls with exponential backoff"""
        for attempt in range(self.MAX_RETRIES):
            try:
                return func(**kwargs)
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                
                if error_code in ['ThrottlingException', 'RequestLimitExceeded']:
                    if attempt < self.MAX_RETRIES - 1:
                        delay = self.RETRY_DELAY * (2 ** attempt)
                        logger.warning(f"Rate limited, retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                raise
            except Exception:
                raise
        
        raise Exception(f"Failed after {self.MAX_RETRIES} retries")
