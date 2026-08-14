def normalize_key(value):
    if value is None:
        return ""

    return str(value).strip().casefold()


def remove_duplicates(records):
    """
    Removes duplicate company records.

    Priority is given to:
    - email
    - website
    - company name
    """

    seen = set()
    unique_records = []

    for record in records:
        email = normalize_key(record.get("email"))
        website = normalize_key(record.get("website"))
        company_name = normalize_key(record.get("company_name"))

        key = (
            email,
            website,
            company_name,
        )

        if key in seen:
            continue

        seen.add(key)
        unique_records.append(record)

    return unique_records
