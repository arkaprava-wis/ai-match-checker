from django.urls import path
from . import views


urlpatterns = [



    # New Implementation Student photo upload
    path('students/<path:student_code>/upload/',views.new_upload_page,name='new_upload_page'),

    # Save student photos
    path('students/<path:student_code>/save-photos/',views.save_student_photos,name='save_student_photos'),

    # Student evaluation page
    path('students/<path:student_code>/evaluate/',views.evaluate_student_page,name='evaluate_student_page'),

    # Start student photo evaluation
    path('students/<path:student_code>/check/',views.check_student_photos,name='check_student_photos'),


    # Save manually entered question results
    path('students/<path:student_code>/save-manual-results/',views.save_manual_question_results,name='save_manual_question_results'),


    path('upload/', views.upload_image, name='upload_image'),
    # path('analyze/<int:image_id>/', views._analyse_image, name='analyze_image'),
    path('analyze/<int:image_id>/', views.analyze_image, name='analyze_image'),
    path('results/', views.results_list, name='results_list'),
    path('results/<int:image_id>/', views.view_results, name='view_results'),
    path('download/<int:image_id>/', views.download_results, name='download_results'),
    
    path('exams/', views.ExamList.as_view(), name='exam_list'),
    path('exams/create/', views.ExamCreateView.as_view(), name='create_exam'),
    path('exams/<int:exam_id>/', views.exam_detail, name='exam_detail'),
    # Note: 'assign-students/' below is already the POST endpoint for assigning
    # students (assign_students_to_exam), so this page uses 'manage-students/'.
    path('exams/<int:exam_id>/manage-students/', views.exam_assign_students_page, name='exam_assign_students_page'),
    path('exams/<int:exam_id>/update/', views.ExamUpdateView.as_view(), name='exam_update'),

    path('exams/<int:exam_id>/delete/', views.delete_exam, name='delete_exam'),
    path('exams/<int:exam_id>/answer-key/', views.exam_answer_key, name='exam_answer_key'),
    
    path('upload_answer_sheet/<int:exam_id>/', views.upload_answer_sheet, name='upload_answer_sheet'),
    path('exam/upload-student-sheets/<int:exam_student_id>/', views.ajax_upload_student_sheets, name='ajax_upload_student_sheets'),
    path('exam/get-existing-sheets/<int:exam_student_id>/', views.ajax_get_existing_sheets, name='ajax_get_existing_sheets'),
    path('analyse_answer_sheets/<int:exam_student_id>/', views.analyse_answer_sheets, name='analyse_answer_sheets'),
    path('update_manual_score/<int:exam_student_id>/', views.update_manual_score, name='update_manual_score'),
    path('view_analysis_results/<int:exam_student_id>/', views.view_analysis_results, name='view_analysis_results'),
    path('exam/<int:exam_id>/results/', views.exam_results, name='exam_results'),
    path('students/', views.StudentList.as_view(), name='student_list'),
    path('exam/delete-student-sheet/<int:sheet_id>/', views.ajax_delete_student_sheet, name='ajax_delete_student_sheet'),
    path('exam/change-student-sheet/<int:sheet_id>/', views.ajax_change_student_sheet, name='ajax_change_student_sheet'),

    
# ajax urls
     path('ajax/get-franchise-students/', views.get_franchise_students, name='get_franchise_students'),
    path('exams/<int:exam_id>/assign-students/', views.assign_students_to_exam, name='assign_students_to_exam'),
    path('exams/<int:exam_id>/remove-student/<int:student_id>/', views.remove_student_from_exam, name='remove_student_from_exam'),
]
