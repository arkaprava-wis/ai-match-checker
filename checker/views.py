import requests
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .forms import ExamForm
from .models import Exam
import google.generativeai as genai
import csv
import io
import time
import json
import os
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import default_storage
from .models import AnswerSheetImage, Exam, ExamAnswerKey, ExamStudent, Student, TableImage, TableResult, TableSection
from .forms import ExamAnswerKeyForm, ExamForm, ImageUploadForm
from core.views import BaseCreateView, BaseListView, BaseUpdateView
from django.urls import reverse_lazy
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from .serializers import FranchiseSerializer, StudentSerializer
from core.models import Franchise

from django.db.models import Q, Window, F, Case, When, Value
from datetime import date
from django.db.models.functions import Rank
from .models import Exam, Student, ExamStudent, Level
from decimal import Decimal, ROUND_HALF_UP
import decimal


# AJAX: Delete student answer sheet
@csrf_exempt
@require_POST
def ajax_delete_student_sheet(request, sheet_id):
    from .models import AnswerSheetImage
    try:
        sheet = AnswerSheetImage.objects.get(id=sheet_id)
        sheet.delete()
        return JsonResponse({'success': True})
    except AnswerSheetImage.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Sheet not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

# AJAX: Change student answer sheet image
@csrf_exempt
@require_POST
def ajax_change_student_sheet(request, sheet_id):
    from .models import AnswerSheetImage
    try:
        sheet = AnswerSheetImage.objects.get(id=sheet_id)
        image = request.FILES.get('image')
        if not image:
            return JsonResponse({'success': False, 'message': 'No image uploaded.'})
        sheet.image = image
        sheet.save()
        return JsonResponse({'success': True})
    except AnswerSheetImage.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Sheet not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .forms import ExamForm
from .models import Exam
import google.generativeai as genai
import csv
import io
import time
import json
import os
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import default_storage
from .models import AnswerSheetImage, Exam, ExamStudent, Student, TableImage, TableResult, TableSection
from .forms import ExamForm, ImageUploadForm
from core.views import BaseCreateView, BaseListView, BaseUpdateView
from django.urls import reverse_lazy
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from .serializers import FranchiseSerializer, StudentSerializer
from core.models import Franchise

from django.db.models import Q, Window, F, Case, When, Value
from datetime import date
from django.db.models.functions import Rank
from .models import Exam, Student, ExamStudent, Level
from decimal import Decimal, ROUND_HALF_UP
import decimal

from django.db import transaction
from .models import ExamPhoto, EvaluationRun

# New Implementation  (Photo Uploading)
def new_upload_page(request, student_code):
    student_name = request.GET.get('name', '').strip()

    # Look up the student and their exam so the page can show
    # an information card (exam name, date and level) with the upload form.
    student = Student.objects.filter(
        student_code=student_code
    ).select_related('current_franchise', 'current_level').first()

    # Prefer the exam the user came from (?exam=<id>, linked from the exam
    # detail page); otherwise fall back to the student's most recent exam so
    # the back button still returns to the exam's Assign Students page.
    exam_students = ExamStudent.objects.filter(
        student__student_code=student_code
    ).select_related('exam')

    exam_student = None
    exam_id = request.GET.get('exam')
    if exam_id and str(exam_id).isdigit():
        exam_student = exam_students.filter(exam_id=exam_id).first()

    if not exam_student:
        exam_student = exam_students.order_by('-exam__exam_date', '-id').first()

    exam = exam_student.exam if exam_student else None

    # Fall back to the stored name when the query-string name is missing.
    if not student_name and student and student.name:
        student_name = student.name

    if exam:
        back_url = reverse('exam_detail', args=[exam.id])
        back_label = 'Back to Exam'
    else:
        back_url = reverse('student_list')
        back_label = 'Back to Students'

    return render(
        request,
        'checker/new_upload_page.html',
        {
            'student_code': student_code,
            'student_name': student_name,
            'student': student,
            'exam': exam,
            'back_url': back_url,
            'back_label': back_label,
        }
    )

@require_POST
def save_student_photos(request, student_code):
    uploaded_files = request.FILES.getlist('photos')

    if not uploaded_files:
        return JsonResponse({
            'success': False,
            'message': 'Please capture at least one photo.'
        }, status=400)

    if len(uploaded_files) > 20:
        return JsonResponse({
            'success': False,
            'message': 'You can upload a maximum of 20 photos at once.'
        }, status=400)

    allowed_types = {'image/jpeg', 'image/png', 'image/webp'}
    max_file_size = 10 * 1024 * 1024  # 10 MB

    for uploaded_file in uploaded_files:
        if uploaded_file.content_type not in allowed_types:
            return JsonResponse({
                'success': False,
                'message': 'Only JPEG, PNG and WebP images are allowed.'
            }, status=400)

        if uploaded_file.size > max_file_size:
            return JsonResponse({
                'success': False,
                'message': 'Each photo must be 10 MB or smaller.'
            }, status=400)

    try:
        with transaction.atomic():
            saved_photos = []

            for uploaded_file in uploaded_files:
                photo = ExamPhoto.objects.create(
                    student_code=student_code,
                    image=uploaded_file
                )
                saved_photos.append(photo)

        return JsonResponse({
            'success': True,
            'message': f'{len(saved_photos)} photo(s) saved successfully.',
            'saved_count': len(saved_photos),
            'photos': [
                {
                    'id': photo.id,
                    'image_url': photo.image.url
                }
                for photo in saved_photos
            ]
        })

    except Exception:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while saving photos.'
        }, status=500)


# New Implementation: Student Evaluation Dashboard Page

# Every uploaded paper carries this many questions; question numbers
# continue across papers (paper 2 starts at 31, paper 3 at 61, ...).
QUESTIONS_PER_PAPER = 30


def _uploaded_paper_name(image_field):
    """The uploaded photo's file name, without its folder or extension.

    Used as the paper's display name on the evaluate page - falls back to
    an empty string when the photo has no stored image.
    """
    stored_name = getattr(image_field, 'name', '') or ''
    base_name = os.path.basename(stored_name)

    if not base_name:
        return ''

    return os.path.splitext(base_name)[0]


def _natural_name_key(name):
    """Sort key that orders names with numbers naturally (test2 < test10)."""
    parts = re.split(r'(\d+)', name.lower())

    # re.split alternates non-digit / digit parts, so even indexes are
    # always strings and odd indexes are always digit runs - turning the
    # digit runs into ints keeps every comparison well typed.
    return tuple(
        int(part) if index % 2 else part
        for index, part in enumerate(parts)
    )


def _paper_display_order(photos):
    """Sort papers by their uploaded file names in natural order.

    A paper named test1 comes before test2, which comes before test10 -
    regardless of the order the papers were uploaded in. Photos without
    a usable file name sort last, keeping their upload order (the sort
    is stable over the upload order, which also breaks name ties).
    """
    def sort_key(photo):
        name = _uploaded_paper_name(getattr(photo, 'image', None))

        if not name:
            return (1, ())

        return (0, _natural_name_key(name))

    return sorted(photos, key=sort_key)


def _result_question_numbers(photo_results):
    """The integer question numbers stored in a paper's results."""
    if not isinstance(photo_results, list):
        return []

    numbers = []

    for result in photo_results:
        if not isinstance(result, dict):
            continue

        number = result.get('question_number')

        if (
            isinstance(number, int)
            and not isinstance(number, bool)
        ):
            numbers.append(number)

    return numbers


def _renumber_results(photo_results, display_start):
    """Shift a paper's stored question numbers to its display position.

    Question numbers are stored following the order the papers were
    evaluated in (upload order). The evaluate page shows papers in
    file-name order instead, so the numbers are re-numbered in memory to
    follow that display order - the paper shown first displays questions
    starting at display_start. Nothing is saved; the save endpoint maps
    the submitted numbers back to the stored numbering.
    """
    stored_numbers = _result_question_numbers(photo_results)

    if not stored_numbers:
        return

    shift = display_start - min(stored_numbers)

    if not shift:
        return

    for result in photo_results:
        if not isinstance(result, dict):
            continue

        number = result.get('question_number')

        if (
            isinstance(number, int)
            and not isinstance(number, bool)
        ):
            result['question_number'] = number + shift


def _renumber_submitted_results(student_code, evaluation_page, submitted_results):
    """Map submitted question numbers back to the stored numbering.

    The evaluate page re-numbers questions to the file-name display order
    (see _renumber_results); the manual save endpoint receives those
    displayed numbers. This rebuilds the same display order and shifts
    the submitted numbers back so they match the numbers stored on the
    evaluation page.
    """
    if not isinstance(submitted_results, list):
        return

    from .models import ExamPhoto

    photos = list(
        ExamPhoto.objects.filter(
            student_code=student_code
        ).order_by('uploaded_at', 'id')
    )

    display_positions = {
        photo.id: position
        for position, photo in enumerate(
            _paper_display_order(photos), start=1
        )
    }

    position = display_positions.get(evaluation_page.source_photo_id)

    if not position:
        return

    display_start = (position - 1) * QUESTIONS_PER_PAPER + 1

    stored_numbers = _result_question_numbers(evaluation_page.results)

    if not stored_numbers:
        return

    shift = min(stored_numbers) - display_start

    if not shift:
        return

    for item in submitted_results:
        if not isinstance(item, dict):
            continue

        number = item.get('question_number')

        if (
            isinstance(number, int)
            and not isinstance(number, bool)
        ):
            item['question_number'] = number + shift


