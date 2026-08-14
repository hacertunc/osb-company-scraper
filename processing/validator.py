import re


EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)


def is_valid_email(email):
    if not email:
        return False

    return bool(EMAIL_PATTERN.match(email))


def is_valid_phone(phone):
    if not phone:
        return False

    digits = re.sub(r"\D", "", phone)

    return 10 <= len(digits) <= 15


def is_valid_website(website):
    if not website:
        return False

    return website.startswith(
        ("http://", "https://")
    )


def validate_record(record):
    return {
        "company_name_valid": bool(
            record.get("company_name")
        ),
        "email_valid": is_valid_email(
            record.get("email")
        ),
        "phone_valid": is_valid_phone(
            record.get("phone")
        ),
        "website_valid": is_valid_website(
            record.get("website")
        ),
    }
