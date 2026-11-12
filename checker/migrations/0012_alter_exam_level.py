# Generated manually to support the expanded hard-coded level choices.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0011_exam_number_of_pages'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exam',
            name='level',
            field=models.CharField(
                choices=[
                    ('1', 'LEVEL 1'),
                    ('12', 'LEVEL 2 (Part-I)'),
                    ('13', 'LEVEL 2 (Part-II)'),
                    ('2', 'LEVEL 3'),
                    ('3', 'LEVEL 4'),
                    ('4', 'LEVEL 5'),
                    ('5', 'LEVEL 6'),
                    ('6', 'LEVEL 7'),
                    ('7', 'LEVEL 8'),
                    ('8', 'LEVEL 9'),
                ],
                max_length=20,
            ),
        ),
    ]
