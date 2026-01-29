def estimate_hours(topic: dict) -> int:
    """
    topic: dict with 'score' and 'complexity'
    returns: estimated study hours
    """

    base_hours = {
        "Easy": 2,
        "Medium": 4,
        "Hard": 6
    }

    hours = base_hours.get(topic["complexity"], 2)

    # Fine-tuning using score
    if topic["score"] >= 8:
        hours += 1

    if topic["score"] >= 12:
        hours += 2

    return hours
