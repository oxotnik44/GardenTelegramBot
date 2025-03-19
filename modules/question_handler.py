user_data = {}  # {user_id: {"photos": [(timestamp, file_id)], "questions": [{"text": str, "message_id": int}] }}

def save_question(user_id, question_text, message_id=None):
    """Сохраняет вопрос пользователя и его message_id"""
    if question_text.endswith("?"):
        question_entry = {"text": question_text, "message_id": message_id}
        # Добавляем вопрос в список вопросов пользователя
        user_data.setdefault(user_id, {"photos": [], "questions": []})["questions"].append(question_entry)

def get_questions(user_id):
    """Возвращает список вопросов пользователя"""
    return user_data.get(user_id, {}).get("questions", [])

def delete_question(user_id, idx):
    """Удаляет вопрос по индексу для данного пользователя"""
    user_questions = user_data.get(user_id, {}).get("questions", [])
    # Проверяем, существует ли вопрос с данным индексом
    if 0 <= idx < len(user_questions):
        # Удаляем вопрос по индексу
        del user_questions[idx]
        # Обновляем список вопросов после удаления
        user_data[user_id]["questions"] = user_questions
        return True
    return False
