# question_handler.py

user_data = {}  # {user_id: {"photos": [(timestamp, file_id)], "questions": [question_text]}}

def save_question(user_id, question_text):
    """Сохраняет вопрос пользователя"""
    if question_text.endswith("?"):
        user_data.setdefault(user_id, {"photos": [], "questions": []})["questions"].append(question_text)

def get_questions(user_id):
    """Возвращает список вопросов пользователя"""
    return user_data.get(user_id, {}).get("questions", [])
