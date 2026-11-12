from django.contrib import admin
from .models import *



@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    pass

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    pass

@admin.register(ExamStudent)
class ExamStudentAdmin(admin.ModelAdmin):
    pass



@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    pass

@admin.register(LevelStage)
class LevelStageAdmin(admin.ModelAdmin):
    pass
    


@admin.register(TableImage)
class TableImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'file_name', 'file_size_kb', 'total_sections', 'uploaded_at', 'processed')
    list_filter = ('processed', 'uploaded_at', 'total_sections')
    search_fields = ('file_name',)
    readonly_fields = ('uploaded_at', 'file_size_kb', 'total_sections')
    
    def file_size_kb(self, obj):
        if obj.file_size:
            return f"{obj.file_size / 1024:.1f} KB"
        return "Unknown"
    file_size_kb.short_description = "File Size"


@admin.register(TableSection)
class TableSectionAdmin(admin.ModelAdmin):
    list_display = ('section_name', 'image', 'section_number', 'total_columns', 'accuracy', 'created_at')
    list_filter = ('section_number', 'created_at', 'image__processed')
    search_fields = ('section_name', 'image__file_name')
    readonly_fields = ('created_at', 'accuracy')
    ordering = ('image', 'section_number')
    
    def accuracy(self, obj):
        return f"{obj.accuracy}%"
    accuracy.short_description = "Accuracy"


@admin.register(TableResult)
class TableResultAdmin(admin.ModelAdmin):
    list_display = ('section', 'column_number', 'calculated_sum', 'given_answer', 'is_correct', 'created_at')
    list_filter = ('is_correct', 'created_at', 'section__section_number')
    search_fields = ('section__section_name', 'section__image__file_name')
    readonly_fields = ('created_at',)
    ordering = ('section__image', 'section__section_number', 'column_number')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('section', 'section__image')