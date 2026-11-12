
import cv2
import numpy as np

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from pathlib import Path
import os

from checker.models import ExamPhoto, EvaluationRun, EvaluationPage
from checker.services.tick_detection import process_image




def evaluate_student_photos(student_code):
    """
    Evaluate all photos uploaded by a particular student.

    Returns the completed EvaluationRun object.
    """

    # Retrieve only this student's uploaded photos.
    photos = ExamPhoto.objects.filter(
        student_code=student_code
    ).order_by('uploaded_at', 'id')

    if not photos.exists():
        raise ValueError(
            f"No uploaded photos found for student {student_code}."
        )

    # Create a new evaluation record.
    evaluation_run = EvaluationRun.objects.create(
        student_code=student_code,
        status='PROCESSING'
    )

    try:
        for page_number, photo in enumerate(photos, start=1):

            # Read the original uploaded photo.
            photo.image.open('rb')

            try:
                image_bytes = photo.image.read()
            finally:
                photo.image.close()

            image_array = np.frombuffer(
                image_bytes,
                dtype=np.uint8
            )

            original_image = cv2.imdecode(
                image_array,
                cv2.IMREAD_COLOR
            )

            if original_image is None:
                raise ValueError(
                    f"Could not read uploaded photo: {photo.image.name}"
                )

            # Calculate the starting question number for this paper.
            questions_per_paper = 30

            start_question = (
                (page_number - 1) * questions_per_paper
            ) + 1

            results, annotated_image = process_image(
                image=original_image,
                page_number=page_number,
                start_question=start_question
            )

            # Convert the annotated OpenCV image into PNG bytes.
            success, encoded_image = cv2.imencode(
                '.png',
                annotated_image
            )

            if not success:
                raise ValueError(
                    f"Could not generate annotated image for page {page_number}."
                )

            # Save the annotated image and its associated results.
            annotated_filename = (
                f"page_{page_number:03d}_annotated.png"
            )

            page = EvaluationPage(
                evaluation_run=evaluation_run,
                source_photo=photo,
                page_number=page_number,
                results=results
            )

            page.annotated_image.save(
                annotated_filename,
                ContentFile(encoded_image.tobytes()),
                save=True
            )

        # Mark the evaluation as completed.
        evaluation_run.status = 'COMPLETED'
        evaluation_run.completed_at = timezone.now()
        evaluation_run.save(
            update_fields=['status', 'completed_at']
        )

        return evaluation_run

    except Exception as error:
        evaluation_run.status = 'FAILED'
        evaluation_run.error_message = str(error)
        evaluation_run.save(
            update_fields=['status', 'error_message']
        )

        raise
