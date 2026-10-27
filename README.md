# Автотесты POST /api/Auth/signup

Набор автоматизированных тестов на Python с использованием библиотеки pytest и паттерна ААА для проверки операции создания нового аккаунта (POST) на эндпоинте /api/Auth/signup.

## Установка и запуск

```bash
python -m venv .venv
source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

## Структура

```text
project/
├── tests/
│   ├── __init__.py       # Пакет с тестами
│   ├── test_signup.py    # Позитивные и негативные сценарии
│   └── conftest.py       # HTTP-сессия, Swagger и генерация данных
├── requirements.txt      # Зависимости и их версии
├── README.md             # Инструкция по запуску
└── .gitignore            # Исключение временных файлов
```


## Вывод тестов

```text
pytest tests/ -v
============================= test session starts =============================
collected 14 items

tests/test_signup.py::TestAuthSignup::test_successful_registration PASSED
tests/test_signup.py::TestAuthSignup::test_registration_with_optional_fields PASSED
tests/test_signup.py::TestAuthSignup::test_empty_json_object_is_rejected PASSED
tests/test_signup.py::TestAuthSignup::test_missing_body_is_rejected PASSED
tests/test_signup.py::TestAuthSignup::test_missing_email_is_rejected PASSED
tests/test_signup.py::TestAuthSignup::test_invalid_email_is_rejected[empty] PASSED
tests/test_signup.py::TestAuthSignup::test_invalid_email_is_rejected[whitespace] PASSED
tests/test_signup.py::TestAuthSignup::test_invalid_email_is_rejected[no-at] PASSED
tests/test_signup.py::TestAuthSignup::test_invalid_email_is_rejected[double-at] PASSED
tests/test_signup.py::TestAuthSignup::test_invalid_email_is_rejected[no-domain] PASSED
tests/test_signup.py::TestAuthSignup::test_email_with_invalid_type_is_rejected[integer] PASSED
tests/test_signup.py::TestAuthSignup::test_email_with_invalid_type_is_rejected[boolean] PASSED
tests/test_signup.py::TestAuthSignup::test_optional_field_with_invalid_type_is_rejected[lang-is-number] PASSED
tests/test_signup.py::TestAuthSignup::test_optional_field_with_invalid_type_is_rejected[utm-is-object] PASSED

============================================================================= 14 passed in 4.27s =============

```
