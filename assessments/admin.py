from django.contrib import admin
from .models import Assessment, Question, Choice, AssessmentAttempt, StudentAnswer

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3

class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1

@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'assessment_type', 'is_published', 'created_at')
    list_filter = ('assessment_type', 'is_published', 'course')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [QuestionInline]

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text_short', 'assessment', 'question_type', 'mark', 'order')
    list_filter = ('question_type', 'assessment__course', 'assessment')
    search_fields = ('question_text', 'explanation')
    inlines = [ChoiceInline]

    def question_text_short(self, obj):
        return obj.question_text[:50] + '...' if len(obj.question_text) > 50 else obj.question_text
    question_text_short.short_description = 'Question Text'

@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('choice_text', 'question', 'is_correct', 'order')
    list_filter = ('is_correct', 'question__assessment')
    search_fields = ('choice_text',)

@admin.register(AssessmentAttempt)
class AssessmentAttemptAdmin(admin.ModelAdmin):
    list_display = ('assessment', 'student', 'score', 'total_marks', 'percentage', 'status', 'submitted_at')
    list_filter = ('status', 'assessment', 'submitted_at')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'assessment__title')

@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'question', 'selected_choice', 'is_correct', 'mark_awarded')
    list_filter = ('is_correct', 'attempt__assessment')
    search_fields = ('attempt__student__username', 'question__question_text', 'text_answer')
