from typing import Any, overload


@overload
def dict_intersect[K, V](dict1: dict[K, V], e2: dict[K, Any]) -> dict[K, V]: ...
@overload
def dict_intersect[K, V](dict1: dict[K, V], e2: set[K]) -> dict[K, V]: ...


def dict_intersect[K, V](dict1: dict[K, V], e2: dict[K, Any] | set[K]) -> dict[K, V]:
    try:
        return {key: dict1[key] for key in dict1.keys() if key in e2.keys()}  # pyright: ignore[reportAttributeAccessIssue]
    except AttributeError:
        return {key: dict1[key] for key in dict1.keys() if key in e2}


@overload
def dict_subtract[K, V](dict1: dict[K, V], e2: dict[K, Any]) -> dict[K, V]: ...
@overload
def dict_subtract[K, V](dict1: dict[K, V], e2: set[K]) -> dict[K, V]: ...


def dict_subtract[K, V](dict1: dict[K, V], e2: dict[K, Any] | set[K]) -> dict[K, V]:
    try:
        return {key: dict1[key] for key in dict1.keys() if key not in e2.keys()}  # pyright: ignore[reportAttributeAccessIssue]
    except AttributeError:
        return {key: dict1[key] for key in dict1.keys() if key not in e2}


def dict_copyorder[K, V](dict: dict[K, V], ref: dict[K, Any]) -> dict[K, V]:
    return {key: dict[key] for key in ref.keys() if key in dict}
