# Алгоритм Луна для проверки номера карты
def validate_card(card_number: str) -> bool:
    digits = [int(d) for d in card_number if d.isdigit()]
    checksum = 0
    reverse_digits = digits[::-1]

    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            digit *= 2
        if digit > 9:
            digit -= 9
        checksum += digit

    return checksum % 10 == 0