def _apply_answer_key(photo_results, answer_key_answers, answer_key_points):
    """Pre-fill each question result with the exam's answer key.

    Adds display fields to every result dict (in memory only - nothing is
    saved): the correct option for the question number (shown as a badge)
    and the score as a toggle between 0 and the question's points. The
    toggle starts on when the detected tick matches the correct option;
    manually saved values always win.

    Each question uses only its own key entry: question 31 uses the key's
    question 31 (set on the exam's answer key page), never question 1's -
    questions the key does not define show a blank badge and no score.
    """
    if not isinstance(photo_results, list):
        return

    for result in photo_results:
        if not isinstance(result, dict):
            continue

        # Answer keys are stored as JSON, so their keys are strings.
        question_key = str(result.get('question_number', ''))
        key_option = answer_key_answers.get(question_key) or None

        correct_option = result.get('correct_option') or key_option
        ticked_option = result.get('ticked_option') or ''

        result['answer_key_option'] = key_option
        result['display_correct'] = correct_option or None

        # Points awarded when the score toggle is on: the answer key's
        # points, unless a manually saved positive score wins.
        manual_score = result.get('score')
        key_points = answer_key_points.get(question_key)

        if manual_score is not None and manual_score > 0:
            award_points = manual_score
        else:
            award_points = key_points

        # The toggle's starting state: a manually saved score decides;
        # otherwise it is on when the detected tick matches the correct
        # option.
        if manual_score is None:
            awarded = bool(ticked_option and ticked_option == correct_option)
        else:
            awarded = manual_score > 0

        result['award_points'] = award_points
        result['has_award_points'] = award_points is not None
        result['score_awarded'] = awarded and award_points is not None


# Student Evaluation Dashboard
def evaluate_student_page(request, student_code):

    from .models import ExamPhoto, EvaluationRun

    # Fetch all uploaded photos for this student.
    photos = list(
        ExamPhoto.objects.filter(
            student_code=student_code
        ).order_by('uploaded_at', 'id')
    )

    # Show the papers in the order of their uploaded file names (test1,
    # test2, ... test10) instead of the order they were uploaded in.
    photos = _paper_display_order(photos)

    # Fetch the latest evaluation run.
    latest_evaluation = EvaluationRun.objects.filter(
        student_code=student_code
    ).order_by('-created_at').first()

    # Fetch all evaluation pages from the latest run.
    evaluation_pages = (
        list(
            latest_evaluation.pages.select_related(
                'source_photo'
            ).order_by('page_number')
        )
        if latest_evaluation
        else []
    )

    # Map evaluation pages to their original uploaded photos.
    evaluation_page_map = {
        page.source_photo_id: page
        for page in evaluation_pages
    }

    # Overall statistics across all evaluated papers.
    all_results = []

    if latest_evaluation and latest_evaluation.status == 'COMPLETED':

        for evaluation_page in evaluation_pages:

            all_results.extend(evaluation_page.results)

    total_questions = len(all_results)

    ok_count = sum(
        1 for result in all_results
        if result.get('status') == 'OK'
    )

    review_count = sum(
        1 for result in all_results
        if result.get('status') != 'OK'
    )

    # Resolve the student's exam (same logic as the upload page) so the
    # exam's answer key can pre-fill the correct option and the score of
    # every question.
    exam_students = ExamStudent.objects.filter(
        student__student_code=student_code
    ).select_related('exam')

    exam_id = request.GET.get('exam')
    exam_student = None
    if exam_id and str(exam_id).isdigit():
        exam_student = exam_students.filter(exam_id=exam_id).first()

    if not exam_student:
        exam_student = exam_students.order_by(
            '-exam__exam_date', '-id'
        ).first()

    answer_key = (
        getattr(exam_student.exam, 'answer_key', None)
        if exam_student
        else None
    )
    answer_key_answers = answer_key.answers if answer_key else {}
    answer_key_points = answer_key.points if answer_key else {}

    exam = exam_student.exam if exam_student else None

    # Fall back to the stored student name so the summary does not show
    # "Unknown" when the link did not carry a name.
    student_name = request.GET.get('name', '').strip()
    if not student_name:
        student = Student.objects.filter(
            student_code=student_code
        ).only('name').first()
        student_name = (student.name if student else '') or ''

    # All uploaded papers are shown at once - no pagination. Attach the
    # evaluation data of each paper to its photo so the template can loop
    # over the papers directly.
    questions_per_paper = QUESTIONS_PER_PAPER

    for index, photo in enumerate(photos, start=1):
        photo.paper_number = index
        photo.paper_name = _uploaded_paper_name(photo.image)
        photo.question_start = (index - 1) * questions_per_paper + 1
        photo.question_end = photo.question_start + questions_per_paper - 1
        photo.evaluation_page = evaluation_page_map.get(photo.id)
        photo.results = photo.evaluation_page.results if photo.evaluation_page else []

        # Question numbers are stored following the evaluation (upload)
        # order; re-number them in memory to the file-name display order
        # so the questions match the displayed paper sequence.
        _renumber_results(photo.results, photo.question_start)

        # Pre-fill each question with the answer key's correct option and,
        # when the detected tick matches it, the key's score.
        _apply_answer_key(
            photo.results, answer_key_answers, answer_key_points
        )

    # Total score for the summary card: every question's current score -
    # a manually saved score wins; otherwise the answer key's points when
    # the detected tick matches the correct option.
    total_score = 0
    for photo in photos:
        if not isinstance(photo.results, list):
            continue
        for result in photo.results:
            if (
                isinstance(result, dict)
                and result.get('score_awarded')
            ):
                total_score += result.get('award_points') or 0

    context = {
        'student_code': student_code,
        'student_name': student_name,

        'exam': exam,

        'photos': photos,
        'latest_evaluation': latest_evaluation,

        'evaluation_pages': evaluation_pages,

        'total_questions': total_questions,
        'ok_count': ok_count,
        'review_count': review_count,
        'total_score': total_score,
    }

    return render(
        request,
        'checker/evaluate_student.html',
        context
    )



@require_POST
def save_manual_question_results(request, student_code):
    from django.db import transaction
    from .models import EvaluationRun, EvaluationPage

    try:
        payload = json.loads(request.body)

        page_id = payload.get('page_id')
        submitted_results = payload.get('results')

        if not page_id or not isinstance(submitted_results, list):
            return JsonResponse({
                'success': False,
                'message': 'Invalid request data.'
            }, status=400)

        # Get the latest evaluation for this student.
        latest_evaluation = EvaluationRun.objects.filter(
            student_code=student_code
        ).order_by('-created_at').first()

        if not latest_evaluation:
            return JsonResponse({
                'success': False,
                'message': 'No evaluation found for this student.'
            }, status=404)

        # Only allow saving to a page in the latest evaluation.
        evaluation_page = EvaluationPage.objects.filter(
            id=page_id,
            evaluation_run=latest_evaluation
        ).first()

        if not evaluation_page:
            return JsonResponse({
                'success': False,
                'message': 'Evaluation page not found.'
            }, status=404)

        # The evaluate page displays papers in file-name order and
        # re-numbers their questions accordingly; map the submitted
        # numbers back to the stored numbering before saving.
        _renumber_submitted_results(
            student_code, evaluation_page, submitted_results
        )

        stored_results = evaluation_page.results

        if not isinstance(stored_results, list):
            return JsonResponse({
                'success': False,
                'message': 'Invalid stored evaluation results.'
            }, status=400)

        # Build a lookup using question numbers.
        result_map = {
            str(result.get('question_number')): result
            for result in stored_results
            if isinstance(result, dict)
        }

        submitted_questions = set()

        with transaction.atomic():

            for item in submitted_results:

                if not isinstance(item, dict):
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid question data.'
                    }, status=400)

                question_number = str(item.get('question_number', ''))

                if (
                    not question_number
                    or question_number not in result_map
                    or question_number in submitted_questions
                ):
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid or duplicate question number.'
                    }, status=400)

                submitted_questions.add(question_number)

                # Validate the correct option (the answer key allows A-D).
                correct_option = item.get('correct_option')

                if correct_option in (None, ''):
                    correct_option = None
                elif isinstance(correct_option, str):
                    correct_option = correct_option.strip().upper()

                    if correct_option not in ('A', 'B', 'C', 'D'):
                        return JsonResponse({
                            'success': False,
                            'message': (
                                f'Invalid correct option for question '
                                f'{question_number}.'
                            )
                        }, status=400)
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'Correct option must be A, B, C, D or blank.'
                    }, status=400)

                # Validate manually entered score.
                score = item.get('score')

                if score in (None, ''):
                    score = None
                elif (
                    isinstance(score, bool)
                    or not isinstance(score, int)
                    or score < 0
                ):
                    return JsonResponse({
                        'success': False,
                        'message': (
                            f'Score for question {question_number} '
                            'must be a non-negative integer or blank.'
                        )
                    }, status=400)

                # Update ONLY the two manual fields.
                result_map[question_number]['correct_option'] = correct_option
                result_map[question_number]['score'] = score

            evaluation_page.results = stored_results
            evaluation_page.save(update_fields=['results'])

        return JsonResponse({
            'success': True,
            'message': 'Manual question results saved successfully.'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON request.'
        }, status=400)

    except Exception:
        return JsonResponse({
            'success': False,
            'message': 'An unexpected error occurred while saving results.'
        }, status=500)








