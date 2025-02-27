from tqdm import tqdm

def create_progress_bar(total, desc, unit="items"):
    """
    Creates and returns a tqdm progress bar.
    :param total: Total number of items.
    :param desc: Description of the progress bar.
    :param unit: Unit of measurement for items (default: "items").
    :return: A tqdm progress bar object.
    """
    # Validate inputs
    if not isinstance(total, int) or total < 0:
        raise ValueError(f"'total' must be a non-negative integer. Got: {total}")
    if not isinstance(desc, str) or not desc.strip():
        raise ValueError(f"'desc' must be a non-empty string. Got: {desc}")

    return tqdm(total=total, desc=desc, unit=unit)
