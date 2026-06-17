DEFAULT_MAX_FUZZY_ROWS = 5000


def is_fuzzy_row_count_allowed(total_rows: int, *, max_rows: int = DEFAULT_MAX_FUZZY_ROWS) -> bool:
    return total_rows <= max_rows
