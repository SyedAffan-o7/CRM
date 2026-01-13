from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads_app', '0018_lead_image_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='assignment_status',
            field=models.CharField(
                max_length=20,
                choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')],
                null=True,
                blank=True,
                default=None,
            ),
        ),
    ]
