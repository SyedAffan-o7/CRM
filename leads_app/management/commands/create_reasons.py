from django.core.management.base import BaseCommand
from leads_app.models import Reason


class Command(BaseCommand):
    help = 'Create sample reasons for Not Fulfilled enquiries'

    def handle(self, *args, **options):
        reasons_data = [
            {
                'name': 'Price too high',
                'description': 'Customer found our pricing too expensive compared to competitors'
            },
            {
                'name': 'Not interested in product',
                'description': 'Customer decided they do not need this product/service'
            },
            {
                'name': 'Budget constraints',
                'description': 'Customer does not have sufficient budget at this time'
            },
            {
                'name': 'Timing not right',
                'description': 'Customer wants to purchase later, not now'
            },
            {
                'name': 'Went with competitor',
                'description': 'Customer chose a competitor\'s product/service'
            },
            {
                'name': 'Technical requirements not met',
                'description': 'Our product does not meet customer\'s technical specifications'
            },
            {
                'name': 'No decision maker contact',
                'description': 'Unable to reach the person who makes purchasing decisions'
            },
            {
                'name': 'Company policy restrictions',
                'description': 'Customer\'s company policy prevents them from purchasing'
            },
            {
                'name': 'Already have similar solution',
                'description': 'Customer already has a similar product/service in place'
            },
            {
                'name': 'Lost contact',
                'description': 'Customer stopped responding to our communications'
            },
            {
                'name': 'Product not available',
                'description': 'Requested product is out of stock or discontinued'
            },
            {
                'name': 'Delivery timeline too long',
                'description': 'Customer needs faster delivery than we can provide'
            }
        ]
        
        created_count = 0
        
        for reason_data in reasons_data:
            reason, created = Reason.objects.get_or_create(
                name=reason_data['name'],
                defaults={
                    'description': reason_data['description'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created reason: {reason.name}')
                )
            else:
                self.stdout.write(f'- Reason already exists: {reason.name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Sample reasons setup complete!')
        )
        self.stdout.write(f'📊 Created {created_count} new reasons')
        self.stdout.write(f'📋 Total active reasons: {Reason.objects.filter(is_active=True).count()}')
