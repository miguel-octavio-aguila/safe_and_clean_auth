from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_userprofile_contract_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='shirt_size',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='talla de camisa'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='pants_size',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='talla de pantalón'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='shoe_size',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='talla de zapatos'),
        ),
    ]
