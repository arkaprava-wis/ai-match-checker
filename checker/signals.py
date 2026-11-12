from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Exam, ExamStudent

@receiver(post_save, sender=Exam)
def generate_exam_code(sender, instance, created, **kwargs):
    if created:
        instance.exam_code = f'CWE-{instance.id}'
        instance.save()

@receiver(post_save, sender=ExamStudent)
def generate_student_exam_id(sender, instance, created, **kwargs):
    if created:
        last_student = ExamStudent.objects.filter(exam=instance.exam).order_by('-student_exam_id').first()
        if last_student and last_student.student_exam_id:
            instance.student_exam_id = last_student.student_exam_id + 1
        else:
            instance.student_exam_id = 1
        instance.save()
