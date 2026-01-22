# Implementation Plan: Virtual Tape Cleanup for AP-PROD AWS Account

## Project Overview

**Objective**: Implement automated cleanup of expired virtual tapes in the AP-PROD AWS account using the virtual tape management script.

**Scope**: Deploy and configure the virtual tape cleanup solution to run from local machines with aws-azure-login authentication.

**Timeline**: 2-3 weeks implementation with 1 week testing and validation.

---

## 1. Prerequisites and Requirements

### 1.1 Technical Requirements

#### Local Machine Setup
- **Operating System**: macOS (as indicated by current environment)
- **Python**: Version 3.6 or higher
- **AWS CLI**: Version 2.x recommended
- **aws-azure-login**: Configured and working
- **Network Access**: Connectivity to AWS Storage Gateway APIs in AP region

#### AWS Account Requirements
- **Account**: ap-prod AWS account
- **Region**: Likely ap-southeast-1, ap-southeast-2, or ap-northeast-1 (to be confirmed)
- **Storage Gateway**: Existing Virtual Tape Library (VTL) configuration
- **IAM Permissions**: Required permissions for Storage Gateway operations

### 1.2 Access Requirements

#### Authentication Method
- **Primary**: aws-azure-login (Azure AD integration)
- **Session Duration**: Typically 1-12 hours (to be confirmed)
- **MFA**: Multi-factor authentication required
- **Profile**: Dedicated AWS profile for ap-prod account

