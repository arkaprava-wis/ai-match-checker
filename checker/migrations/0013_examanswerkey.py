from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0012_alter_exam_level'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExamAnswerKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answers', models.JSONField(default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('exam', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='answer_key', to='checker.exam')),
            ],
        ),
    ]
