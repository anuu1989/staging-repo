#!/usr/bin/env python3
"""
Test script to verify ARN parsing logic for tape and gateway ARNs
"""

def test_arn_parsing():
    """Test the ARN parsing logic used in get_tape_details"""
    
    # Sample tape ARNs
    test_tape_arns = [
        "arn:aws:storagegateway:us-east-1:123456789012:tape/sgw-12345678/VTL001",
        "arn:aws:storagegateway:ap-southeast-1:123456789012:tape/sgw-87654321/TAPE002",
        "arn:aws:storagegateway:eu-west-1:123456789012:tape/sgw-11111111/BACKUP003"
    ]
    
    print("Testing ARN parsing logic:")
    print("=" * 60)
    
    tapes_by_gateway = {}
    
    for tape_arn in test_tape_arns:
        print(f"\nProcessing tape ARN: {tape_arn}")
        
        try:
            # Extract gateway ARN from tape ARN
            arn_parts = tape_arn.split(':')
            print(f"  ARN parts: {arn_parts}")
            
            if len(arn_parts) >= 6:
                resource_part = arn_parts[5]  # tape/gateway-id/tape-id
                print(f"  Resource part: {resource_part}")
                
                resource_parts = resource_part.split('/')
                print(f"  Resource parts: {resource_parts}")
                
                if len(resource_parts) >= 2:
                    gateway_id = resource_parts[1]
                    print(f"  Gateway ID: {gateway_id}")
                    
                    # Reconstruct gateway ARN
                    gateway_arn = f"{':'.join(arn_parts[:5])}:gateway/{gateway_id}"
                    print(f"  Gateway ARN: {gateway_arn}")
                    
                    if gateway_arn not in tapes_by_gateway:
                        tapes_by_gateway[gateway_arn] = []
                    tapes_by_gateway[gateway_arn].append(tape_arn)
                    
                    print(f"  ✓ Successfully parsed")
                else:
                    print(f"  ✗ Invalid resource format")
            else:
                print(f"  ✗ Invalid ARN format")
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print(f"\n" + "=" * 60)
    print("Final grouping by gateway:")
    for gateway_arn, tape_arns in tapes_by_gateway.items():
        print(f"\nGateway: {gateway_arn}")
        for tape_arn in tape_arns:
            print(f"  - {tape_arn}")

if __name__ == "__main__":
    test_arn_parsing()