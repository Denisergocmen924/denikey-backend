import secrets
import string


def generate_password(
    length: int = 16,
    uppercase: bool = True,
    lowercase: bool = True,
    numbers: bool = True,
    symbols: bool = True
) -> str:
    chars = ""
    required = []

    if uppercase:
        chars += string.ascii_uppercase
        required.append(secrets.choice(string.ascii_uppercase))
    if lowercase:
        chars += string.ascii_lowercase
        required.append(secrets.choice(string.ascii_lowercase))
    if numbers:
        chars += string.digits
        required.append(secrets.choice(string.digits))
    if symbols:
        chars += string.punctuation
        required.append(secrets.choice(string.punctuation))

    if not chars:
        raise ValueError("En az bir karakter tipi seçilmelidir")

    remaining = [secrets.choice(chars) for _ in range(length - len(required))]
    password_list = required + remaining
    secrets.SystemRandom().shuffle(password_list)

    return "".join(password_list)