#### Required IAM Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "storagegateway:ListGateways",
                "storagegateway:ListTapes",
                "storagegateway:DescribeTapes",
                "storagegateway:DeleteTape"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:RequestedRegion": ["ap-southeast-1", "ap-southeast-2", "ap-northeast-1"]
                }
            }
        }
    ]
}
```

---

## 2. Pre-Implementation Assessment

### 2.1 Environment Discovery

#### Storage Gateway Inventory
- [ ] Identify all Storage Gateways in AP regions
- [ ] Document gateway ARNs and names
- [ ] Assess current virtual tape inventory
- [ ] Identify tape retention policies
- [ ] Document tape naming conventions

#### Current State Analysis
```bash
# Discovery commands to run after authentication
aws-azure-login --profile ap-prod
aws storagegateway list-gateways --profile ap-prod --region ap-southeast-1
aws storagegateway list-tapes --profile ap-prod --region ap-southeast-1 --limit 10
```

### 2.2 Risk Assessment

#### High Risk Items
- **Data Loss**: Permanent deletion of virtual tapes
- **Compliance**: Regulatory retention requirements
- **Business Impact**: Disruption to backup/restore operations
- **Access Control**: Unauthorized tape deletion

#### Mitigation Strategies
- **Dry-run Testing**: Extensive testing before production execution
- **Approval Process**: Management sign-off for tape deletion lists
- **Backup Verification**: Ensure data exists in alternative locations
- **Audit Logging**: Comprehensive logging of all operations

---

## 3. Implementation Phases

### Phase 1: Setup and Configuration (Week 1)

#### 3.1 Local Environment Setup

**Day 1-2: Tool Installation and Configuration**

1. **Install Required Tools**
   ```bash
   # Install Python dependencies
   pip3 install boto3
   
   # Verify aws-azure-login
   aws-azure-login --version
   
   # Test AWS CLI access
   aws sts get-caller-identity --profile ap-prod
   ```

2. **Download and Configure Scripts**
   ```bash
   # Create project directory
   mkdir -p ~/aws-tape-cleanup/ap-prod
   cd ~/aws-tape-cleanup/ap-prod
   
   # Download scripts (assuming from repository)
   curl -O https://raw.githubusercontent.com/company/repo/main/delete_expired_virtual_tapes.py
   curl -O https://raw.githubusercontent.com/company/repo/main/cleanup_tapes.sh
   curl -O https://raw.githubusercontent.com/company/repo/main/requirements.txt
   
   # Make scripts executable
   chmod +x cleanup_tapes.sh
   
   # Install dependencies
   pip3 install -r requirements.txt
   ```

3. **Configure AWS Profile**
   ```bash
   # Configure aws-azure-login for ap-prod
   aws-azure-login --configure --profile ap-prod
   
   # Test authentication
   aws-azure-login --profile ap-prod
   aws sts get-caller-identity --profile ap-prod
   ```

#### 3.2 Initial Discovery and Testing

**Day 3-4: Environment Assessment**

1. **Discover Storage Gateways**
   ```bash
   # Login to ap-prod account
   aws-azure-login --profile ap-prod
   
   # Discover gateways in each AP region
   for region in ap-southeast-1 ap-southeast-2 ap-northeast-1; do
     echo "=== Region: $region ==="
     aws storagegateway list-gateways --profile ap-prod --region $region
   done
   ```

2. **Generate Initial Inventory**
   ```bash
   # For each region with Storage Gateways
   ./cleanup_tapes.sh --region ap-southeast-1 --profile ap-prod --list-all --output-file ap-prod-inventory-$(date +%Y%m%d).txt
   ```

3. **Analyze Current State**
   - Document total number of tapes
   - Identify tape age distribution
   - Assess storage usage and costs
   - Review tape status distribution

**Day 5: Create Configuration Files**

1. **Create Region-Specific Configurations**
   ```bash
   # Create configuration directory
   mkdir -p config
   
   # Create region-specific config files
   cat > config/ap-southeast-1.conf << EOF
   REGION=ap-southeast-1
   PROFILE=ap-prod
   EXPIRY_DAYS=90
   GATEWAY_ARN=arn:aws:storagegateway:ap-southeast-1:123456789012:gateway/sgw-xxxxxxxx
   EOF
   ```

2. **Create Wrapper Scripts**
   ```bash
   # Create region-specific wrapper
   cat > cleanup-ap-prod-apse1.sh << 'EOF'
   #!/bin/bash
   source config/ap-southeast-1.conf
   
   # Ensure authentication
   aws-azure-login --profile $PROFILE
   
   # Execute cleanup
   ./cleanup_tapes.sh --region $REGION --profile $PROFILE "$@"
   EOF
   
   chmod +x cleanup-ap-prod-apse1.sh
   ```

### Phase 2: Testing and Validation (Week 2)

#### 3.3 Comprehensive Testing

**Day 6-8: Dry-Run Testing**

1. **Test All Operation Modes**
   ```bash
   # Test inventory listing
   ./cleanup-ap-prod-apse1.sh --list-all --output-file test-inventory.txt
   
   # Test expired tape identification
   ./cleanup-ap-prod-apse1.sh --delete-expired --expiry-days 180
   
   # Test specific tape deletion (dry-run)
   ./cleanup-ap-prod-apse1.sh --delete-specific --tape-file test-tapes.txt
   ```

2. **Validate Results**
   - Verify tape counts and identification
   - Check expiry date calculations
   - Validate tape status filtering
   - Confirm dry-run safety measures

3. **Error Handling Testing**
   ```bash
   # Test with invalid credentials
   # Test with network issues
   # Test with invalid tape IDs
   # Test with permission errors
   ```

**Day 9-10: Integration Testing**

1. **End-to-End Workflow Testing**
   ```bash
   # Complete workflow test
   ./cleanup-ap-prod-apse1.sh --list-all --output-file full-inventory.txt
   
   # Edit file to select test tapes (if any safe test tapes exist)
   cp full-inventory.txt test-deletion.txt
   # Edit test-deletion.txt to contain only safe test tapes
   
   # Test deletion workflow (dry-run)
   ./cleanup-ap-prod-apse1.sh --delete-specific --tape-file test-deletion.txt
   ```

2. **Authentication Flow Testing**
   ```bash
   # Test session expiration handling
   # Test re-authentication process
   # Test profile switching
   ```

### Phase 3: Production Deployment (Week 3)

#### 3.4 Production Preparation

**Day 11-12: Final Configuration**

1. **Create Production Scripts**
   ```bash
   # Create production-ready wrapper
   cat > production-cleanup.sh << 'EOF'
   #!/bin/bash
   
   set -e
   
   # Configuration
   REGION=${1:-ap-southeast-1}
   PROFILE=ap-prod
   LOG_DIR=logs
   DATE=$(date +%Y%m%d_%H%M%S)
   
   # Create log directory
   mkdir -p $LOG_DIR
   
   # Authenticate
   echo "Authenticating to AWS..."
   aws-azure-login --profile $PROFILE
   
   # Verify authentication
   aws sts get-caller-identity --profile $PROFILE
   
   # Execute with logging
   ./cleanup_tapes.sh --region $REGION --profile $PROFILE "$@" 2>&1 | tee $LOG_DIR/cleanup_${REGION}_${DATE}.log
   EOF
   
   chmod +x production-cleanup.sh
   ```

2. **Create Operational Procedures**
   - Standard Operating Procedures (SOP)
   - Emergency rollback procedures
   - Escalation contacts
   - Approval workflows

#### 3.5 Production Execution

**Day 13-15: Controlled Production Rollout**

1. **Phase 3a: Initial Production Inventory**
   ```bash
   # Generate comprehensive inventory
   ./production-cleanup.sh ap-southeast-1 --list-all --output-file ap-prod-inventory-$(date +%Y%m%d).txt
   
   # Analyze and review inventory
   # Get management approval for deletion criteria
   ```

2. **Phase 3b: First Production Cleanup**
   ```bash
   # Conservative first cleanup (longer expiry period)
   ./production-cleanup.sh ap-southeast-1 --delete-expired --expiry-days 365 --execute
   
   # Monitor and validate results
   ```

3. **Phase 3c: Regular Operations**
   ```bash
   # Establish regular cleanup schedule
   # Document operational procedures
   # Set up monitoring and alerting
   ```

---

## 4. Operational Procedures

### 4.1 Standard Operating Procedure

#### Pre-Execution Checklist
- [ ] Verify aws-azure-login authentication
- [ ] Confirm AWS profile and region
- [ ] Review expiry criteria and business requirements
- [ ] Ensure backup/restore operations are not in progress
- [ ] Obtain necessary approvals for tape deletion

#### Execution Steps
1. **Authenticate to AWS**
   ```bash
   aws-azure-login --profile ap-prod
   ```

2. **Generate Current Inventory**
   ```bash
   ./production-cleanup.sh ap-southeast-1 --list-all --output-file inventory-$(date +%Y%m%d).txt
   ```

3. **Review and Approve Deletion List**
   ```bash
   # For expired tapes
   ./production-cleanup.sh ap-southeast-1 --delete-expired --expiry-days 90
   
   # Review output and get approval
   ```

4. **Execute Deletion**
   ```bash
   # Execute with confirmation
   ./production-cleanup.sh ap-southeast-1 --delete-expired --expiry-days 90 --execute
   ```

5. **Verify Results**
   ```bash
   # Generate post-cleanup inventory
   ./production-cleanup.sh ap-southeast-1 --list-all --output-file post-cleanup-$(date +%Y%m%d).txt
   ```

### 4.2 Scheduled Operations

#### Weekly Inventory Report
```bash
#!/bin/bash
# weekly-inventory.sh

