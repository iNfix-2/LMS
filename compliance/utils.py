import re

PROFANITIES = [
    'abuse', 'fuck', 'shit', 'asshole', 'bitch', 'crap', 'bastard', 'cunt', 'dick', 'pussy', 'nigger', 'faggot'
]

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
PHONE_REGEX = re.compile(r'\+?[0-9][0-9\s-]{6,14}[0-9]')

def censor_content(text):
    if not text:
        return "", False, []

    censored = text
    flagged_reasons = []
    is_flagged = False

    # Check for emails
    emails = EMAIL_REGEX.findall(censored)
    if emails:
        is_flagged = True
        flagged_reasons.append("PII detected: Email address")
        censored = EMAIL_REGEX.sub("[EMAIL REDACTED]", censored)

    # Check for phone numbers
    phones = PHONE_REGEX.findall(censored)
    for phone in phones:
        clean_phone = phone.replace(" ", "").replace("-", "")
        # Basic check to avoid masking dates like 2026-07-15
        if "-" in phone and len(phone) == 10 and phone.count("-") == 2:
            continue
        if len(clean_phone) >= 8:
            is_flagged = True
            if "PII detected: Phone number" not in flagged_reasons:
                flagged_reasons.append("PII detected: Phone number")
            censored = censored.replace(phone, "[PHONE REDACTED]")

    # Check for profanities
    for word in PROFANITIES:
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        matches = pattern.findall(censored)
        if matches:
            is_flagged = True
            if "Profanity detected" not in flagged_reasons:
                flagged_reasons.append("Profanity detected")
            censored = pattern.sub("*" * len(word), censored)

    return censored, is_flagged, flagged_reasons
