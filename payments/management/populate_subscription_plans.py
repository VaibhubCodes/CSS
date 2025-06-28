from django.core.management.base import BaseCommand
from payments.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Populate default subscription plans'

    def handle(self, *args, **options):
        # Delete existing plans if needed
        if self.confirm_action("Delete existing plans?"):
            SubscriptionPlan.objects.all().delete()
            self.stdout.write("Deleted existing plans")

        # Create default plans
        default_plans = [
            {
                'name': 'Basic Plan',
                'plan_code': 'basic',
                'description': 'Perfect for individuals getting started with basic file management needs',
                'price': 499,
                'storage_gb': 5,
                'is_sparkle': False,
                'features': [
                    '5GB Cloud Storage',
                    'Basic File Management',
                    'Email Support',
                    'Standard Processing Speed',
                    'Basic Security Features'
                ],
                'sort_order': 1,
                'duration_days': 30,
            },
            {
                'name': 'Premium Plan',
                'plan_code': 'premium',
                'description': 'Great for professionals and small teams who need enhanced features',
                'price': 999,
                'storage_gb': 20,
                'is_sparkle': True,
                'features': [
                    '20GB Cloud Storage',
                    'Advanced File Management',
                    'Priority Support',
                    'Fast Processing Speed',
                    'Enhanced Security',
                    'File Versioning',
                    'Advanced Analytics',
                    'Team Collaboration Tools'
                ],
                'sort_order': 2,
                'duration_days': 30,
            },
            {
                'name': 'Enterprise Plan',
                'plan_code': 'enterprise',
                'description': 'Ideal for large teams and organizations requiring premium features',
                'price': 1999,
                'storage_gb': 50,
                'is_sparkle': True,
                'features': [
                    '50GB Cloud Storage',
                    'Enterprise File Management',
                    '24/7 Priority Support',
                    'Lightning Fast Processing',
                    'Enterprise Security',
                    'Advanced File Versioning',
                    'Comprehensive Analytics',
                    'Advanced Team Collaboration',
                    'API Access',
                    'Custom Integrations',
                    'Admin Controls',
                    'Audit Logs'
                ],
                'sort_order': 3,
                'duration_days': 30,
            }
        ]

        created_count = 0
        for plan_data in default_plans:
            plan, created = SubscriptionPlan.objects.get_or_create(
                plan_code=plan_data['plan_code'],
                defaults=plan_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created plan: {plan.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Plan already exists: {plan.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} subscription plans')
        )

    def confirm_action(self, message):
        response = input(f"{message} (y/N): ")
        return response.lower() in ['y', 'yes']
