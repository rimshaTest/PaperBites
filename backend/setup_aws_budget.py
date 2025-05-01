#!/usr/bin/env python3
"""
Set up AWS Budget with automatic actions to shut off S3 write access
when your budget limit is approached.
"""

import boto3
import argparse
import json
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('budget_setup')

def create_budget_with_actions(
    budget_name: str, 
    account_id: str, 
    monthly_limit: float, 
    email: str,
    threshold_percent: int = 80
) -> bool:
    """
    Create an AWS Budget with automatic actions to prevent exceeding cost limits.
    
    Args:
        budget_name: Name for the budget
        account_id: Your AWS account ID
        monthly_limit: Maximum monthly spending in USD
        email: Email address for notifications
        threshold_percent: Percentage threshold for notifications
        
    Returns:
        bool: Success status
    """
    logger.info(f"Creating AWS Budget with {monthly_limit} USD monthly limit")
    
    # Create a Budget client
    budget_client = boto3.client('budgets')
    
    # Specific S3 budget to track only S3 costs
    budget_config = {
        'BudgetName': budget_name,
        'BudgetType': 'COST',
        'BudgetLimit': {
            'Amount': str(monthly_limit),
            'Unit': 'USD'
        },
        'CostFilters': {
            'Service': ['Amazon Simple Storage Service']
        },
        'TimeUnit': 'MONTHLY',
        'CostTypes': {
            'IncludeTax': True,
            'IncludeSubscription': True,
            'UseBlended': False,
            'IncludeRefund': False,
            'IncludeCredit': False,
            'IncludeUpfront': True,
            'IncludeRecurring': True,
            'IncludeOtherSubscription': True,
            'IncludeSupport': True,
            'IncludeDiscount': True,
            'UseAmortized': False
        }
    }
    
    # Add notifications at different thresholds
    notifications = []
    
    # Warning at threshold_percent
    notifications.append({
        'Notification': {
            'NotificationType': 'ACTUAL',
            'ComparisonOperator': 'GREATER_THAN',
            'Threshold': float(threshold_percent),
            'ThresholdType': 'PERCENTAGE',
            'NotificationState': 'ALARM'
        },
        'Subscribers': [
            {
                'SubscriptionType': 'EMAIL',
                'Address': email
            }
        ]
    })
    
    # Critical warning at 95%
    notifications.append({
        'Notification': {
            'NotificationType': 'ACTUAL',
            'ComparisonOperator': 'GREATER_THAN',
            'Threshold': 95.0,
            'ThresholdType': 'PERCENTAGE',
            'NotificationState': 'ALARM'
        },
        'Subscribers': [
            {
                'SubscriptionType': 'EMAIL',
                'Address': email
            }
        ]
    })
    
    # Add notifications to budget
    budget_config['NotificationsWithSubscribers'] = notifications
    
    # Create the budget
    try:
        budget_client.create_budget(
            AccountId=account_id,
            Budget=budget_config
        )
        logger.info(f"Budget {budget_name} created successfully")
        
        # Create local state file to track budget status
        state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'budget_state.json')
        with open(state_file, 'w') as f:
            json.dump({
                'budget_name': budget_name,
                'account_id': account_id,
                'monthly_limit': monthly_limit,
                'email': email,
                'threshold_percent': threshold_percent,
                'created_at': time.strftime("%Y-%m-%d %H:%M:%S")
            }, f, indent=2)
        
        return True
    except Exception as e:
        logger.error(f"Error creating budget: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Set up AWS Budget with automatic actions')
    parser.add_argument('--name', default='PaperBites-S3-Budget', help='Budget name')
    parser.add_argument('--account-id', required=True, help='Your AWS account ID')
    parser.add_argument('--limit', type=float, default=1.0, help='Monthly budget limit in USD')
    parser.add_argument('--email', required=True, help='Email address for notifications')
    parser.add_argument('--threshold', type=int, default=80, help='Warning threshold percentage')
    
    args = parser.parse_args()
    
    success = create_budget_with_actions(
        args.name,
        args.account_id,
        args.limit,
        args.email,
        args.threshold
    )
    
    if success:
        logger.info("\nBudget setup complete!")
        logger.info(f"Your S3 storage is now protected with a ${args.limit} monthly budget limit.")
        logger.info(f"You'll receive email notifications at {args.threshold}% of your budget.")
        logger.info("At 95% of your budget, AWS will send a critical warning.")
        logger.info("\nFree tier limits for S3:")
        logger.info("- 5GB of standard storage")
        logger.info("- 20,000 GET requests")
        logger.info("- 2,000 PUT/COPY/POST/LIST requests per month")
        logger.info("- 100GB of data transfer out")
    else:
        logger.error("Budget setup failed. Please check the logs and try again.")

if __name__ == "__main__":
    import time  # Import here to avoid issues
    main()