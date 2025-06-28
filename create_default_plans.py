from django.conf import settings
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')
django.setup()

from payments.models import SubscriptionPlan

def create_default_plans():
    """Create default subscription plans"""
    plans_data = [
        {
            'name': 'Basic Plan',
            'plan_code': 'basic',
            'description': 'Perfect for individuals getting started',
            'price': 499,
            'storage_gb': 5,
            'is_sparkle': False,
            'features': ['5GB Storage', 'Basic Support', 'Standard Processing'],
            'sort_order': 1,
        },
        {
            'name': 'Premium Plan',
            'plan_code': 'premium',
            'description': 'Great for professionals and small teams',
            'price': 999,
            'storage_gb': 20,
            'is_sparkle': True,
            'features': ['20GB Storage', 'Priority Support', 'Fast Processing', 'Advanced Features'],
            'sort_order': 2,
        },
        {
            'name': 'Enterprise Plan',
            'plan_code': 'enterprise',
            'description': 'Ideal for large teams and organizations',
            'price': 1999,
            'storage_gb': 50,
            'is_sparkle': True,
            'features': ['50GB Storage', '24/7 Support', 'Fastest Processing', 'All Premium Features'],
            'sort_order': 3,
        }
    ]
    
    for plan_data in plans_data:
        plan, created = SubscriptionPlan.objects.update_or_create(
            plan_code=plan_data['plan_code'],
            defaults=plan_data
        )
        print(f"{'Created' if created else 'Updated'} plan: {plan.name}")

if __name__ == '__main__':
    create_default_plans()
    print("Default plans setup complete!")