REGIONS="ap-southeast-1 ap-southeast-2 ap-northeast-1"
DATE=$(date +%Y%m%d)

aws-azure-login --profile ap-prod

for region in $REGIONS; do
    ./production-cleanup.sh $region --list-all --output-file weekly-inventory-${region}-${DATE}.txt
done

# Email reports to stakeholders
```

#### Monthly Cleanup
```bash
#!/bin/bash
# monthly-cleanup.sh

REGIONS="ap-southeast-1 ap-southeast-2 ap-northeast-1"
EXPIRY_DAYS=90

aws-azure-login --profile ap-prod

for region in $REGIONS; do
    echo "Processing region: $region"
    
    # Generate deletion preview
    ./production-cleanup.sh $region --delete-expired --expiry-days $EXPIRY_DAYS > preview-${region}.txt
    
    # Wait for approval
    read -p "Proceed with deletion in $region? (y/N): " confirm
    if [[ $confirm == [yY] ]]; then
        ./production-cleanup.sh $region --delete-expired --expiry-days $EXPIRY_DAYS --execute
    fi
done
```

---

## 5. Security and Compliance

### 5.1 Security Measures

#### Access Control
- **Principle of Least Privilege**: Only necessary Storage Gateway permissions
- **Time-Limited Access**: aws-azure-login session timeouts
- **Audit Logging**: All operations logged with timestamps
- **Approval Workflow**: Management approval for production deletions

#### Data Protection
- **Dry-Run First**: Always test before execution
- **Backup Verification**: Confirm data exists elsewhere before deletion
- **Retention Compliance**: Respect regulatory retention requirements
- **Change Control**: Follow established change management processes

### 5.2 Compliance Requirements

#### Audit Trail
- **Operation Logs**: Detailed logs of all tape operations
- **Authentication Logs**: aws-azure-login session records
- **Approval Records**: Documentation of management approvals
- **Change Records**: Tracking of all configuration changes

#### Retention Policies
- **Legal Hold**: Check for legal hold requirements
- **Regulatory Compliance**: Ensure compliance with data retention regulations
- **Business Requirements**: Align with business backup retention policies
- **Documentation**: Maintain records of retention policy decisions

---

## 6. Monitoring and Alerting

### 6.1 Operational Monitoring

#### Key Metrics
- **Tape Count**: Total virtual tapes by region
- **Storage Usage**: Total allocated vs. used storage
- **Deletion Rate**: Tapes deleted per cleanup cycle
- **Error Rate**: Failed operations and reasons
- **Cost Impact**: Storage cost reduction from cleanup

#### Monitoring Implementation
```bash
# Create monitoring script
cat > monitor-tapes.sh << 'EOF'
#!/bin/bash

