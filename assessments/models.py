from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from courses.models import Course, Module

class Assessment(models.Model):
    ASSESSMENT_TYPES = [
        ('quiz', 'Quiz'),
        ('ca_test', 'Continuous Assessment Test'),
        ('exam', 'Exam'),
        ('practice', 'Practice'),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assessments')
    module = models.ForeignKey(Module, on_delete=models.SET_NULL, null=True, blank=True, related_name='assessments')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPES, default='quiz')
    time_limit_minutes = models.PositiveIntegerField(default=0)
    pass_mark = models.PositiveIntegerField(default=50)
    is_published = models.BooleanField(default=False)
    show_corrections = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Assessment.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def total_questions(self):
        return self.questions.count()

    def total_marks(self):
        return self.questions.aggregate(total=models.Sum('mark'))['total'] or 0

    def __str__(self):
        return f"{self.title} ({self.get_assessment_type_display()})"

class Question(models.Model):
    QUESTION_TYPES = [
        ('objective', 'Objective'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
        ('theory', 'Theory'),
    ]
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='objective')
    mark = models.PositiveIntegerField(default=1)
    explanation = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q: {self.question_text[:50]}..."

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.choice_text} ({'Correct' if self.is_correct else 'Incorrect'})"

class AssessmentAttempt(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
    ]
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assessment_attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(default=0)
    total_marks = models.FloatField(default=0)
    percentage = models.FloatField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-started_at']

    def calculate_score(self):
        total_attempt_score = 0
        total_possible_marks = self.assessment.total_marks()
        
        for ans in self.answers.all().select_related('question'):
            q = ans.question
            if q.question_type in ['objective', 'true_false']:
                is_correct = False
                if ans.selected_choice:
                    is_correct = ans.selected_choice.is_correct
                elif ans.text_answer:
                    correct_choice = q.choices.filter(is_correct=True).first()
                    if correct_choice:
                        is_correct = (ans.text_answer.strip().lower() == correct_choice.choice_text.strip().lower())
                
                ans.is_correct = is_correct
                ans.mark_awarded = q.mark if is_correct else 0
                ans.is_graded = True
                ans.save()
                total_attempt_score += ans.mark_awarded
            else:
                total_attempt_score += ans.mark_awarded
                
        self.score = total_attempt_score
        self.total_marks = total_possible_marks
        if total_possible_marks > 0:
            self.percentage = round((total_attempt_score / total_possible_marks) * 100, 2)
        else:
            self.percentage = 0
            
        self.status = 'submitted'
        self.submitted_at = timezone.now()
        self.save()

    def recalculate_manual_score(self):
        total_attempt_score = 0
        total_possible_marks = self.assessment.total_marks()
        
        for ans in self.answers.all().select_related('question'):
            total_attempt_score += ans.mark_awarded
                
        self.score = total_attempt_score
        self.total_marks = total_possible_marks
        if total_possible_marks > 0:
            self.percentage = round((total_attempt_score / total_possible_marks) * 100, 2)
        else:
            self.percentage = 0
            
        self.save()

    def __str__(self):
        return f"{self.student.username} - {self.assessment.title} ({self.status})"

class StudentAnswer(models.Model):
    attempt = models.ForeignKey(AssessmentAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True)
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)
    mark_awarded = models.FloatField(default=0)
    feedback = models.TextField(blank=True)
    is_graded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ans for {self.question.question_text[:30]} by {self.attempt.student.username}"
