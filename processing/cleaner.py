import re


def clean_text(value):
    if value is None:
        return ""

    value = str(value).strip()
    value = re.sub(r"\s+", " ", value)

    return value


def clean_email(email):
    email = clean_text(email).lower()

    if not email:
        return ""

    email = email.replace(" ", "")

    return email


def clean_phone(phone):
    phone = clean_text(phone)

    if not phone:
        return ""

    return re.sub(r"[^\d+]", "", phone)


def clean_website(website):
    website = clean_text(website)

    if not website:
        return ""

    if not website.startswith(("http://", "https://")):
        website = "https://" + website

    return website


def clean_company_record(record):
    return {
        "company_name": clean_text(record.get("company_name")),
        "sector": clean_text(record.get("sector")),
        "phone": clean_phone(record.get("phone")),
        "email": clean_email(record.get("email")),
        "website": clean_website(record.get("website")),
        "address": clean_text(record.get("address")),
    }