REGIONS="ap-southeast-1 ap-southeast-2 ap-northeast-1"
ALERT_THRESHOLD=1000  # Alert if more than 1000 tapes

aws-azure-login --profile ap-prod

for region in $REGIONS; do
    count=$(aws storagegateway list-tapes --profile ap-prod --region $region --query 'length(TapeInfos)')
    
    echo "Region $region: $count tapes"
    
    if [ $count -gt $ALERT_THRESHOLD ]; then
        echo "ALERT: High tape count in $region: $count tapes"
        # Send alert notification
    fi
done
EOF
```

### 6.2 Alerting and Notifications

#### Alert Conditions
- **High Tape Count**: Unusual accumulation of tapes
- **Deletion Failures**: Failed tape deletion operations
- **Authentication Issues**: aws-azure-login failures
- **Permission Errors**: IAM permission problems

#### Notification Methods
- **Email Alerts**: Operations team notifications
- **Slack Integration**: Real-time team notifications
- **Dashboard Updates**: Operational dashboard metrics
- **Log Aggregation**: Centralized logging system integration

---

## 7. Risk Management and Contingency

### 7.1 Risk Mitigation

#### Technical Risks
- **Data Loss**: Comprehensive testing and approval processes
- **Service Disruption**: Scheduled maintenance windows
- **Authentication Failure**: Backup authentication methods
- **Script Errors**: Extensive testing and validation

#### Operational Risks
- **Human Error**: Clear procedures and confirmation prompts
- **Unauthorized Access**: Strong access controls and audit logging
- **Compliance Violations**: Regular compliance reviews
- **Business Impact**: Stakeholder communication and approval

### 7.2 Contingency Plans

#### Emergency Procedures
1. **Immediate Stop**: Process to halt ongoing operations
2. **Rollback Plan**: Steps to reverse changes (where possible)
3. **Escalation Path**: Contact information for emergency support
4. **Communication Plan**: Stakeholder notification procedures

#### Recovery Procedures
1. **Data Recovery**: Steps to recover accidentally deleted tapes (if possible)
2. **Service Restoration**: Process to restore normal operations
3. **Root Cause Analysis**: Investigation and remediation procedures
4. **Process Improvement**: Updates to prevent recurrence

---

## 8. Success Criteria and Validation

### 8.1 Success Metrics

#### Technical Success
- [ ] Script executes without errors
- [ ] Correct identification of expired tapes
- [ ] Successful deletion of approved tapes
- [ ] Accurate inventory reporting
- [ ] Proper authentication handling

#### Operational Success
- [ ] Reduced storage costs
- [ ] Improved tape management efficiency
- [ ] Compliance with retention policies
- [ ] Stakeholder satisfaction
- [ ] Minimal operational disruption

### 8.2 Validation Procedures

#### Pre-Production Validation
- [ ] Comprehensive dry-run testing
- [ ] Security review and approval
- [ ] Compliance verification
- [ ] Stakeholder sign-off
- [ ] Documentation review

#### Post-Production Validation
- [ ] Verify expected tape deletions
- [ ] Confirm cost reduction
- [ ] Review audit logs
- [ ] Stakeholder feedback
- [ ] Performance metrics analysis

---

## 9. Documentation and Training

### 9.1 Documentation Requirements

#### Technical Documentation
- **Installation Guide**: Step-by-step setup instructions
- **Configuration Guide**: Parameter and option documentation
- **Troubleshooting Guide**: Common issues and solutions
- **API Reference**: AWS Storage Gateway API usage
- **Security Guide**: Security considerations and best practices

#### Operational Documentation
- **Standard Operating Procedures**: Day-to-day operational procedures
- **Emergency Procedures**: Incident response and escalation
- **Compliance Procedures**: Regulatory and policy compliance
- **Change Management**: Process for making changes
- **Audit Procedures**: Regular review and validation processes

### 9.2 Training Plan

#### Target Audiences
- **Operations Team**: Day-to-day script execution
- **Security Team**: Security review and compliance
- **Management**: Approval processes and oversight
- **Audit Team**: Compliance verification and reporting

#### Training Content
- **Tool Usage**: How to execute scripts and interpret results
- **Security Procedures**: Authentication and access control
- **Compliance Requirements**: Regulatory and policy compliance
- **Emergency Procedures**: Incident response and escalation
- **Troubleshooting**: Common issues and resolution steps

---

## 10. Timeline and Milestones

### Week 1: Setup and Configuration
- **Day 1-2**: Environment setup and tool installation
- **Day 3-4**: Initial discovery and inventory
- **Day 5**: Configuration and wrapper script creation

### Week 2: Testing and Validation
- **Day 6-8**: Comprehensive dry-run testing
- **Day 9-10**: Integration and end-to-end testing

### Week 3: Production Deployment
- **Day 11-12**: Production preparation and final configuration
- **Day 13-15**: Controlled production rollout

### Ongoing Operations
- **Weekly**: Inventory reports and monitoring
- **Monthly**: Scheduled cleanup operations
- **Quarterly**: Compliance reviews and process improvements

---

## 11. Approval and Sign-off

### Required Approvals
- [ ] **Technical Lead**: Technical implementation approval
- [ ] **Security Team**: Security review and approval
- [ ] **Compliance Officer**: Regulatory compliance approval
- [ ] **Operations Manager**: Operational readiness approval
- [ ] **Business Owner**: Business impact and cost approval

### Sign-off Criteria
- [ ] All testing completed successfully
- [ ] Security review passed
- [ ] Compliance requirements met
- [ ] Documentation completed
- [ ] Training delivered
- [ ] Contingency plans in place

---

## Appendices

### Appendix A: Command Reference
```bash
# Authentication
aws-azure-login --profile ap-prod

