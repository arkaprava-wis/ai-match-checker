# Generated manually for the Exam creation fields.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0009_evaluationrun_evaluationpage'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='level',
            field=models.CharField(
                choices=[(f'LEVEL {number}', f'LEVEL {number}') for number in range(1, 11)],
                default='LEVEL 1',
                max_length=10,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='exam',
            name='part',
            field=models.CharField(
                blank=True,
                choices=[('I', 'I'), ('II', 'II'), ('III', 'III'), ('IV', 'IV')],
                max_length=3,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='exam',
            name='number_of_questions',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