# Run tick detection for all uploaded photos of a student
@require_POST
def check_student_photos(request, student_code):

    from checker.services.evaluation_service import evaluate_student_photos

    try:
        evaluation = evaluate_student_photos(student_code)

        messages.success(
            request,
            f'Evaluation completed successfully. '
            f'{evaluation.pages.count()} page(s) processed.'
        )

    except ValueError as error:
        messages.warning(request, str(error))

    except Exception as error:
        messages.error(
            request,
            f'Evaluation failed: {str(error)}'
        )

    # Keep the exam context (if any) so the evaluation page keeps using
    # the same exam's answer key after the redirect.
    target = reverse('evaluate_student_page', args=[student_code])

    exam_id = request.POST.get('exam', '').strip()
    if exam_id and exam_id.isdigit():
        target += f'?exam={exam_id}'

    return redirect(target)






# AJAX endpoint for uploading answer sheet images (page-wise)
@csrf_exempt
def ajax_upload_student_sheets(request, exam_student_id):
    exam_student = get_object_or_404(ExamStudent, pk=exam_student_id)
    if request.method == 'POST':
        images = request.FILES.getlist('images')
        if not images:
            return JsonResponse({'success': False, 'message': 'Please select at least one image to upload.'})
        uploaded_sheets = []
        for image in images:
            answer_sheet = AnswerSheetImage.objects.create(
                exam_student=exam_student,
                image=image
            )
            uploaded_sheets.append({
                'id': answer_sheet.id,
                'image_url': answer_sheet.image.url,
                'uploaded_at': answer_sheet.uploaded_at.strftime('%Y-%m-%d %H:%M')
            })
        return JsonResponse({'success': True, 'uploaded_images': uploaded_sheets})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

# AJAX endpoint for fetching existing sheets for modal display
def ajax_get_existing_sheets(request, exam_student_id):
    exam_student = get_object_or_404(ExamStudent, pk=exam_student_id)
    sheets = AnswerSheetImage.objects.filter(exam_student=exam_student).select_related('table_image')
    sheets_data = []
    for sheet in sheets:
        sheets_data.append({
            'id': sheet.id,
            'image_url': sheet.image.url,
            'uploaded_at': sheet.uploaded_at.strftime('%Y-%m-%d %H:%M'),
            'table_image_id': sheet.table_image.id if sheet.table_image else None
        })
    return JsonResponse({'sheets': sheets_data})




