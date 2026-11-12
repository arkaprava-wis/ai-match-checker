from django.db import models
from django.core.validators import FileExtensionValidator
import json
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser

from core.models import User, State, District, Franchise



class Level(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class LevelStage(models.Model):
    name = models.CharField(max_length=100)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class TableImage(models.Model):
    image = models.ImageField(
        upload_to='table_images/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        help_text="Upload an image file (JPG, JPEG, PNG)"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(blank=True, null=True)
    total_sections = models.IntegerField(default=0)
    
    # Enhanced student and center information
    student_name = models.CharField(max_length=100, blank=True, null=True, help_text="Student name extracted from image")
    roll_number = models.CharField(max_length=50, blank=True, null=True, help_text="Roll number if present")
    center_name = models.CharField(max_length=150, blank=True, null=True, help_text="Education center/school name")
    
    # Image type detection with expanded options
    image_type = models.CharField(
        max_length=30,
        choices=[
            ('SECTION_TABLE', 'Section-based Table'),
            ('INDIVIDUAL_PROBLEMS', 'Individual Problems (P1-P20)'),
            ('NUMBERED_COLUMNS', 'Numbered Columns (1-50+)'),
            ('MIXED_OPERATIONS', 'Mixed Operations (Addition/Multiplication/Division)'),
            ('UNKNOWN', 'Unknown Format')
        ],
        default='UNKNOWN',
        help_text="Type of math worksheet detected"
    )
    
    def save(self, *args, **kwargs):
        if self.image:
            self.file_name = self.image.name
            self.file_size = self.image.size
        super().save(*args, **kwargs)
    
    def __str__(self):
        name_info = f" - {self.student_name}" if self.student_name else ""
        center_info = f" ({self.center_name})" if self.center_name else ""
        return f"Table Image {self.id}{name_info}{center_info} - {self.uploaded_at.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        ordering = ['-uploaded_at']


class TableSection(models.Model):
    """Model to represent different sections or groups in an image"""
    image = models.ForeignKey(TableImage, on_delete=models.CASCADE, related_name='sections')
    section_name = models.CharField(max_length=50)  # e.g., "Columns 1-10", "Section A"
    section_number = models.IntegerField()  # 1, 2, 3, etc.
    total_columns = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['image', 'section_number']
        ordering = ['section_number']
    
    def __str__(self):
        return f"{self.section_name} - {self.image.student_name or f'Image {self.image.id}'}"
    
    @property
    def accuracy(self):
        """Calculate accuracy based only on answered problems"""
        results = self.results.all()
        answered_results = results.exclude(given_answer__isnull=True)
        if not answered_results:
            return 0
        correct = answered_results.filter(is_correct=True).count()
        return round((correct / answered_results.count()) * 100, 1)
    
    @property
    def correct_answers(self):
        return self.results.filter(is_correct=True).count()
    
    @property
    def wrong_answers(self):
        return self.results.filter(is_correct=False, given_answer__isnull=False).count()
    
    @property 
    def unanswered_count(self):
        return self.results.filter(given_answer__isnull=True).count()


class TableResult(models.Model):
    PROBLEM_TYPE_CHOICES = [
        ('addition', 'Addition'),
        ('multiplication', 'Multiplication'),
        ('division', 'Division'),
        ('subtraction', 'Subtraction'),
    ]

    image = models.ForeignKey(TableImage, on_delete=models.CASCADE)
    section = models.ForeignKey(TableSection, on_delete=models.CASCADE,blank=True, null=True, related_name='results')
    column_number = models.IntegerField()
    problem_identifier = models.CharField(max_length=50, null=True, blank=True)
    extracted_numbers = models.JSONField(default=list)  # Store list of numbers
    calculated_sum = models.DecimalField(max_digits=15, decimal_places=3, null=True)  # Changed to DecimalField for precision
    given_answer = models.DecimalField(max_digits=15, decimal_places=3, null=True)  # Changed to DecimalField for precision
    is_correct = models.BooleanField(default=False)
    numbers_count = models.IntegerField(default=0)
    problem_type = models.CharField(max_length=20, choices=PROBLEM_TYPE_CHOICES, default='addition')  # NEW FIELD
    created_at = models.DateTimeField(auto_now_add=True)

    
    class Meta:
        unique_together = ['section', 'column_number']
        ordering = ['section__section_number', 'column_number']
    
    def save(self, *args, **kwargs):
        # Set is_correct based on comparison
        if self.given_answer is not None and self.calculated_sum is not None:
            self.is_correct = (self.calculated_sum == self.given_answer)
        else:
            self.is_correct = False
        super().save(*args, **kwargs)
    
    def __str__(self):
        student_info = f"{self.image.student_name} - " if self.image.student_name else ""
        status = "Right" if self.is_correct else "Wrong" if self.given_answer is not None else "Unanswered"
        return f"{student_info}Column {self.column_number}: {status}"
    
    @property
    def status(self):
        """Get the status as a string"""
        if self.given_answer is None:
            return "Unanswered"
        return "Right" if self.is_correct else "Wrong"
    
    @property
    def difference(self):
        """Calculate the difference between calculated sum and given answer"""
        if self.given_answer is not None and self.calculated_sum is not None:
            return self.calculated_sum - self.given_answer
        return None
    
    @property
    def display_expression(self):
        """Display the mathematical expression"""
        if not self.extracted_numbers:
            return "No numbers"
        numbers_str = " + ".join([str(num) if num >= 0 else f"({num})" for num in self.extracted_numbers])
        return f"{numbers_str} = {self.calculated_sum}"


class Student(models.Model):
    current_franchise = models.ForeignKey(Franchise, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, editable=False)
    student_code = models.CharField(max_length=25, null=True, blank=True, unique=True,editable=False)
    name = models.CharField(max_length=200,null=True, blank=True)
    phone = models.CharField(max_length=13,null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    source = models.CharField(max_length=200,null=True, blank=True, default='Franchise')
 
    parents_name = models.CharField(max_length=200,null=True, blank=True)
    alternative_phone = models.CharField(max_length=13,null=True, blank=True)
 
    dob = models.DateField(null=True,blank=True, verbose_name="Date of Birth")
    admission_date = models.DateField(null=True,blank=True)
 
    current_level = models.ForeignKey(Level,on_delete=models.SET_NULL, null=True,blank=True,related_name='student_level')
    current_stage = models.ForeignKey(LevelStage,on_delete=models.SET_NULL, null=True,blank=True,related_name='student_level_stage', editable=False)
 
    cleared_stage = models.ManyToManyField(LevelStage,blank=True, editable=False)
    
 
    is_active = models.BooleanField(default=False, verbose_name="Active student ?")
    is_approved = models.BooleanField(default=False, verbose_name="Approve student ?")
 
    approve_reason = models.CharField(max_length=500,null=True, blank=True,editable=False)
 
    is_subscribe = models.BooleanField(default=False, verbose_name="Subscribed ?")
    is_passout = models.BooleanField(default=False, verbose_name="Passout ?")
    is_dropout = models.BooleanField(default=False, verbose_name="Dropout ?")
    notes = models.CharField(null=True, blank=True, max_length=500, verbose_name="Reason of approval", help_text="Maximum 500 character can hold")
 
    created_at = models.DateTimeField(auto_now_add=True)
    points_gain = models.PositiveIntegerField(default=0,editable=False)
    image = models.ImageField(upload_to='profile_picture',null=True, blank=True)
    gender = models.CharField(max_length=200,null=True, blank=True)
 
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    address = models.CharField(max_length=200,null=True, blank=True, verbose_name="Student Address")
    request_id = models.CharField(max_length=200,null=True, blank=True)
    class StudentManager(models.Manager):
        def active_approved(self):
            """Get only active and approved students"""
            return self.filter(is_active=True, is_approved=True)
        
        def by_franchise(self, franchise_id):
            """Get students by franchise"""
            return self.filter(current_franchise_id=franchise_id)
    
    def get_full_info(self):
        """Get formatted student information"""
        info = {
            'name': self.name or 'N/A',
            'code': self.student_code or 'N/A',
            'level': self.current_level.name if self.current_level else 'N/A',
            'franchise': self.current_franchise.name if self.current_franchise else 'N/A',
            'location': self.current_franchise.location if self.current_franchise else 'N/A',
        }
        return info

    def is_assigned_to_exam(self, exam):
        """Check if student is assigned to specific exam"""
        return ExamStudent.objects.filter(exam=exam, student=self).exists()
# New models for Exam feature

class Exam(models.Model):
    LEVEL_CHOICES = [
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
    ]

    name = models.CharField(
        verbose_name="Exam Name",
        max_length=200
    )
    exam_date = models.DateField(
        verbose_name="Exam Date"
    )
    place = models.CharField(
        verbose_name="Exam Place",
        max_length=200
    )
    level = models.CharField(
        verbose_name="Exam Level",
        max_length=20,
        choices=LEVEL_CHOICES
    )
    number_of_questions = models.PositiveIntegerField(
        verbose_name="Number of Questions",
    )
    number_of_pages = models.PositiveIntegerField(
        verbose_name="Number of Pages",
    )
    remarks = models.TextField(
        verbose_name="Remarks",
        null=True, blank=True,
    )
    franchises = models.ManyToManyField(Franchise)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ExamAnswerKey(models.Model):
    """The correct multiple-choice answer for every question in an exam."""
    exam = models.OneToOneField(Exam, on_delete=models.CASCADE, related_name='answer_key')
    answers = models.JSONField(default=dict)
    points = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Answer key: {self.exam.name}"


class ExamStudent(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    student_exam_id = models.PositiveIntegerField(blank=True, null=True)
    score = models.FloatField(blank=True, null=True)
    manual_score = models.FloatField(blank=True, null=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('exam', 'student')
        ordering = ['student_exam_id']

    def __str__(self):
        return f"{self.student.name} - {self.exam.name}"


class AnswerSheetImage(models.Model):
    exam_student = models.ForeignKey(ExamStudent, related_name='answer_sheets', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='answer_sheets/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    table_image = models.OneToOneField(TableImage, on_delete=models.SET_NULL, null=True, blank=True)



# New Implementation with photo
class ExamPhoto(models.Model):
    student_code = models.CharField(max_length=100, db_index=True)
    image = models.ImageField(upload_to='student_photos/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_code} - Photo {self.pk}"



class EvaluationRun(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    student_code = models.CharField(
        max_length=100,
        db_index=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    error_message = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.student_code} - Evaluation {self.pk}"


class EvaluationPage(models.Model):

    evaluation_run = models.ForeignKey(
        EvaluationRun,
        on_delete=models.CASCADE,
        related_name='pages'
    )

    source_photo = models.ForeignKey(
        ExamPhoto,
        on_delete=models.CASCADE,
        related_name='evaluation_pages'
    )

    annotated_image = models.ImageField(
        upload_to='evaluation_results/%Y/%m/'
    )

    page_number = models.PositiveIntegerField(default=1)

    results = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['page_number']
        unique_together = ('evaluation_run', 'source_photo')

    def __str__(self):
        return (
            f"Evaluation {self.evaluation_run_id} "
            f"- Page {self.page_number}"
        )
