#!/usr/bin/env python3
"""
Diagnostic script to troubleshoot virtual tape discovery issues
"""

import boto3
import argparse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def diagnose_tape_discovery(region, profile=None):
    """Diagnose tape discovery issues step by step"""
    
    try:
        # Initialize AWS client
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        storagegateway = session.client('storagegateway', region_name=region)
        
        print("="*60)
        print("VIRTUAL TAPE DISCOVERY DIAGNOSTIC")
        print("="*60)
        
        # Step 1: Test basic connectivity
        print("\n1. Testing AWS connectivity...")
        try:
            sts = session.client('sts')
            identity = sts.get_caller_identity()
            print(f"   ✓ Connected as: {identity.get('Arn', 'Unknown')}")
            print(f"   ✓ Account: {identity.get('Account', 'Unknown')}")
        except Exception as e:
            print(f"   ✗ Connection failed: {e}")
            return
        
        # Step 2: List gateways
        print(f"\n2. Discovering Storage Gateways in {region}...")
        try:
            gateways_response = storagegateway.list_gateways(Limit=100)
            gateways = gateways_response.get('Gateways', [])
            print(f"   ✓ Found {len(gateways)} Storage Gateway(s)")
            
            for i, gw in enumerate(gateways, 1):
                print(f"   Gateway {i}:")
                print(f"     Name: {gw.get('GatewayName', 'Unknown')}")
                print(f"     ARN: {gw.get('GatewayARN', 'No ARN')}")
                print(f"     Type: {gw.get('GatewayType', 'Unknown')}")
                print(f"     Status: {gw.get('GatewayOperationalState', 'Unknown')}")
                
        except Exception as e:
            print(f"   ✗ Failed to list gateways: {e}")
            return
        
        if not gateways:
            print("   ⚠ No Storage Gateways found - this explains why no tape details are retrieved")
            return
        
        # Step 3: List all tapes
        print(f"\n3. Listing all virtual tapes...")
        try:
            all_tapes = []
            marker = None
            
            while True:
                params = {'Limit': 100}
                if marker:
                    params['Marker'] = marker
                
                response = storagegateway.list_tapes(**params)
                tapes = response.get('TapeInfos', [])
                all_tapes.extend(tapes)
                
                marker = response.get('Marker')
                if not marker:
                    break
                    
                print(f"   Retrieved {len(tapes)} tapes, continuing...")
            
            print(f"   ✓ Found {len(all_tapes)} total virtual tapes")
            
            # Show sample tape ARNs
            if all_tapes:
                print("   Sample tape ARNs:")
                for i, tape in enumerate(all_tapes[:3], 1):
                    print(f"     {i}. {tape.get('TapeARN', 'No ARN')}")
                    print(f"        Barcode: {tape.get('TapeBarcode', 'Unknown')}")
                    print(f"        Status: {tape.get('TapeStatus', 'Unknown')}")
                    
        except Exception as e:
            print(f"   ✗ Failed to list tapes: {e}")
            return
        
        if not all_tapes:
            print("   ⚠ No virtual tapes found")
            return
        
        # Step 4: Test describe_tapes for each gateway
        print(f"\n4. Testing describe_tapes for each gateway...")
        
        # Take a small sample of tapes for testing
        test_tape_arns = [tape['TapeARN'] for tape in all_tapes[:5]]
        print(f"   Testing with {len(test_tape_arns)} sample tapes")
        
        total_found = 0
        
        for i, gw in enumerate(gateways, 1):
            gateway_arn = gw.get('GatewayARN')
            gateway_name = gw.get('GatewayName', 'Unknown')
            
            print(f"\n   Gateway {i}: {gateway_name}")
            print(f"   ARN: {gateway_arn}")
            
            try:
                # Try to get details for sample tapes
                response = storagegateway.describe_tapes(
                    GatewayARN=gateway_arn,
                    TapeARNs=test_tape_arns
                )
                
                detailed_tapes = response.get('Tapes', [])
                print(f"     ✓ Found {len(detailed_tapes)} tapes in this gateway")
                total_found += len(detailed_tapes)
                
                # Show sample details
                for tape in detailed_tapes[:2]:
                    print(f"       - {tape.get('TapeBarcode', 'Unknown')}: {tape.get('TapeStatus', 'Unknown')}")
                    
            except Exception as e:
                error_msg = str(e)
                if "InvalidGatewayRequestException" in error_msg:
                    print(f"     ○ Gateway doesn't have these tapes (normal)")
                elif "does not exist" in error_msg or "not found" in error_msg:
                    print(f"     ✗ Gateway not found: {e}")
                else:
                    print(f"     ✗ Unexpected error: {e}")
        
        print(f"\n5. Summary:")
        print(f"   Total gateways: {len(gateways)}")
        print(f"   Total tapes (list_tapes): {len(all_tapes)}")
        print(f"   Tapes found via describe_tapes: {total_found}")
        
        if total_found == 0:
            print(f"\n⚠ ISSUE IDENTIFIED:")
            print(f"   - list_tapes finds {len(all_tapes)} tapes")
            print(f"   - describe_tapes finds 0 tapes across all gateways")
            print(f"   - This suggests the tapes might be in a different state or")
            print(f"     the gateways returned by list_gateways don't own these tapes")
            
            print(f"\n🔍 RECOMMENDATIONS:")
            print(f"   1. Check if tapes are in VTS (Virtual Tape Shelf) - archived tapes")
            print(f"   2. Verify gateway operational status")
            print(f"   3. Check if tapes are in transit or being processed")
            print(f"   4. Try querying with a specific gateway ARN if known")
        
    except Exception as e:
        print(f"Diagnostic failed: {e}")

def main():
    parser = argparse.ArgumentParser(description='Diagnose virtual tape discovery issues')
    parser.add_argument('--region', required=True, help='AWS region')
    parser.add_argument('--profile', help='AWS profile to use')
    
    args = parser.parse_args()
    
    diagnose_tape_discovery(args.region, args.profile)

if __name__ == "__main__":
    main()