# class StudentList(BaseListView):
    model = Student
    template_name = 'student/list.html'

    def get_queryset(self):
        queryset = super().get_queryset()
        level = self.request.GET.get('level')
        franchise = self.request.GET.get('franchise')
        search = self.request.GET.get('search')

        if level:
            queryset = queryset.filter(current_level_id=level)
        if franchise:
            queryset = queryset.filter(current_franchise_id=franchise)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(student_code__icontains=search) |
                Q(email__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['levels'] = Level.objects.all()
        context['franchises'] = Franchise.objects.all()
        context['current_filters'] = {
            'level': self.request.GET.get('level', ''),
            'franchise': self.request.GET.get('franchise', ''),
            'search': self.request.GET.get('search', ''),
        }
        return context
    

class StudentList(BaseListView):
    model = Student
    template_name = 'student/list.html'
    API_URL = 'https://main.aicrosswindabacus.com/franchise/api/students/'

    def get_queryset(self):
        self.api_error = None
        self.api_count = 0

        params = {
            'page': self.request.GET.get('page', '1'),
        }

        # Pass search and filters to the API only if supported by its backend.
        search = self.request.GET.get('search', '').strip()
        level = self.request.GET.get('level', '').strip()
        franchise = self.request.GET.get('franchise', '').strip()

        if search:
            params['search'] = search
        if level:
            params['level'] = level
        if franchise:
            params['franchise'] = franchise

        try:
            response = requests.get(
                self.API_URL,
                params=params,
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()

            if not isinstance(payload, dict):
                raise ValueError('Expected a paginated JSON object.')

            results = payload.get('results', [])
            if not isinstance(results, list):
                raise ValueError('The API results field is not a list.')

            self.api_count = payload.get('count', len(results))
            self.api_next = payload.get('next')
            self.api_previous = payload.get('previous')

            return [
                {
                    'name': item.get('name') or '',
                    'email': '',
                    'phone': item.get('phone') or '',
                    'franchise': item.get('franchise') or '',
                    'level': item.get('level') or '',
                    'student_code': item.get('student_code') or '',
                    'franchise_location': item.get('franchise_location') or '',
                }
                for item in results
                if isinstance(item, dict)
            ]

        except (requests.RequestException, ValueError) as exc:
            self.api_error = str(exc)
            self.api_next = None
            self.api_previous = None
            return []

    def get_context_data(self, **kwargs):
        # Skip BaseListView.get_context_data(), which assumes a database QuerySet.
        context = super(BaseListView, self).get_context_data(**kwargs)

        context['objects'] = self.object_list
        # Identify students who already have uploaded photos
        student_codes = [
            student.get('student_code')
            for student in self.object_list
            if student.get('student_code')
        ]

        context['uploaded_student_codes'] = set(
            ExamPhoto.objects.filter(
                student_code__in=student_codes
            ).values_list('student_code', flat=True)
        )
        context['levels'] = []
        context['franchises'] = []

        context['current_filters'] = {
            'level': self.request.GET.get('level', ''),
            'franchise': self.request.GET.get('franchise', ''),
            'search': self.request.GET.get('search', ''),
        }

        context['api_error'] = self.api_error
        context['api_count'] = self.api_count
        context['api_next'] = self.api_next
        context['api_previous'] = self.api_previous

        return context













def upload_image(request):
    """Handle image upload and display upload form"""
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                image_obj = form.save()
                messages.success(request, 'Image uploaded successfully!')
                return redirect('analyze_image', image_id=image_obj.id)
            except Exception as e:
                messages.error(request, f'Error uploading image: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = ImageUploadForm()

    return render(request, 'checker/upload.html', {'form': form})


# Django wrapper view specifically for the standalone /analyze/<image_id>/ workflow.
def analyze_image(request, image_id):
    """Analyze an uploaded TableImage and store the results."""
    image_obj = get_object_or_404(TableImage, id=image_id)

    try:
        # Run the existing image analysis pipeline
        sections_data, image_type = _analyse_image(image_obj.image.path)

        # Store detected image type
        image_obj.image_type = image_type

        # Clear any existing results for this image
        TableResult.objects.filter(image=image_obj).delete()
        TableSection.objects.filter(image=image_obj).delete()

        # Store sections and results
        for section_data in sections_data:
            section_obj = TableSection.objects.create(
                image=image_obj,
                section_name=section_data['section_name'],
                section_number=section_data['section_number'],
                total_columns=len(section_data['results'])
            )

            for result in section_data['results']:
                TableResult.objects.create(
                    image=image_obj,
                    section=section_obj,
                    column_number=result['column'],
                    problem_identifier=result.get('problem_id'),
                    extracted_numbers=result.get('numbers', []),
                    calculated_sum=result.get('calculated_answer'),
                    given_answer=result.get('answer'),
                    is_correct=result['status'] == 'Right',
                    numbers_count=len(result.get('numbers', []))
                )

        # Update image processing status
        image_obj.total_sections = len(sections_data)
        image_obj.processed = True
        image_obj.save()

        messages.success(request, 'Image analyzed successfully!')

        return redirect('view_results', image_id=image_obj.id)

    except Exception as e:
        print(f"Error analyzing image {image_obj.id}: {e}")
        messages.error(request, f'Error analyzing image: {str(e)}')
        return redirect('upload_image')

def _analyse_image(image_path):
    image_type = determine_image_type(image_path)

    if image_type == 'NUMBERED_COLUMNS':
        sections_data = process_numbered_columns(image_path)
    elif image_type == 'INDIVIDUAL_PROBLEMS':
        sections_data = process_individual_problems_enhanced(image_path)
    elif image_type == 'MIXED_OPERATIONS':
        sections_data = process_mixed_operations(image_path)
    else:
        sections_data = process_table_image_sections(image_path)

    return sections_data, image_type


def determine_image_type(image_path):
    """Enhanced image type detection to identify mixed operations worksheets"""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("models/gemini-3.6-flash")

    with open(image_path, "rb") as f:
        img = f.read()

    prompt = (
        "Analyze this mathematical worksheet image and determine its format type.\n\n"
        "Possible types:\n"
        "1. NUMBERED_COLUMNS: Has numbered column headers (1,2,3,4...) with numbers below for addition\n"
        "2. INDIVIDUAL_PROBLEMS: Has problems labeled P1, P2, P3... with individual calculations\n" 
        "3. MIXED_OPERATIONS: Contains different sections with various operations like:\n"
        "   - VISUALIZATION section with numbered columns\n"
        "   - MULTIPLICATION section with problems like '462X2=', '199X5='\n"
        "   - DIVISION section with problems like '2034÷4=', '4236÷6='\n"
        "   - May include decimal results\n"
        "4. SECTION_TABLES: Traditional sections (A, B, C) with table format\n\n"
        "Look for keywords like 'MULTIPLICATION', 'DIVISION', 'VISUALIZATION' or math operators (×, ÷, *, /).\n\n"
        "Respond with just the type name: NUMBERED_COLUMNS, INDIVIDUAL_PROBLEMS, MIXED_OPERATIONS, or SECTION_TABLES"
    )

    try:
        response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": img}])
        image_type = response.text.strip()
        print(f"Detected image type: {image_type}")
        return image_type
    except Exception as e:
        print(f"Error determining image type: {e}")
        return 'SECTION_TABLES'


def process_mixed_operations(image_path):
    """Process worksheets with mixed operations including multiplication and division"""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("models/gemini-3.6-flash")

    with open(image_path, "rb") as f:
        img = f.read()

    prompt = (
        "This image contains a mathematical worksheet with multiple sections and different operations.\n\n"
        "SECTION TYPES TO IDENTIFY:\n"
        "1. VISUALIZATION: Tables with numbered columns containing positive/negative numbers for addition\n"
        "2. MULTIPLICATION: Problems like '462X2=', '199X5=', '868X3=' with handwritten answers\n"
        "3. DIVISION: Problems like '2034÷4=', '4236÷6=', '4013÷8=' with handwritten answers (may have decimals)\n\n"
        "For each section, extract all problems with their numbers and handwritten answers.\n\n"
        "FORMAT AS JSON:\n"
        "{\n"
        "  \"sections\": [\n"
        "    {\n"
        "      \"section_name\": \"VISUALIZATION\",\n"
        "      \"section_type\": \"addition\",\n"
        "      \"problems\": [\n"
        "        {\n"
        "          \"problem_id\": \"21\",\n"
        "          \"numbers\": [130, 162, 568, 807, -760, 378],\n"
        "          \"handwritten_answer\": 1285,\n"
        "          \"operation\": \"addition\"\n"
        "        }\n"
        "      ]\n"
        "    },\n"
        "    {\n"
        "      \"section_name\": \"MULTIPLICATION\",\n"
        "      \"section_type\": \"multiplication\",\n"
        "      \"problems\": [\n"
        "        {\n"
        "          \"problem_id\": \"41\",\n"
        "          \"numbers\": [462, 2],\n"
        "          \"handwritten_answer\": 924,\n"
        "          \"operation\": \"multiplication\"\n"
        "        }\n"
        "      ]\n"
        "    },\n"
        "    {\n"
        "      \"section_name\": \"DIVISION\",\n"
        "      \"section_type\": \"division\",\n"
        "      \"problems\": [\n"
        "        {\n"
        "          \"problem_id\": \"51\",\n"
        "          \"numbers\": [2034, 4],\n"
        "          \"handwritten_answer\": 508.5,\n"
        "          \"operation\": \"division\"\n"
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "RULES:\n"
        "- For ADDITION: Extract all numbers in the column\n"
        "- For MULTIPLICATION: Extract the two numbers being multiplied\n"
        "- For DIVISION: Extract dividend and divisor\n"
        "- Handle decimal answers properly (like 508.5, 501.625)\n"
        "- Include negative numbers with minus sign\n"
        "- If handwritten answer is unclear, set to null\n"
        "- Only return JSON"
    )

    tries = 3
    for i in range(tries):
        try:
            time.sleep(8)
            response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": img}])
            response_text = response.text.strip()
            print(f"Mixed Operations Response:\n{response_text}")

            json_block = extract_json_block(response_text)
            data = json.loads(json_block)

            return convert_mixed_operations_to_sections(data)

        except Exception as e:
            if i == tries - 1:
                raise Exception(f"Failed to process mixed operations: {str(e)}")
            time.sleep(15)


def convert_mixed_operations_to_sections(data):
    """Convert mixed operations data to standard sections format"""
    sections_data = []

    for section_idx, section in enumerate(data.get('sections', [])):
        section_name = section.get('section_name', f'Section {section_idx + 1}')
        section_type = section.get('section_type', 'addition')
        problems = section.get('problems', [])

        if not problems:
            continue

        results = []
        for idx, problem in enumerate(problems):
            problem_id = problem.get('problem_id', f'{section_type[0].upper()}{idx + 1}')
            numbers = problem.get('numbers', [])
            answer = problem.get('handwritten_answer')
            operation = problem.get('operation', section_type)

            if not numbers:
                continue

            # Calculate the correct answer based on operation type
            calculated_answer = calculate_answer(numbers, operation)

            # Determine if the answer is correct
            status = determine_correctness(calculated_answer, answer)

            results.append({
                'column': idx + 1,
                'problem_id': problem_id,
                'numbers': numbers,
                'calculated_answer': calculated_answer,
                'answer': answer,
                'status': status,
                'problem_type': operation
            })

        if results:
            sections_data.append({
                'section_name': section_name,
                'section_number': section_idx + 1,
                'results': results
            })

    return sections_data


def calculate_answer(numbers, operation):
    """Calculate the correct answer based on operation type"""
    if not numbers:
        return None

    try:
        if operation == 'addition':
            return sum(numbers)
        elif operation == 'multiplication':
            result = 1
            for num in numbers:
                result *= num
            return result
        elif operation == 'division' and len(numbers) >= 2:
            dividend = Decimal(str(numbers[0]))
            divisor = Decimal(str(numbers[1]))
            if divisor == 0:
                return None
            result = dividend / divisor
            # Round to 3 decimal places for consistency
            return float(result.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))
        else:
            return None
    except (ValueError, TypeError, decimal.InvalidOperation):
        return None


def determine_correctness(calculated_answer, given_answer):
    """Determine if the given answer matches calculated answer, handling decimals"""
    if given_answer is None:
        return "Unanswered"

    if calculated_answer is None:
        return "Error"

    try:
        calc_decimal = Decimal(str(calculated_answer))
        given_decimal = Decimal(str(given_answer))

        # Allow small tolerance for decimal comparisons
        tolerance = Decimal('0.01')

        if abs(calc_decimal - given_decimal) <= tolerance:
            return "Right"
        else:
            return "Wrong"

    except (ValueError, TypeError, decimal.InvalidOperation):
        return "Right" if str(calculated_answer) == str(given_answer) else "Wrong"


def extract_json_block(text):
    """Extract JSON block from response text"""
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*$', '', text)

    # Find JSON block
    start_idx = text.find('{')
    end_idx = text.rfind('}')

    if start_idx != -1 and end_idx != -1:
        return text[start_idx:end_idx + 1]

    return text


def process_numbered_columns(image_path):
    """Process numbered columns format with improved decimal handling"""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("models/gemini-3.6-flash")

    with open(image_path, "rb") as f:
        img = f.read()

    prompt = (
        "This image shows a math worksheet with numbered columns for addition.\n\n"
        "Extract all columns with their numbers and handwritten answers (may include decimals).\n\n"
        "Format as JSON:\n"
        "{\n"
        "  \"columns\": [\n"
        "    {\n"
        "      \"column_number\": 1,\n"
        "      \"numbers\": [2, 1, 1, 5],\n"
        "      \"handwritten_answer\": 9\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "RULES:\n"
        "- Read VERTICALLY down each column\n"
        "- SKIP column headers\n"
        "- Include negative numbers\n"
        "- Handle decimal answers accurately\n"
        "- Only return JSON"
    )

    tries = 5
    for i in range(tries):
        try:
            time.sleep(8)
            response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": img}])
            response_text = response.text.strip()
            print(f"Numbered Columns Response:\n{response_text}")

            json_block = extract_json_block(response_text)
            columns_data = json.loads(json_block)
            validated_columns = validate_and_clean_columns(columns_data)
            return convert_columns_to_sections_enhanced(validated_columns)

        except Exception as e:
            if i == tries - 1:
                raise Exception(f"Failed to process numbered columns: {str(e)}")
            time.sleep(20)


def validate_and_clean_columns(columns_data):
    """Enhanced validation for columns data"""
    cleaned_columns = {"columns": []}

    for column in columns_data.get('columns', []):
        column_num = column.get('column_number', 0)
        numbers = column.get('numbers', [])
        answer = column.get('handwritten_answer')

        #need to remove this logic
        # Remove column number if it appears in numbers
        # numbers = [num for num in numbers if num != column_num]

        # Validate reasonable number count
        if len(numbers) > 8:
            numbers = numbers[:6]

        if numbers and len(numbers) >= 2:
            cleaned_columns["columns"].append({
                'column_number': column_num,
                'numbers': numbers,
                'handwritten_answer': answer
            })

    return cleaned_columns


def convert_columns_to_sections_enhanced(columns_data):
    """Enhanced conversion with proper decimal handling"""
    sections_data = []
    columns = columns_data.get('columns', [])

    if not columns:
        raise Exception("No valid columns found")

    columns_per_section = 10
    section_number = 1

    for i in range(0, len(columns), columns_per_section):
        section_columns = columns[i:i + columns_per_section]
        start_num = section_columns[0]['column_number'] if section_columns else i + 1
        end_num = section_columns[-1]['column_number'] if section_columns else i + len(section_columns)
        section_name = f"Columns {start_num}-{end_num}"

        results = []
        for column in section_columns:
            column_num = column.get('column_number', 0)
            numbers = column.get('numbers', [])
            answer = column.get('handwritten_answer')

            if numbers:
                calculated_sum = sum(numbers)
                status = determine_correctness(calculated_sum, answer)

                results.append({
                    'column': column_num,
                    'problem_id': f'Col{column_num}',
                    'numbers': numbers,
                    'calculated_answer': calculated_sum,
                    'answer': answer,
                    'status': status,
                    'problem_type': 'addition'
                })

        if results:
            sections_data.append({
                'section_name': section_name,
                'section_number': section_number,
                'results': results
            })
            section_number += 1

    return sections_data


def process_individual_problems_enhanced(image_path):
    """Enhanced individual problems processing with operation detection"""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("models/gemini-3.6-flash")

    with open(image_path, "rb") as f:
        img = f.read()

    # prompt = (
    #     "Extract individual math problems with operation detection.\n\n"
    #     "Format as JSON:\n"
    #     "{\n"
    #     "  \"problems\": [\n"
    #     "    {\n"
    #     "      \"problem_id\": \"P1\",\n"
    #     "      \"operation\": \"addition\",\n"
    #     "      \"numbers\": [1, 2, 1],\n"
    #     "      \"handwritten_answer\": 4\n"
    #     "    }\n"
    #     "  ]\n"
    #     "}\n\n"
    #     "Handle decimals accurately and detect operation types correctly."
    # )

    # New Prompt
    prompt = (
    "Analyze this image of a math worksheet containing numbered vertical columns.\n\n"

    "For every visible column, identify exactly these three things:\n"
    "1. The printed column number/header.\n"
    "2. ALL printed arithmetic operands belonging to that column.\n"
    "3. The handwritten answer belonging to that column.\n\n"

    "IMPORTANT EXTRACTION RULES:\n"
    "- The number of printed operands is VARIABLE.\n"
    "- Each column may contain between 2 and 20 printed operands.\n"
    "- Do NOT assume that a column contains 4 operands.\n"
    "- Do NOT assume that all columns contain the same number of operands.\n"
    "- Read each column independently from TOP TO BOTTOM.\n"
    "- The printed column number/header is NOT an operand.\n"
    "- Include EVERY printed operand that belongs to the column.\n"
    "- Do NOT omit an operand because it is visually similar to another number.\n"
    "- Do NOT remove an operand because its value is equal to the column number.\n"
    "- Preserve the exact order of operands from top to bottom.\n"
    "- Preserve the sign of every negative number exactly as printed.\n"
    "- Preserve decimal values exactly when present.\n"
    "- Do NOT calculate the sum yourself.\n"
    "- Do NOT correct, infer, or replace a number based on what the mathematical result should be.\n"
    "- Do NOT invent a number that is unclear or not visible.\n"
    "- Do NOT move a number from one column to another.\n"
    "- The handwritten answer is SEPARATE from the printed operands.\n"
    "- Read the handwritten answer independently; do not derive it from the operands.\n"
    "- If the handwritten answer is unclear, return null rather than guessing.\n"
    "- Every visible numbered column must appear in the JSON output.\n\n"

    "COLUMN BOUNDARY RULE:\n"
    "- Associate a printed operand with the nearest corresponding vertical column.\n"
    "- Do not combine numbers from adjacent columns.\n"
    "- Do not use numbers from the column header as operands.\n\n"

    "OUTPUT RULES:\n"
    "- Return ONLY valid JSON.\n"
    "- Do not return Markdown.\n"
    "- Do not return explanations.\n"
    "- Do not return calculations.\n"
    "- Do not add fields other than the specified fields.\n\n"

    "Return exactly this JSON structure:\n"
    "{\n"
    '  "columns": [\n'
    "    {\n"
    '      "column_number": 1,\n'
    '      "numbers": [],\n'
    '      "handwritten_answer": null\n'
    "    }\n"
    "  ]\n"
    "}\n"
    )

    tries = 5
    for i in range(tries):
        try:
            time.sleep(7)
            response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": img}])
            response_text = response.text.strip()

            json_block = extract_json_block(response_text)
            problems_data = json.loads(json_block)
            return convert_problems_to_sections_enhanced(problems_data)

        except Exception as e:
            if i == tries - 1:
                raise Exception(f"Failed to process individual problems: {str(e)}")
            time.sleep(15)


def convert_problems_to_sections_enhanced(problems_data):
    """Enhanced conversion with operation support"""
    sections_data = []
    problems = problems_data.get('problems', [])

    if not problems:
        raise Exception("No problems found")

    problems_per_section = 10
    section_number = 1

    for i in range(0, len(problems), problems_per_section):
        section_problems = problems[i:i + problems_per_section]
        start_num = i + 1
        end_num = min(i + problems_per_section, len(problems))
        section_name = f"Problems {start_num}-{end_num}"

        results = []
        for idx, problem in enumerate(section_problems):
            problem_id = problem.get('problem_id', f'P{i + idx + 1}')
            operation = problem.get('operation', 'addition')
            numbers = problem.get('numbers', [])
            answer = problem.get('handwritten_answer')

            if numbers:
                calculated_answer = calculate_answer(numbers, operation)
                status = determine_correctness(calculated_answer, answer)

                results.append({
                    'column': idx + 1,
                    'problem_id': problem_id,
                    'numbers': numbers,
                    'calculated_answer': calculated_answer,
                    'answer': answer,
                    'status': status,
                    'problem_type': operation
                })

        if results:
            sections_data.append({
                'section_name': section_name,
                'section_number': section_number,
                'results': results
            })
            section_number += 1

    return sections_data


def process_table_image_sections(image_path):
    """Process traditional section-based tables"""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("models/gemini-3.6-flash")

    with open(image_path, "rb") as f:
        img = f.read()

    prompt = (
        "Extract math table sections (Section A, B, C, etc.).\n\n"
        "Format response as:\n"
        "SECTION: [section_name]\n"
        "[CSV data with Ans row as last row]\n\n"
        "Include ALL numbers whether single-digit or multi-digit.\n"
        "Preserve negative signs.\n"
        "Only output section names and CSV data."
    )

    tries = 5
    for i in range(tries):
        try:
            time.sleep(7)
            response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": img}])
            response_text = response.text.strip()
            print(f"Section Tables Response:\n{response_text}")

            sections_data = parse_multi_section_response(response_text)
            if not sections_data:
                raise Exception("Could not extract valid section data")
            return sections_data

        except Exception as e:
            if i == tries - 1:
                raise Exception(f"Failed to process sections: {str(e)}")
            time.sleep(15)


def parse_multi_section_response(response_text):
    """Enhanced parser for multi-section responses"""
    sections_data = []

    sections = re.split(r'SECTION:\s*', response_text)
    sections = [s.strip() for s in sections if s.strip()]

    for section_idx, section in enumerate(sections):
        lines = section.strip().split('\n')
        if not lines:
            continue

        section_name = lines[0].strip()
        csv_lines = [line.strip() for line in lines[1:] if line.strip()]

        if not csv_lines:
            continue

        # Parse CSV data
        data_rows = []
        for line in csv_lines:
            try:
                row = [float(x.strip()) for x in re.split('[,\t]+', line) if x.strip()]
                if row:
                    data_rows.append(row)
            except ValueError:
                continue

        if len(data_rows) < 2:
            continue

        # Last row is answers, previous rows are numbers
        answer_row = data_rows[-1]
        number_rows = data_rows[:-1]

        results = []
        for col_idx in range(len(answer_row)):
            numbers = [row[col_idx] for row in number_rows if col_idx < len(row)]
            answer = answer_row[col_idx] if col_idx < len(answer_row) else None

            if numbers:
                calculated_sum = sum(numbers)
                status = determine_correctness(calculated_sum, answer)

                results.append({
                    'column': col_idx + 1,
                    'problem_id': f'{section_name}_Col{col_idx + 1}',
                    'numbers': numbers,
                    'calculated_answer': calculated_sum,
                    'answer': answer,
                    'status': status,
                    'problem_type': 'addition'
                })

        if results:
            sections_data.append({
                'section_name': section_name,
                'section_number': section_idx + 1,
                'results': results
            })

    return sections_data

def parse_multi_section_response(response_text):
    """Parse multi-section CSV response"""
    sections_data = []
    sections = re.split(r'SECTION:\s*([^\n]+)', response_text)[1:]
    
    section_number = 1
    for i in range(0, len(sections), 2):
        if i + 1 >= len(sections):
            break
            
        section_name = sections[i].strip()
        section_csv_data = sections[i + 1].strip()
        
        try:
            section_results = process_section_csv_data(section_csv_data)
            if section_results:
                sections_data.append({
                    'section_name': section_name,
                    'section_number': section_number,
                    'results': section_results
                })
                section_number += 1
        except Exception as e:
            print(f"Error processing section {section_name}: {str(e)}")
            continue
    
    return sections_data


def process_section_csv_data(csv_data):
    """Process CSV data for a single section"""
    rows = list(csv.reader(io.StringIO(csv_data)))
    clean_rows = []
    
    for row in rows:
        if not row or not any(cell.strip() for cell in row):
            continue
            
        clean_row = []
        for cell in row:
            cell = cell.strip()
            if cell and is_valid_number(cell):
                clean_row.append(int(cell))
        
        if clean_row:
            clean_rows.append(clean_row)
    
    if len(clean_rows) < 2:
        raise Exception("Not enough valid rows found")
    
    data_rows = clean_rows[:-1]
    ans_row = clean_rows[-1]
    
    results = []
    for col in range(len(ans_row)):
        col_sum = sum(data_rows[row][col] for row in range(len(data_rows)))
        answer = ans_row[col]
        
        # Handle unanswered questions (though rare in section format)
        if answer is None:
            status = "Unanswered"
        elif col_sum == answer:
            status = "Right"
        else:
            status = "Wrong"
            
        results.append({
            'column': col + 1,
            'numbers': [data_rows[row][col] for row in range(len(data_rows))],
            'sum': col_sum,
            'answer': answer,
            'status': status
        })
    
    return results


def is_valid_number(cell_value):
    """Check if a cell value is a valid number"""
    cell_value = str(cell_value).strip()
    if not cell_value:
        return False
    try:
        int(cell_value)
        return True
    except ValueError:
        return False


def view_results(request, image_id):
    """Display results for processed image with sections"""
    image_obj = get_object_or_404(TableImage, id=image_id)
    sections = TableSection.objects.filter(image=image_obj).order_by('section_number')

    if not sections.exists():
        messages.warning(request, 'No results found for this image. Please analyze it first.')
        return redirect('analyze_image', image_id=image_id)

    # Calculate overall statistics including unanswered
    total_results = TableResult.objects.filter(image=image_obj)
    total_columns = total_results.count()
    correct_answers = total_results.filter(is_correct=True).count()
    wrong_answers = total_results.filter(is_correct=False).count()
    
    # Calculate unanswered by checking if given_answer is None
    unanswered = total_results.filter(given_answer__isnull=True).count()
    answered_problems = total_columns - unanswered
    overall_accuracy = (correct_answers / answered_problems * 100) if answered_problems > 0 else 0

    # Prepare section data with results
    sections_with_results = []
    for section in sections:
        results = TableResult.objects.filter(section=section).order_by('column_number')
        sections_with_results.append({
            'section': section,
            'results': results
        })

    context = {
        'image': image_obj,
        'sections_with_results': sections_with_results,
        'total_sections': sections.count(),
        'total_columns': total_columns,
        'correct_answers': correct_answers,
        'wrong_answers': wrong_answers,
        'unanswered': unanswered,
        'answered_problems': answered_problems,
        'overall_accuracy': round(overall_accuracy, 1)
    }

    return render(request, 'checker/results.html', context)


def results_list(request):
    """Display a list of all processed images"""
    images = TableImage.objects.filter(processed=True).order_by('-uploaded_at')
    return render(request, 'checker/results_list.html', {'images': images})


def download_results(request, image_id):
    """Download results as CSV file with sections"""
    image_obj = get_object_or_404(TableImage, id=image_id)
    sections = TableSection.objects.filter(image=image_obj).order_by('section_number')

    response = HttpResponse(content_type='text/csv')
    filename = f"math_results_{image_obj.student_name or 'Unknown'}_{image_obj.center_name or 'Unknown'}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Center Name', 'Section', 'Column', 'Numbers', 'Count', 'Sum', 'Given Answer', 'Status'])

    for section in sections:
        results = TableResult.objects.filter(section=section).order_by('column_number')
        for result in results:
            numbers_str = ', '.join(map(str, result.extracted_numbers))
            answer_display = result.given_answer if result.given_answer is not None else 'Not Answered'
            status_display = 'Right' if result.is_correct else 'Wrong' if result.given_answer is not None else 'Unanswered'
            
            writer.writerow([
                image_obj.student_name or 'Unknown',
                image_obj.center_name or 'Unknown',
                section.section_name,
                result.problem_identifier or f"Column {result.column_number}",
                f"[{numbers_str}]",
                result.numbers_count,
                result.calculated_sum,
                answer_display,
                status_display
            ])

    return response



class ExamList(BaseListView):
    model = Exam
    template_name = 'checker/exam_list.html'
    add_url = reverse_lazy('create_exam')

    def get_queryset(self):
        queryset = super().get_queryset()
        today = date.today()

        name = self.request.GET.get('name')
        exam_date = self.request.GET.get('date')

        if name:
            queryset = queryset.filter(name__icontains=name)
        if exam_date:
            queryset = queryset.filter(exam_date=exam_date)

        queryset = queryset.annotate(
            # total_students=0, #Count('examstudent'),
            # total_answer_sheets=0, #Count('examstudent__answer_sheets'),
            order=Case(
                When(exam_date=today, then=Value(1)),
                When(exam_date__gt=today, then=Value(2)),
                default=Value(3),
            )
        ).order_by('order', '-exam_date')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['today_date'] = date.today().strftime('%Y-%m-%d')
        context['current_filters'] = {
            'name': self.request.GET.get('name', ''),
            'date': self.request.GET.get('date', ''),
        }
        context['user_can_add_exam'] = user.has_perm('checker.add_exam')
        context['user_can_update_exam'] = user.has_perm('checker.change_exam')
        context['user_can_delete_exam'] = user.has_perm('checker.delete_exam')

        return context







# def create_exam(request):
#     if request.method == 'POST':
#         form = ExamForm(request.POST)
#         if form.is_valid():
#             exam = form.save()
            
#             return redirect('exam_detail', exam_id=exam.id)
#     else:
#         form = ExamForm()
#     return render(request, 'checker/create_exam.html', {'form': form})






class ExamCreateView(BaseCreateView):
    template_name = 'checker/create_exam.html'
    model = Exam
    form_class = ExamForm
    success_url = reverse_lazy('exam_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        exam = self.object
        # Assign franchises
      

        exam.save()
        messages.success(self.request, 'Exam created successfully!')
        return redirect(reverse('exam_list'))


class ExamUpdateView(BaseUpdateView):
    template_name = 'checker/exam_update.html'
    model = Exam
    form_class = ExamForm
    success_url = reverse_lazy('exam_list')
    pk_url_kwarg = 'exam_id'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Exam updated successfully!')
        return redirect(reverse('exam_list'))





@csrf_exempt
def upload_answer_sheets(request, exam_student_id):
    if request.method == 'POST':
        exam_student = get_object_or_404(ExamStudent, id=exam_student_id)
        images = request.FILES.getlist('images')
        for image in images:
            AnswerSheetImage.objects.create(exam_student=exam_student, image=image)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request'})



@csrf_exempt
def analyse_answer_sheets(request, exam_student_id):
    exam_student = get_object_or_404(ExamStudent, id=exam_student_id)
    total_score = 0

    for answer_sheet in exam_student.answer_sheets.all():
        try:
            # Create a TableImage object for each answer sheet
            table_image = TableImage.objects.create(
                image=answer_sheet.image,
                student_name=exam_student.student.name,
            )

            answer_sheet.table_image = table_image
            answer_sheet.save()

            sections_data, image_type = _analyse_image(answer_sheet.image.path)
            table_image.image_type = image_type

            # Clear existing results and sections for this table_image
            TableResult.objects.filter(image=table_image).delete()
            TableSection.objects.filter(image=table_image).delete()

            for section_data in sections_data:
                section_obj = TableSection.objects.create(
                    image=table_image,
                    section_name=section_data['section_name'],
                    section_number=section_data['section_number'],
                    total_columns=len(section_data['results'])
                )

                for result in section_data['results']:
                    TableResult.objects.create(
                        image=table_image,
                        section=section_obj,
                        column_number=result['column'],
                        problem_identifier=result.get('problem_id'),
                        extracted_numbers=result.get('numbers', []),
                        calculated_sum=result.get('calculated_answer'),
                        given_answer=result['answer'],
                        is_correct=result['status'] == 'Right',
                        numbers_count=len(result.get('numbers', [])),
                        # Add problem_type field to your model if not exists
                        # problem_type=result.get('problem_type', 'addition')
                    )

                    if result['status'] == 'Right':
                        total_score += 1

            table_image.total_sections = len(sections_data)
            table_image.processed = True
            table_image.save()

        except Exception as e:
            print(f"Error analysing image {answer_sheet.image.name}: {e}")

    exam_student.score = total_score
    exam_student.save()
    return JsonResponse({'success': True, 'score': total_score})


from rest_framework.parsers import JSONParser
from core.models import State, District
from .models import Level

@csrf_exempt

def bulk_create_franchises_students(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        franchises_data = data.get('franchises', [])
        students_data = data.get('students', [])

        states_created = set()
        districts_created = set()
        levels_created = set()

        # Handle State and District assignment/creation for franchises
        for franchise in franchises_data:
            state_name = franchise.get('state_name')
            district_name = franchise.get('district_name')
            # Assign/create State
            if state_name:
                state_obj, s_created = State.objects.get_or_create(name=state_name)
                franchise['state'] = state_obj.id
                if s_created:
                    states_created.add(state_name)
            # Assign/create District
            if district_name:
                if state_name:
                    district_obj, d_created = District.objects.get_or_create(name=district_name, ref_state=state_obj)
                else:
                    first_state = State.objects.first()
                    district_obj, d_created = District.objects.get_or_create(name=district_name, ref_state=first_state)
                franchise['district'] = district_obj.id
                if d_created:
                    districts_created.add(district_name)

        franchise_serializer = FranchiseSerializer(data=franchises_data, many=True)
        franchise_serializer.is_valid(raise_exception=True)
        franchises = franchise_serializer.save()
        franchise_map = {f.name: f for f in franchises}

        # Handle Student assignment for franchise, state, district, and level
        for student in students_data:
            franchise_name = student.get('current_franchise_name')
            if franchise_name and franchise_name in franchise_map:
                student['current_franchise'] = franchise_map[franchise_name].id

            # Assign/create State
            state_name = student.get('state_name')
            if state_name:
                state_obj, s_created = State.objects.get_or_create(name=state_name)
                student['state'] = state_obj.id
                if s_created:
                    states_created.add(state_name)

            # Assign/create District
            district_name = student.get('district_name')
            if district_name:
                if state_name:
                    district_obj, d_created = District.objects.get_or_create(name=district_name, ref_state=state_obj)
                else:
                    first_state = State.objects.first()
                    district_obj, d_created = District.objects.get_or_create(name=district_name, ref_state=first_state)
                student['district'] = district_obj.id
                if d_created:
                    districts_created.add(district_name)

            # Assign/create Level
            level_name = student.get('level') or student.get('current_level_name')
            if level_name:
                level_obj, l_created = Level.objects.get_or_create(name=level_name)
                student['current_level'] = level_obj.id
                if l_created:
                    levels_created.add(level_name)

        student_serializer = StudentSerializer(data=students_data, many=True)
        student_serializer.is_valid(raise_exception=True)
        students = student_serializer.save()
        return JsonResponse({
            'franchises_created': FranchiseSerializer(franchises, many=True).data,
            'students_created': StudentSerializer(students, many=True).data,
            'states_created': list(states_created),
            'districts_created': list(districts_created),
            'levels_created': list(levels_created)
        }, status=status.HTTP_201_CREATED)
    return JsonResponse({'error': 'Only POST method allowed.'}, status=405)
   
# views.py

from django.core.paginator import Paginator

@permission_required('checker.change_exam')
def upload_answer_sheet(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    levels = Level.objects.all()
    franchises = Franchise.objects.all()

    # Filtering logic
    current_filters = {
        'level': request.GET.get('level', ''),
        'name': request.GET.get('name', ''),
        'franchise': request.GET.get('franchise', ''),
        'student_code': request.GET.get('student_code', ''),
    }

    exam_students = ExamStudent.objects.filter(exam=exam).select_related('student', 'student__current_franchise', 'student__current_level')

    if current_filters['level']:
        exam_students = exam_students.filter(student__current_level_id=current_filters['level'])
    if current_filters['name']:
        exam_students = exam_students.filter(student__name__icontains=current_filters['name'])
    if current_filters['franchise']:
        exam_students = exam_students.filter(student__current_franchise_id=current_filters['franchise'])
    if current_filters['student_code']:
        exam_students = exam_students.filter(student_exam_id=current_filters['student_code'])

    # Pagination
    paginator = Paginator(exam_students, 10)  # Show 10 students per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Check if all students have been analyzed
    total_students_in_exam = ExamStudent.objects.filter(exam=exam).count()
    analyzed_students_count = ExamStudent.objects.filter(exam=exam, score__isnull=False).count()
    all_analyzed = total_students_in_exam > 0 and total_students_in_exam == analyzed_students_count

    context = {
        'exam': exam,
        'levels': levels,
        'franchises': franchises,
        'exam_students': page_obj,
        'page_obj': page_obj,
        'current_filters': current_filters,
        'all_analyzed': all_analyzed,
    }
    return render(request, 'checker/upload_answer_sheet.html', context)


@permission_required('checker.add_exam')
def exam_answer_key(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if not exam.number_of_questions:
        messages.error(request, 'Set the number of questions for this exam before creating its answer key.')
        return redirect('exam_list')

    answer_key = getattr(exam, 'answer_key', None)
    form = ExamAnswerKeyForm(
        request.POST or None,
        exam=exam,
        answer_key=answer_key,
    )

    if request.method == 'POST' and form.is_valid():
        ExamAnswerKey.objects.update_or_create(
            exam=exam,
            defaults={
                'answers': form.get_answers(),
                'points': form.get_points(),
            },
        )
        messages.success(request, 'Answer key saved successfully.')
        return redirect('exam_answer_key', exam_id=exam.id)

    question_rows = [
        {
            'number': question_number,
            'answer_field': form[f'question_{question_number}'],
            'points_field': form[f'points_{question_number}'],
        }
        for question_number in range(1, exam.number_of_questions + 1)
    ]
    split_at = max(exam.number_of_questions // 2, 1)

    return render(request, 'checker/exam_answer_key.html', {
        'exam': exam,
        'form': form,
        'left_rows': question_rows[:split_at],
        'right_rows': question_rows[split_at:],
    })



@permission_required('checker.view_exam')
def exam_detail(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    # The assignment panel now lives on the manage-students page, so this
    # page only needs the exam and its students (no franchise options).
    exam_students = _assigned_students_with_status(exam)

    # Statistics cards: students assigned to the exam and students who
    # actually appeared (uploaded at least one answer-sheet photo).
    appeared_count = sum(
        1
        for exam_student in exam_students
        if getattr(exam_student, 'is_uploaded', False)
    )

    context = {
        'exam': exam,
        'exam_students': exam_students,
        'assigned_count': len(exam_students),
        'appeared_count': appeared_count,
    }
    return render(request, 'checker/exam_detail.html', context)


@permission_required('checker.view_exam')
def exam_assign_students_page(request, exam_id):
    """Standalone page for assigning students to an exam.

    Works like the assignment section on the exam detail page, but without
    the upload/evaluate actions - it is focused on assignment management.
    """
    exam = get_object_or_404(Exam, id=exam_id)
    context = _exam_student_assignment_context(exam)
    return render(request, 'checker/exam_assign_students.html', context)


@permission_required('checker.delete_exam')
@require_POST
def delete_exam(request, exam_id):
    """Delete an exam together with everything related to it.

    The answer key, assigned students and legacy answer-sheet image rows
    go with the exam via the database cascade. Uploaded photos and
    evaluation results are keyed by student code, so they are deleted
    explicitly for the students assigned to this exam. The underlying
    image files are removed from storage afterwards (best effort).
    """
    from .models import EvaluationPage

    exam = get_object_or_404(Exam, id=exam_id)
    exam_name = exam.name

    # Students assigned to this exam - their photos and evaluation
    # results are removed with it.
    student_codes = list(
        ExamStudent.objects.filter(exam=exam)
        .exclude(student__student_code__isnull=True)
        .exclude(student__student_code='')
        .values_list('student__student_code', flat=True)
    )

    try:
        with transaction.atomic():
            image_files = []

            # Legacy answer sheets cascade with ExamStudent; collect
            # their files first so they can be cleaned off storage too.
            legacy_sheets = AnswerSheetImage.objects.filter(
                exam_student__exam=exam
            )
            image_files += [
                sheet.image for sheet in legacy_sheets if sheet.image
            ]

            if student_codes:
                photos = ExamPhoto.objects.filter(
                    student_code__in=student_codes
                )
                pages = EvaluationPage.objects.filter(
                    evaluation_run__student_code__in=student_codes
                )
                image_files += [photo.image for photo in photos if photo.image]
                image_files += [
                    page.annotated_image for page in pages
                    if page.annotated_image
                ]

                # EvaluationPage cascades from both EvaluationRun and
                # ExamPhoto, so these deletes remove the pages too.
                EvaluationRun.objects.filter(
                    student_code__in=student_codes
                ).delete()
                photos.delete()

            # Cascades: ExamStudent, ExamAnswerKey, AnswerSheetImage.
            exam.delete()

        # The rows are gone; remove the underlying files from storage
        # as well. Best effort - never fails the request.
        for image_file in image_files:
            try:
                image_file.delete(save=False)
            except Exception:
                pass

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })

    return JsonResponse({
        'success': True,
        'message': f'Successfully deleted exam "{exam_name}"'
    })


def _assigned_students_with_status(exam):
    """Assigned students ordered by franchise with uploaded status and score.

    Shared by the exam detail page and the standalone assign-students page.
    """
    # Ordered by franchise (then student name) so the templates can
    # regroup the list into per-franchise collapsible table sections.
    exam_students = ExamStudent.objects.filter(exam=exam).select_related(
        'student', 'student__current_franchise', 'student__current_level'
    ).order_by(
        'student__current_franchise__name', 'student__name'
    )

    # Uploaded status + evaluated score for the Assigned Students table.
    student_codes = [
        exam_student.student.student_code
        for exam_student in exam_students
        if exam_student.student.student_code
    ]

    photo_counts = {}
    latest_run_by_code = {}

    if student_codes:
        from django.db.models import Count

        photo_counts = dict(
            ExamPhoto.objects.filter(student_code__in=student_codes)
            .values('student_code')
            .annotate(total=Count('id'))
            .values_list('student_code', 'total')
        )

        # Latest evaluation run per student (runs are ordered newest first
        # within each student_code group, so keep only the first seen).
        runs = (
            EvaluationRun.objects.filter(student_code__in=student_codes)
            .prefetch_related('pages')
            .order_by('student_code', '-created_at')
        )
        for run in runs:
            latest_run_by_code.setdefault(run.student_code, run)

    # Total scores, mirroring the "Get Total Score" logic on the evaluation page.
    total_scores = {}
    for code, run in latest_run_by_code.items():
        total = 0
        for page in run.pages.all():
            results = page.results
            if not isinstance(results, list):
                continue
            for result in results:
                if not isinstance(result, dict):
                    continue
                score = result.get('score')
                if (
                    isinstance(score, int)
                    and not isinstance(score, bool)
                    and score >= 0
                ):
                    total += score
        total_scores[code] = total

    for exam_student in exam_students:
        code = exam_student.student.student_code
        exam_student.photo_count = photo_counts.get(code, 0)
        exam_student.is_uploaded = exam_student.photo_count > 0
        exam_student.total_score = (
            total_scores.get(code) if code in latest_run_by_code else None
        )

    return exam_students


def _franchise_options():
    """Active franchises for the assignment dropdown.

    Uses the same central API as the Franchise page, falling back to the
    local database when the API is temporarily unavailable.
    Returns a (franchises, api_error) tuple.
    """
    try:
        response = requests.get(
            'https://main.aicrosswindabacus.com/franchise/all/',
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError('Expected the franchise API to return a list.')

        franchises = sorted(
            (
                {
                    'id': item.get('id'),
                    'name': item.get('name') or '',
                    'franchise_code': item.get('franchise_code') or '',
                    'location': item.get('franchise_location') or '',
                    'is_active': item.get('is_active', False),
                }
                for item in payload
                if isinstance(item, dict) and item.get('id') and item.get('is_active')
            ),
            key=lambda franchise: franchise['name'].casefold(),
        )
        return franchises, None
    except (requests.RequestException, ValueError) as exc:
        # Keep the page usable when the central API is temporarily unavailable.
        franchises = [
            {
                'id': franchise.id,
                'name': franchise.name or '',
                'franchise_code': franchise.franchise_code or '',
                'location': franchise.location or '',
                'is_active': True,
            }
            for franchise in Franchise.objects.all().order_by('name')
        ]
        return franchises, str(exc)


def _exam_student_assignment_context(exam):
    """Common context for the exam detail and assign-students pages."""
    exam_students = _assigned_students_with_status(exam)
    franchises, franchise_api_error = _franchise_options()
    return {
        'exam': exam,
        'exam_students': exam_students,
        'franchises': franchises,
        'franchise_api_error': franchise_api_error,
    }


def get_or_create_local_api_franchise(franchise_id):
    """Create a local relation record for a franchise returned by the API."""
    response = requests.get(
        'https://main.aicrosswindabacus.com/franchise/all/',
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError('Expected the franchise API to return a list.')

    api_franchise = next(
        (
            item for item in payload
            if isinstance(item, dict) and str(item.get('id')) == str(franchise_id)
        ),
        None,
    )
    if not api_franchise:
        raise ValueError('The selected franchise was not found in the API.')

    name = api_franchise.get('name') or ''
    location = api_franchise.get('franchise_location') or api_franchise.get('location') or ''
    franchise_code = api_franchise.get('franchise_code') or None

    # NEW CODE: franchise_code is unique. Check it first so an existing local
    # mirror is reused instead of causing a duplicate-key database error.
    local_franchise = None
    if franchise_code:
        local_franchise = Franchise.objects.filter(franchise_code=franchise_code).first()
    if not local_franchise:
        local_franchise = Franchise.objects.filter(name=name, location=location).first()
    if local_franchise:
        return local_franchise

    # NEW CODE: Store a minimal local copy so Student.current_franchise and
    # Exam.franchises can keep using their existing foreign-key relationships.
    # bulk_create intentionally avoids the Franchise post-save sync signal: this
    # data originated from the central API and must not be sent back to it.
    Franchise.objects.bulk_create([
        Franchise(
            name=name,
            location=location,
            email=api_franchise.get('email') or '',
            mobile=api_franchise.get('mobile') or '',
            owner=api_franchise.get('owner') or '',
            short_name=api_franchise.get('short_name') or name,
            city=api_franchise.get('city') or '',
            franchise_code=franchise_code,
        )
    ])
    return Franchise.objects.filter(name=name, location=location).order_by('-id').first()


def get_franchise_students(request):
    """Load API students, sync them locally, and return local student IDs."""
    franchise_id = request.GET.get('franchise_id')
    level = request.GET.get('level')
    search = request.GET.get('search', '').strip()

    if not franchise_id:
        return JsonResponse({'students': []})

    # PREVIOUS CODE: This queried only local Student rows, so an API franchise
    # could be selected but no students were returned.
    # students = Student.objects.filter(current_franchise_id=franchise_id)

    # NEW CODE: Request students from the same central API used by StudentList.
    params = {
        'franchise': franchise_id,
        'level': level,
        'is_active': 'true',
        'page_size': 1000,
    }
    if search:
        params['search'] = search

    try:
        response = requests.get(
            'https://main.aicrosswindabacus.com/franchise/api/students/',
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        api_students = payload.get('results', []) if isinstance(payload, dict) else payload
        if not isinstance(api_students, list):
            raise ValueError('Expected the student API to return a list.')

        local_franchise = get_or_create_local_api_franchise(franchise_id)
        students_data = []
        for api_student in api_students:
            if not isinstance(api_student, dict):
                continue

            # student_code is the stable API identifier used to prevent local
            # duplicates when this franchise is opened more than once.
            student_code = (api_student.get('student_code') or '').strip()
            if not student_code:
                continue

            level_name = (api_student.get('level') or '').strip()
            level = None
            if level_name:
                level, _ = Level.objects.get_or_create(name=level_name)

            # NEW CODE: Import/update a local student before sending its ID to
            # the browser. The unchanged assignment view can now create the
            # existing ExamStudent relation safely.
            student, _ = Student.objects.update_or_create(
                student_code=student_code,
                defaults={
                    'name': api_student.get('name') or '',
                    'phone': api_student.get('phone') or '',
                    'current_franchise': local_franchise,
                    'current_level': level,
                },
            )
            students_data.append({
                'id': student.id,
                'name': student.name or '',
                'student_code': student.student_code,
                'level': level_name,
                'location': local_franchise.location or '',
                'franchise_name': local_franchise.name,
            })

        return JsonResponse({'students': students_data})
    except (requests.RequestException, ValueError) as exc:
        return JsonResponse({'students': [], 'message': str(exc)}, status=502)
    except Exception as exc:
        # NEW CODE: Return a readable AJAX error instead of silently showing
        # an empty student list when a local mirror/database operation fails.
        return JsonResponse(
            {'students': [], 'message': f'Unable to sync API students: {exc}'},
            status=500,
        )

def assign_students_to_exam(request, exam_id):
    """Assign selected students to exam"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    exam = get_object_or_404(Exam, id=exam_id)
    
    try:
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])
        
        if not student_ids:
            return JsonResponse({'success': False, 'message': 'No students selected'})
        
      
        students = Student.objects.filter(id__in=student_ids).select_related('current_franchise')
        
        created_count = 0
        existing_count = 0
        
        for student in students:
            # Check if student is already assigned to this exam
            exam_student, created = ExamStudent.objects.get_or_create(
                exam=exam,
                student=student,
            )
            
            if created:
                created_count += 1
                # Add franchise to exam if not already present
                if student.current_franchise:
                    exam.franchises.add(student.current_franchise)
            else:
                existing_count += 1
        
        message = f"Successfully assigned {created_count} students to the exam."
        if existing_count > 0:
            message += f" {existing_count} students were already assigned."
        
        return JsonResponse({
            'success': True, 
            'message': message,
            'created': created_count,
            'existing': existing_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

def remove_student_from_exam(request, exam_id, student_id):
    """Remove a student from exam"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    exam = get_object_or_404(Exam, id=exam_id)
    
    try:
        exam_student = ExamStudent.objects.get(exam=exam, student_id=student_id)
        student_name = exam_student.student.name
        exam_student.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully removed {student_name} from the exam'
        })
        
    except ExamStudent.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Student not found in exam'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

def update_manual_score(request, exam_student_id):
    if request.method == 'POST':
        exam_student = get_object_or_404(ExamStudent, id=exam_student_id)
        manual_score = request.POST.get('manual_score')
        if manual_score:
            try:
                exam_student.manual_score = float(manual_score)
                exam_student.save()
                messages.success(request, 'Manual score updated successfully.')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid score value.')
        else:
            messages.warning(request, 'Manual score cannot be empty.')
    return redirect('upload_answer_sheet', exam_id=exam_student.exam.id)

def view_analysis_results(request, exam_student_id):
    exam_student = get_object_or_404(ExamStudent, id=exam_student_id)
    answer_sheets = AnswerSheetImage.objects.filter(exam_student=exam_student).select_related('table_image').prefetch_related('table_image__sections__results')
    
    analysis_data = []
    for sheet in answer_sheets:
        if sheet.table_image:
            total_results = TableResult.objects.filter(image=sheet.table_image)
            total_columns = total_results.count()
            correct_answers = total_results.filter(is_correct=True).count()
            wrong_answers = total_results.filter(is_correct=False).count()
            unanswered = total_results.filter(given_answer__isnull=True).count()
            answered_problems = total_columns - unanswered
            overall_accuracy = (correct_answers / answered_problems * 100) if answered_problems > 0 else 0

            sections_with_results = []
            for section in sheet.table_image.sections.all():
                results = section.results.all().order_by('column_number')
                sections_with_results.append({
                    'section': section,
                    'results': results
                })
            
            analysis_data.append({
                'sheet': sheet,
                'image': sheet.table_image,
                'sections_with_results': sections_with_results,
                'total_sections': sheet.table_image.sections.count(),
                'total_columns': total_columns,
                'correct_answers': correct_answers,
                'wrong_answers': wrong_answers,
                'unanswered': unanswered,
                'answered_problems': answered_problems,
                'overall_accuracy': round(overall_accuracy, 1)
            })

    context = {
        'exam_student': exam_student,
        'analysis_data': analysis_data,
    }
    return render(request, 'checker/view_analysis_results.html', context)

@permission_required('checker.view_exam')
def exam_results(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    levels = Level.objects.filter(student_level__examstudent__exam=exam).distinct()
    franchises = Franchise.objects.filter(student__examstudent__exam=exam).distinct()

    selected_level_id = request.GET.get('level')
    selected_franchise_id = request.GET.get('franchise')

    results = ExamStudent.objects.filter(exam=exam, score__isnull=False).select_related(
        'student', 'student__current_level', 'student__current_franchise'
    ).order_by('student__current_level__name', 'student__current_franchise__name', '-score')

    if selected_level_id:
        results = results.filter(student__current_level_id=selected_level_id)
    if selected_franchise_id:
        results = results.filter(student__current_franchise_id=selected_franchise_id)

    # Rank calculation
    # This is a bit complex to do in a single query with groups.
    # We can do it in python.

    grouped_results = {}
    for r in results:
        level_name = r.student.current_level.name if r.student.current_level else "Uncategorized"
        franchise_name = r.student.current_franchise.name if r.student.current_franchise else "Uncategorized"
        
        if level_name not in grouped_results:
            grouped_results[level_name] = {}
        
        if franchise_name not in grouped_results[level_name]:
            grouped_results[level_name][franchise_name] = []
            
        grouped_results[level_name][franchise_name].append(r)

    # Add rank
    for level_name, franchises_data in grouped_results.items():
        for franchise_name, students in franchises_data.items():
            rank = 1
            for student in students:
                student.rank = rank
                rank += 1

    context = {
        'exam': exam,
        'levels': levels,
        'franchises': franchises,
        'selected_level_id': selected_level_id,
        'selected_franchise_id': selected_franchise_id,
        'grouped_results': grouped_results,
    }
    return render(request, 'checker/exam_results.html', context)
