# JSON schemas for validating structured AI outputs

PRACTICE_QUESTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_text": {"type": "string"},
                    "question_type": {"type": "string"},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "correct_answer": {"type": "string"},
                    "explanation": {"type": "string"},
                    "difficulty": {"type": "string"}
                },
                "required": ["question_text", "question_type", "correct_answer", "explanation", "difficulty"]
            }
        }
    },
    "required": ["questions"]
}

QUIZ_DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "instructions": {"type": "string"},
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_text": {"type": "string"},
                    "choices": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "correct_choice": {"type": "string"},
                    "explanation": {"type": "string"},
                    "mark": {"type": "integer"}
                },
                "required": ["question_text", "choices", "correct_choice", "explanation", "mark"]
            }
        }
    },
    "required": ["title", "instructions", "questions"]
}

WORKSHEET_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "instructions": {"type": "string"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string"},
                    "questions": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["heading", "questions"]
            }
        },
        "answer_guide": {"type": "string"}
    },
    "required": ["title", "instructions", "sections", "answer_guide"]
}

REPORT_COMMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "strengths": {"type": "string"},
        "areas_for_improvement": {"type": "string"},
        "recommendation": {"type": "string"},
        "tutor_comment": {"type": "string"}
    },
    "required": ["summary", "strengths", "areas_for_improvement", "recommendation", "tutor_comment"]
}

STUDY_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "weak_areas": {
            "type": "array",
            "items": {"type": "string"}
        },
        "recommended_lessons": {
            "type": "array",
            "items": {"type": "string"}
        },
        "practice_tasks": {
            "type": "array",
            "items": {"type": "string"}
        },
        "guardian_support_tip": {"type": "string"},
        "weekly_plan": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["weak_areas", "recommended_lessons", "practice_tasks", "guardian_support_tip", "weekly_plan"]
}

def validate_json_structure(data, schema):
    """
    Simple fallback-friendly json schema validator.
    Returns True if valid, False otherwise.
    """
    if not isinstance(data, dict):
        return False
    
    # Check top-level required fields
    for field in schema.get("required", []):
        if field not in data:
            return False
            
    # Check properties
    properties = schema.get("properties", {})
    for key, val in data.items():
        if key not in properties:
            continue
        prop_type = properties[key].get("type")
        if prop_type == "string" and not isinstance(val, str):
            return False
        elif prop_type == "integer" and not isinstance(val, int) and not isinstance(val, float):
            return False
        elif prop_type == "array":
            if not isinstance(val, list):
                return False
            # Check items
            item_schema = properties[key].get("items", {})
            if item_schema.get("type") == "object":
                for item in val:
                    if not isinstance(item, dict):
                        return False
                    for sub_field in item_schema.get("required", []):
                        if sub_field not in item:
                            return False
    return True