# Basic inventory
./cleanup_tapes.sh --region ap-southeast-1 --profile ap-prod --list-all

# Save inventory to file
./cleanup_tapes.sh --region ap-southeast-1 --profile ap-prod --list-all --output-file inventory.txt

# Delete expired tapes (dry-run)
./cleanup_tapes.sh --region ap-southeast-1 --profile ap-prod --delete-expired --expiry-days 90

# Delete expired tapes (execute)
./cleanup_tapes.sh --region ap-southeast-1 --profile ap-prod --delete-expired --expiry-days 90 --execute

# Delete specific tapes
./cleanup_tapes.sh --region ap-southeast-1 --profile ap-prod --delete-specific --tape-file tapes.txt --execute
```

### Appendix B: Configuration Templates
```bash
# Region configuration template
REGION=ap-southeast-1
PROFILE=ap-prod
EXPIRY_DAYS=90
GATEWAY_ARN=arn:aws:storagegateway:ap-southeast-1:123456789012:gateway/sgw-xxxxxxxx
LOG_LEVEL=INFO
BACKUP_RETENTION_DAYS=365
```

### Appendix C: Troubleshooting Guide

#### Common Error Messages and Solutions

**"Parameter validation failed: Missing required parameter GatewayARN"**
- **Cause**: AWS Storage Gateway APIs require gateway ARN specification
- **Solution**: Script automatically extracts gateway ARNs from tape ARNs
- **Verification**: Check that tape ARNs follow correct format

**"Unable to locate credentials"**
- **Cause**: AWS credentials not configured or expired
- **Solution**: Run `aws-azure-login --profile ap-prod` to authenticate
- **Verification**: Test with `aws sts get-caller-identity --profile ap-prod`

**"Access Denied" or "UnauthorizedOperation"**
- **Cause**: Insufficient IAM permissions
- **Solution**: Verify IAM policy includes required Storage Gateway permissions
- **Required Actions**: `storagegateway:ListTapes`, `storagegateway:DescribeTapes`, `storagegateway:DeleteTape`

**"No virtual tapes found"**
- **Possible Causes**: 
  - No Storage Gateways in the specified region
  - No virtual tapes created
  - Incorrect region specified
  - Authentication/permission issues
- **Troubleshooting Steps**:
  1. Verify region has Storage Gateways: `aws storagegateway list-gateways --region <region> --profile ap-prod`
  2. Check authentication: `aws sts get-caller-identity --profile ap-prod`
  3. Verify permissions with a simple list operation

### Appendix D: Known Issues and Resolutions

#### AWS Storage Gateway API Requirements
**Issue**: Parameter validation errors with Storage Gateway APIs
- **Root Cause**: The `describe_tapes` API requires `GatewayARN` parameters, but tape ARNs don't reliably contain gateway information
- **Solution Implemented**: 
  - Gateway discovery approach: List all gateways in the region
  - Try each gateway to find the requested tapes
  - Robust error handling for gateways that don't contain the tapes
  - Efficient tape discovery across multiple gateways

**Updated Approach**:
```python
# Instead of parsing tape ARNs (unreliable), discover gateways
gateways = storagegateway.list_gateways()
for gateway in gateways:
    try:
        # Try to get tape details from this gateway
        response = storagegateway.describe_tapes(
            GatewayARN=gateway['GatewayARN'], 
            TapeARNs=requested_tape_arns
        )
        # Process found tapes and remove from remaining list
    except Exception:
        # Gateway doesn't have these tapes, try next gateway
        continue
```

#### aws-azure-login Integration
**Issue**: Session management and authentication flow
- **Considerations**: 
  - Sessions typically expire after 1-12 hours
  - Re-authentication required for long-running operations
  - MFA prompts may interrupt automated processes

**Mitigation Strategies**:
```bash
# Session validation wrapper
validate_session() {
    aws sts get-caller-identity --profile ap-prod >/dev/null 2>&1 || {
        echo "Session expired, re-authenticating..."
        aws-azure-login --profile ap-prod
    }
}
```
- **Authentication Issues**: aws-azure-login troubleshooting
- **Permission Errors**: IAM policy verification
- **Network Issues**: Connectivity troubleshooting
- **Script Errors**: Common error messages and solutions

---

**Document Version**: 1.0  
**Last Updated**: January 22, 2026  
**Next Review**: February 22, 2026  
**Owner**: Infrastructure Team  
**Approvers**: [To be filled during approval process]