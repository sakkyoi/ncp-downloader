from functools import reduce


def deep_get(data: dict, keys: list, default=None):
    try:
        return reduce(lambda c, k: c[k], keys, data)
    except (KeyError, TypeError):
        return default
