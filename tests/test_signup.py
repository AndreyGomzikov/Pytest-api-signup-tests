import re

import pytest
import requests
from jsonschema import validate

TIMEOUT = 15
REJECTION_STATUS = 409
TYPE_ERROR_MESSAGE = (
    r"could\s+not\s+be\s+converted\s+to\s+System\.String"
)
NEGATIVE_REPLY = re.compile(
    r"\b(?:error|failed|failure|invalid|rejected|denied|"
    r"unsuccessful|not\s+successful|not\s+created)\b",
    re.IGNORECASE,
)


def _signup(session: requests.Session, url: str, payload: dict):
    return session.post(url, json=payload, timeout=TIMEOUT)


def _assert_registered(response, contract):
    assert response.status_code == contract.success_status, (
        f"Expected HTTP {contract.success_status}, "
        f"got HTTP {response.status_code}: {response.text[:300]!r}"
    )
    content_type = response.headers.get("Content-Type", "").lower()
    if "json" in content_type:
        try:
            result = response.json()
        except requests.exceptions.JSONDecodeError as exc:
            pytest.fail(f"Invalid JSON success response: {exc}")
        validate(instance=result, schema=contract.success_schema)
    elif "text/plain" in content_type:
        result = response.text
    else:
        pytest.fail(f"Unexpected success response type: {content_type!r}")

    assert isinstance(result, str) and result.strip(), (
        "Signup must return a non-empty string on success"
    )
    assert not NEGATIVE_REPLY.search(result), (
        f"Success response describes an error: {result!r}"
    )


def _assert_rejected(
    response, *, code: str, message_pattern: str,
    field: str | None = None, submitted_value=None,
    check_value: bool = False,
):
    """Check the actual HTTP 409 error code and reason, not status alone.

    The public Swagger omits 4xx responses. These assertions follow
    reproducible responses collected from the target API.
    """
    assert response.status_code == REJECTION_STATUS, (
        f"Expected HTTP {REJECTION_STATUS}, got {response.status_code}: "
        f"{response.text[:300]!r}"
    )
    content_type = response.headers.get("Content-Type", "").lower()
    assert "json" in content_type, (
        f"Error response must be JSON, got {content_type!r}"
    )
    try:
        document = response.json()
    except requests.exceptions.JSONDecodeError as exc:
        pytest.fail(f"Invalid JSON error response: {exc}")

    assert isinstance(document, dict), (
        f"Expected error object, got {document!r}"
    )
    details = document.get("error")
    assert isinstance(details, dict), (
        f"Expected JSON field 'error' containing an object: {document!r}"
    )
    assert details.get("code") == code, (
        f"Expected error code {code!r}, got {details.get('code')!r}: "
        f"{document!r}"
    )
    message = details.get("message")
    assert isinstance(message, str) and message.strip(), (
        f"Missing non-empty error message: {document!r}"
    )
    assert re.search(message_pattern, message, re.IGNORECASE), (
        f"Error message {message!r} does not match "
        f"{message_pattern!r}"
    )

    if field is not None:
        if code == "validation.failed":
            assert f"$.{field}" in message, (
                f"Type conversion error not linked to {field!r}: "
                f"{message!r}"
            )
        else:
            assert code.startswith(f"user.{field}."), (
                f"Wrong field in error code {code!r}, expected {field!r}"
            )

    if check_value:
        assert details.get("values") == submitted_value, (
            f"Error describes another value: {details.get('values')!r}, "
            f"submitted {submitted_value!r}"
        )


class TestAuthSignup:

    def test_successful_registration(
        self, api_session, signup_url, signup_contract, new_signup
    ):
        payload = new_signup()
        response = _signup(api_session, signup_url, payload)
        _assert_registered(response, signup_contract)

    def test_registration_with_optional_fields(
        self, api_session, signup_url, signup_contract, new_signup
    ):
        payload = new_signup(optional=True)
        response = _signup(api_session, signup_url, payload)
        _assert_registered(response, signup_contract)

    def test_empty_json_object_is_rejected(
        self, api_session, signup_url
    ):
        payload = {}
        response = _signup(api_session, signup_url, payload)
        _assert_rejected(
            response,
            code="user.email.notNull",
            message_pattern=r"email\s+cannot\s+be\s+null",
            field="email",
        )

    def test_missing_body_is_rejected(self, api_session, signup_url):
        headers = {"Content-Type": "application/json"}
        response = api_session.post(
            signup_url, headers=headers, timeout=TIMEOUT
        )
        _assert_rejected(
            response,
            code="validation.failed",
            message_pattern=r"non-empty\s+request\s+body\s+is\s+required",
        )

    def test_missing_email_is_rejected(self, api_session, signup_url):
        payload = {"lang": "en"}
        response = _signup(api_session, signup_url, payload)
        _assert_rejected(
            response,
            code="user.email.notNull",
            message_pattern=r"email\s+cannot\s+be\s+null",
            field="email",
        )

    @pytest.mark.parametrize(
        "email",
        ["", " ", "plainaddress", "double@@example.com", "user@"],
        ids=["empty", "whitespace", "no-at", "double-at", "no-domain"],
    )
    def test_invalid_email_is_rejected(
        self, email, api_session, signup_url
    ):
        payload = {"email": email}
        response = _signup(api_session, signup_url, payload)
        if email.strip():
            expected_code = "user.email.isInvalid"
            reason = r"invalid\s+email\s+format"
        else:
            expected_code = "user.email.isRequired"
            reason = r"email\s+is\s+required"
        _assert_rejected(
            response,
            code=expected_code,
            message_pattern=reason,
            field="email",
            submitted_value=email,
            check_value=True,
        )

    @pytest.mark.parametrize(
        "email", [123456, True], ids=["integer", "boolean"]
    )
    def test_email_with_invalid_type_is_rejected(
        self, email, api_session, signup_url
    ):
        payload = {"email": email}
        response = _signup(api_session, signup_url, payload)
        _assert_rejected(
            response,
            code="validation.failed",
            message_pattern=TYPE_ERROR_MESSAGE,
            field="email",
        )

    @pytest.mark.parametrize(
        "field, value",
        [("lang", 100), ("utm", {"utm_source": "pytest"})],
        ids=["lang-is-number", "utm-is-object"],
    )
    def test_optional_field_with_invalid_type_is_rejected(
        self, field, value, api_session, signup_url, new_signup
    ):
        payload = new_signup()
        payload[field] = value
        response = _signup(api_session, signup_url, payload)
        _assert_rejected(
            response,
            code="validation.failed",
            message_pattern=TYPE_ERROR_MESSAGE,
            field=field,
        )
