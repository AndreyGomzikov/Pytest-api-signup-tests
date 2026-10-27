import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from uuid import uuid4

import pytest
import requests
from faker import Faker
from jsonschema import validate

BASE_URL = "https://automation.tivaliclub.com/fcle"
HTTP_TIMEOUT = 15


@dataclass(frozen=True)
class SignupContract:
    """The published OpenAPI schema for POST /api/Auth/signup."""

    request_schema: dict
    success_schema: dict
    success_status: int

    @classmethod
    def from_openapi(cls, specification: dict) -> "SignupContract":
        operation = specification["paths"]["/api/Auth/signup"]["post"]
        request_body = operation["requestBody"]
        request_schema = request_body["content"]["application/json"]["schema"]
        if "$ref" in request_schema:
            reference = request_schema["$ref"]
            if not reference.startswith("#/components/schemas/"):
                raise ValueError(f"Unsupported schema reference: {reference}")
            schema_name = reference.rsplit("/", 1)[-1]
            request_schema = (
                specification["components"]["schemas"][schema_name]
            )

        statuses = operation["responses"]
        response_schema = (
            statuses["200"]["content"]["application/json"]["schema"]
        )
        properties = request_schema.get("properties", {})
        if "email" not in request_schema.get("required", []):
            raise ValueError("Swagger no longer requires the email field")
        if "email" not in properties:
            raise ValueError("Swagger does not contain an email property")
        if response_schema.get("type") != "string":
            raise ValueError("Swagger changed the 200 response from string")
        return cls(request_schema, response_schema, 200)


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.getenv("SIGNUP_BASE_URL", BASE_URL).rstrip("/")


@pytest.fixture(scope="session")
def api_session() -> Iterator[requests.Session]:
    with requests.Session() as session:
        session.headers.update({"Accept": "application/json"})
        yield session


@pytest.fixture(scope="session")
def signup_contract(
    api_session: requests.Session, base_url: str
) -> SignupContract:
    swagger_url = os.getenv(
        "SIGNUP_SWAGGER_URL", f"{base_url}/swagger/v1/swagger.json"
    )
    try:
        response = api_session.get(swagger_url, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return SignupContract.from_openapi(response.json())
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        pytest.fail(f"Cannot read signup OpenAPI schema: {exc}", pytrace=False)


@pytest.fixture(scope="session")
def signup_url(base_url: str) -> str:
    return f"{base_url}/api/Auth/signup"


@pytest.fixture(autouse=True)
def isolate_cookies(api_session: requests.Session) -> Iterator[None]:
    api_session.cookies.clear()
    yield
    api_session.cookies.clear()


@pytest.fixture
def new_signup(signup_contract: SignupContract) -> Callable[..., dict]:
    fake = Faker("en_US")
    domain = os.getenv("SIGNUP_TEST_EMAIL_DOMAIN", "example.com")
    domain = domain.strip().lower()
    if not domain or "@" in domain or " " in domain:
        raise ValueError("Invalid SIGNUP_TEST_EMAIL_DOMAIN")

    def factory(*, optional: bool = False) -> dict:
        name = fake.pystr(min_chars=6, max_chars=6).lower()
        email = f"qa.{name}.{uuid4().hex}@{domain}"
        result = {"email": email}
        if optional:
            if "lang" in signup_contract.request_schema["properties"]:
                result["lang"] = "en"
            if "utm" in signup_contract.request_schema["properties"]:
                result["utm"] = '{"utm_source":"pytest"}'
        validate(instance=result, schema=signup_contract.request_schema)
        return result

    return factory
