# Reusable prompt builders for AI tools

def build_lesson_assistant_prompt(lesson, user_question, student=None):
    """
    Builds the prompt for the lesson-specific chatbot assistant.
    Enforces age-appropriate explanation, context containment, and tutor guidance encouragement.
    """
    course = lesson.module.course
    class_level = course.class_level.name
    student_name = student.get_full_name() or student.username if student else "Student"
    
    prompt = f"""
    You are an AI learning assistant for Edukom LMS.
    You are helping a student named {student_name} who is in grade/class: {class_level}.
    The student is studying the course: '{course.title}' and the lesson: '{lesson.title}'.
    
    Lesson Content:
    \"\"\"
    {lesson.content}
    \"\"\"
    
    Student's Question:
    {user_question}
    
    Instructions:
    1. Answer the student's question in a clear, friendly, and age-appropriate language suitable for the level '{class_level}'.
    2. Stay strictly within the topic of the lesson and general educational context. Do not answer questions outside learning/educational boundaries.
    3. Do not provide any harmful, inappropriate, or distracting content.
    4. If you do not know the answer or if the question is outside the scope of the lesson, politely say so.
    5. Always encourage the student to ask their tutor or teacher if they need further clarification or if they are confused.
    """
    return prompt.strip()


def build_lesson_summary_prompt(lesson):
    """
    Builds the prompt for generating a simple lesson summary, key points, terms, and revision questions.
    """
    prompt = f"""
    Generate a summary for the following lesson.
    
    Lesson Title: {lesson.title}
    Course: {lesson.module.course.title}
    
    Lesson Content:
    \"\"\"
    {lesson.content}
    \"\"\"
    
    Requirements:
    1. Write a simple, easy-to-understand summary.
    2. List the key points to remember.
    3. Define important terms or vocabulary introduced in the lesson.
    4. Provide 5 revision questions that test the student's comprehension of the content.
    
    Respond in clear Markdown format.
    """
    return prompt.strip()


def build_practice_question_prompt(lesson, difficulty="medium", number_of_questions=5):
    """
    Builds the prompt for generating practice questions for a lesson.
    Expects structured JSON output.
    """
    prompt = f"""
    Generate {number_of_questions} practice questions for the following lesson:
    Lesson: '{lesson.title}'
    Course: '{lesson.module.course.title}'
    Target Difficulty: {difficulty}
    
    Lesson Content:
    \"\"\"
    {lesson.content}
    \"\"\"
    
    You must output a single JSON object matching the following JSON Schema:
    {{
        "questions": [
            {{
                "question_text": "The text of the question",
                "question_type": "objective or true_false or short_answer",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "The correct answer or choice",
                "explanation": "Detailed explanation of why this answer is correct",
                "difficulty": "{difficulty}"
            }}
        ]
    }}
    
    Ensure all choices are listed in 'options' for objective/true_false questions, and options is null or empty for short_answer questions.
    Only return valid JSON. Do not include markdown code block styling like ```json ... ```. Just return raw JSON.
    """
    return prompt.strip()


def build_quiz_generation_prompt(course, module, lesson, question_count=10, difficulty="medium"):
    """
    Builds the prompt for tutors to generate a quiz draft.
    Expects structured JSON output matching QuizDraftSchema.
    """
    lesson_context = f"Lesson: '{lesson.title}'" if lesson else ""
    module_context = f"Module: '{module.title}'" if module else ""
    
    prompt = f"""
    You are a professional educational assistant helping a tutor create a quiz draft.
    Course: '{course.title}'
    {module_context}
    {lesson_context}
    Number of Questions to Generate: {question_count}
    Difficulty: {difficulty}
    
    Provide a title for the quiz, basic instructions, and {question_count} multiple choice objective questions.
    
    You must output a single JSON object matching the following JSON Schema:
    {{
        "title": "A suitable title for the quiz draft",
        "instructions": "General instructions for the students taking this quiz",
        "questions": [
            {{
                "question_text": "The question text",
                "choices": ["Choice 1", "Choice 2", "Choice 3", "Choice 4"],
                "correct_choice": "The exact string representing the correct choice",
                "explanation": "Why this choice is correct",
                "mark": 1
            }}
        ]
    }}
    
    Only return valid JSON. Do not include markdown code block styling. Return raw JSON.
    """
    return prompt.strip()


