from django import forms
from .models import Exam, ExamAnswerKey, TableImage
from core.models import Franchise


class ImageUploadForm(forms.ModelForm):
    student_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Student Name (optional - auto-detected)',
            'id': 'studentName'
        }),
        help_text="Leave blank for auto-detection from image"
    )
    
    roll_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Roll Number (optional - auto-detected)',
            'id': 'rollNumber'
        }),
        help_text="Leave blank for auto-detection from image"
    )

    class Meta:
        model = TableImage
        fields = ['image', 'student_name', 'roll_number']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'id': 'fileInput',
                'style': 'display: none;'
            })
        }
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Check file size (15MB limit for detailed worksheets)
            if image.size > 15 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 15MB.")
            
            # Check file type
            if not image.content_type.startswith('image/'):
                raise forms.ValidationError("File must be an image.")
            
            # Check file extension
            allowed_extensions = ['jpg', 'jpeg', 'png']
            file_extension = image.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                raise forms.ValidationError(
                    f"File extension '{file_extension}' not allowed. "
                    f"Allowed extensions: {', '.join(allowed_extensions)}"
                )
        
        return image
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set manual student info if provided
        if self.cleaned_data.get('student_name'):
            instance.student_name = self.cleaned_data['student_name']
        if self.cleaned_data.get('roll_number'):
            instance.roll_number = self.cleaned_data['roll_number']
        
        if commit:
            instance.save()
        return instance


class ExamForm(forms.ModelForm):
    number_of_questions = forms.IntegerField(
        required=True,
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
    )
    number_of_pages = forms.IntegerField(
        required=True,
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
    )

    class Meta:
        model = Exam
        fields = ['name', 'exam_date', 'place', 'level', 'number_of_questions', 'number_of_pages', 'remarks']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'exam_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': __import__('datetime').date.today().isoformat()
            }),
            'place': forms.TextInput(attrs={'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_exam_date(self):
        exam_date = self.cleaned_data.get('exam_date')
        from datetime import date
        if self.instance.pk and exam_date == self.instance.exam_date:
            return exam_date
        if exam_date and exam_date < date.today():
            raise forms.ValidationError("Exam date cannot be in the past.")
        return exam_date


class ExamAnswerKeyForm(forms.Form):
    ANSWER_CHOICES = [
        ('', 'Select an answer'),
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    ]

    def __init__(self, *args, exam, answer_key=None, **kwargs):
        super().__init__(*args, **kwargs)
        saved_answers = answer_key.answers if answer_key else {}
        saved_points = answer_key.points if answer_key else {}

        for question_number in range(1, exam.number_of_questions + 1):
            self.fields[f'question_{question_number}'] = forms.ChoiceField(
                label=f'Question {question_number}',
                choices=self.ANSWER_CHOICES,
                initial=saved_answers.get(str(question_number)),
                widget=forms.Select(attrs={'class': 'form-select'}),
            )
            self.fields[f'points_{question_number}'] = forms.IntegerField(
                label='Points',
                min_value=0,
                initial=saved_points.get(str(question_number), 1),
                widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            )

    def get_answers(self):
        return {
            field_name.removeprefix('question_'): answer
            for field_name, answer in self.cleaned_data.items()
            if field_name.startswith('question_')
        }

    def get_points(self):
        return {
            field_name.removeprefix('points_'): points
            for field_name, points in self.cleaned_data.items()
            if field_name.startswith('points_')
        }
