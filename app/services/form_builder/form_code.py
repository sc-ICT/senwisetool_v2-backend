from datetime import datetime
from secrets import choice
from string import ascii_uppercase


def generate_form_code(
    user_id: int,
) -> str:
    random_part = "".join(choice(ascii_uppercase) for _ in range(6))

    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S",
    )

    return f"FORM{user_id}_{random_part}_{timestamp}"
