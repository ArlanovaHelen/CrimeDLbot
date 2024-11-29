import openai
from functions_for_bot import find_sql
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("AI_KEY")
def ask_gpt_with_text_context(question, text_data):
    prompt = f"Привіт! Маю таблицю crimes з такою структурою стовпців (в скобках їх значення): \n\n{text_data}\n\n Можеш створити SQL-запит на основі даних, що означають назви стовпчиків з таблиці crimes, питання, по якому потрібно сформувати SQL-запит: {question}\n\n Для формування запиту врахуй, що колонку 'GROUP' треба писати вквадратних дужках. Відповідь:"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an assistant that helps find answers in text data."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000
    )
    answer = response.choices[0].message['content'].strip()
    return answer



def load_text_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        text_data = file.read()
    return text_data



def split_text(text, max_tokens=10000):
    words = text.split()
    chunks = []
    chunk = []
    current_tokens = 0

    for word in words:
        current_tokens += len(word) // 4 + 1
        if current_tokens >= max_tokens:
            chunks.append(' '.join(chunk))
            chunk = [word]
            current_tokens = len(word) // 4 + 1
        else:
            chunk.append(word)

    if chunk:
        chunks.append(' '.join(chunk))

    return chunks

if __name__ == "__main__":
    user_question = input("Введіть ваше питання: ")
    file_path = "data_to_compare.txt"
    text_data = load_text_data(file_path)

    text_chunks = split_text(text_data)

    all_responses = []
    for chunk in text_chunks:
        gpt_response = ask_gpt_with_text_context(user_question, chunk)

        if gpt_response.lower().startswith("пропу"):
            pass
        else:
            all_responses.append(gpt_response)

    if all_responses:
        final_response = "\n".join(all_responses)
        print("\nОстаточна відповідь GPT:")
        print(final_response)
        print(find_sql(gpt_response))
    else:
        print("\nЖодної відповіді не знайдено.")
else:
    pass