def build_worksheet_prompt(course, lesson, difficulty="medium"):
    """
    Builds the prompt for tutors to generate a worksheet.
    Expects structured JSON output matching WorksheetSchema.
    """
    prompt = f"""
    You are a professional educational assistant helping a tutor create a worksheet.
    Course: '{course.title}'
    Lesson: '{lesson.title}'
    Difficulty: {difficulty}
    
    Generate a complete educational worksheet draft including sections, questions, and an answer guide.
    
    You must output a single JSON object matching the following JSON Schema:
    {{
        "title": "Title of the worksheet",
        "instructions": "Instructions for the student",
        "sections": [
            {{
                "heading": "Section Heading (e.g. Section A: Vocabulary)",
                "questions": [
                    "Question 1 description",
                    "Question 2 description"
                ]
            }}
        ],
        "answer_guide": "Full text explaining correct answers and criteria for grading."
    }}
    
    Only return valid JSON. Do not include markdown code block styling.
    """
    return prompt.strip()


def build_report_comment_prompt(student, course, report_metrics):
    """
    Builds the prompt to generate a report comment draft based on student metrics.
    Enforces tutor tone, privacy, and drafts only.
    """
    prompt = f"""
    You are a helpful educational tutor writing a progress report comment draft.
    Student name/identifier: {student.get_full_name() or student.username}
    Course: '{course.title}'
    
    Performance Metrics:
    - Lesson Progress: {report_metrics.get('lesson_progress_percentage', 0)}%
    - Assessment Average Score: {report_metrics.get('assessment_average', 0)}%
    - Assignment Average Score: {report_metrics.get('assignment_average', 0)}%
    - Overall Course Percentage: {report_metrics.get('overall_percentage', 0)}%
    
    Privacy Rules:
    - Do not mention or include guardian contact details, invoice amounts, billing status, or other payment/private records.
    - Write in a professional, constructive, encouraging tutor tone.
    
    You must output a single JSON object matching the following JSON Schema:
    {{
        "summary": "High-level summary of the student's progress in this course",
        "strengths": "Specific areas where the student performed well or showed dedication",
        "areas_for_improvement": "Areas where the student needs focus or additional practice",
        "recommendation": "Next steps for the student to improve or maintain progress",
        "tutor_comment": "A ready-to-use, cohesive paragraph combining these insights for the official report card comment."
    }}
    
    Only return valid JSON. Do not include markdown code block styling.
    """
    return prompt.strip()


def build_study_recommendation_prompt(student, course, performance_data):
    """
    Builds the prompt to generate practical study recommendations for a student.
    Expects structured JSON output matching StudyPlanSchema.
    """
    prompt = f"""
    You are an AI study coach helping a student build a personalized study plan.
    Student: {student.get_full_name() or student.username}
    Course: '{course.title}'
    Class Level: {course.class_level.name}
    
    Current Performance Data:
    - Unfinished Lessons: {performance_data.get('unfinished_lessons', [])}
    - Assessment Performance: {performance_data.get('assessment_results', 'No assessments completed yet')}
    - Assignment Performance: {performance_data.get('assignment_results', 'No assignments completed yet')}
    
    Generate personalized study recommendations. Keep it encouraging, actionable, and age-appropriate.
    
    You must output a single JSON object matching the following JSON Schema:
    {{
        "weak_areas": ["List of topics/lessons or skill areas needing improvement"],
        "recommended_lessons": ["Titles of lessons/topics the student should study next"],
        "practice_tasks": ["Actionable tasks/exercises the student should perform"],
        "guardian_support_tip": "A tip for their guardian on how to support them with these areas",
        "weekly_plan": [
            "Day 1-2 Focus: ...",
            "Day 3-4 Focus: ...",
            "Day 5-7 Focus: ..."
        ]
    }}
    
    Only return valid JSON. Do not include markdown code block styling.
    """
    return prompt.strip()


import re

def clean_pii_from_text(text):
    """
    Cleans email addresses, phone numbers, and potential credit card numbers from prompt texts.
    """
    if not text:
        return ""
    # Email regex
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED EMAIL]', text)
    # Phone number regex (basic international/national formats)
    text = re.sub(r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}', '[REDACTED PHONE]', text)
    # Credit Card regex
    text = re.sub(r'\b(?:\d[ -]*?){13,16}\b', '[REDACTED CARD]', text)
    return text

