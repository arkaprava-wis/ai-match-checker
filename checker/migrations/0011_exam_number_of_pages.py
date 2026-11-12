# Generated manually for the optional Exam page count.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0010_exam_level_part_number_of_questions'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='number_of_pages',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
