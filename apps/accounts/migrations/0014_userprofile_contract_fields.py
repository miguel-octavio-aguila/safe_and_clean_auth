from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_email_nullable'),
    ]

    operations = [
        # ── CustomUser: emergency contact fields ────────────────────────────
        migrations.AddField(
            model_name='customuser',
            name='emergency_contact_first_name',
            field=models.CharField(max_length=150, null=True, verbose_name='nombre del contacto de emergencia'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='emergency_contact_last_name',
            field=models.CharField(max_length=150, null=True, verbose_name='apellido del contacto de emergencia'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='emergency_contact_phone_number',
            field=models.CharField(max_length=15, null=True, verbose_name='teléfono del contacto de emergencia'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='emergency_contact_relation',
            field=models.CharField(blank=True, max_length=150, null=True, verbose_name='relación del contacto de emergencia'),
        ),
        # ── UserProfile: contract & personal data fields ────────────────────
        migrations.AddField(
            model_name='userprofile',
            name='contract_start',
            field=models.DateField(blank=True, null=True, verbose_name='inicio del contrato'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='contract_end',
            field=models.DateField(blank=True, null=True, verbose_name='fin del contrato'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='curp',
            field=models.CharField(blank=True, max_length=18, null=True, verbose_name='CURP'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='rfc',
            field=models.CharField(blank=True, max_length=13, null=True, verbose_name='RFC'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='nss',
            field=models.CharField(blank=True, max_length=15, null=True, verbose_name='Número de seguro social'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='date_of_birth',
            field=models.DateField(blank=True, null=True, verbose_name='fecha de nacimiento'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='age',
            field=models.IntegerField(blank=True, null=True, verbose_name='edad'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='gender',
            field=models.CharField(
                blank=True,
                choices=[('MALE', 'Hombre'), ('FEMALE', 'Mujer'), ('OTHER', 'Otro')],
                max_length=20,
                null=True,
                verbose_name='género',
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='place_of_birth',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='lugar de nacimiento'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='marital_status',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='estado civil'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='address',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='dirección'),
        ),
        # ── MessageType choices update on all three log models ──────────────
        migrations.AlterField(
            model_name='adminmessages',
            name='messageType',
            field=models.CharField(
                choices=[
                    ('ACTIVATION', 'Activación'),
                    ('CONFIRMATION', 'Confirmación'),
                    ('PASSWORD_CHANGE', 'Cambio de contraseña'),
                    ('PASSWORD_RESET', 'Restablecimiento de contraseña'),
                    ('PASSWORD_RESET_CONFIRM', 'Confirmación de restablecimiento de contraseña'),
                    ('CONTRACT_EXPIRING', 'Contrato próximo a expirar'),
                    ('CONTRACT_EXPIRED', 'Contrato expirado'),
                ],
                max_length=50,
                verbose_name='tipo de mensaje',
            ),
        ),
        migrations.AlterField(
            model_name='employeemessages',
            name='messageType',
            field=models.CharField(
                choices=[
                    ('ACTIVATION', 'Activación'),
                    ('CONFIRMATION', 'Confirmación'),
                    ('PASSWORD_CHANGE', 'Cambio de contraseña'),
                    ('PASSWORD_RESET', 'Restablecimiento de contraseña'),
                    ('PASSWORD_RESET_CONFIRM', 'Confirmación de restablecimiento de contraseña'),
                    ('CONTRACT_EXPIRING', 'Contrato próximo a expirar'),
                    ('CONTRACT_EXPIRED', 'Contrato expirado'),
                ],
                max_length=50,
                verbose_name='tipo de mensaje',
            ),
        ),
        migrations.AlterField(
            model_name='clientmessages',
            name='messageType',
            field=models.CharField(
                choices=[
                    ('ACTIVATION', 'Activación'),
                    ('CONFIRMATION', 'Confirmación'),
                    ('PASSWORD_CHANGE', 'Cambio de contraseña'),
                    ('PASSWORD_RESET', 'Restablecimiento de contraseña'),
                    ('PASSWORD_RESET_CONFIRM', 'Confirmación de restablecimiento de contraseña'),
                    ('CONTRACT_EXPIRING', 'Contrato próximo a expirar'),
                    ('CONTRACT_EXPIRED', 'Contrato expirado'),
                ],
                max_length=50,
                verbose_name='tipo de mensaje',
            ),
        ),
    ]
