def get_object[T](catalog_objects: list[object], t: type[T]) -> T | None:
    for obj in catalog_objects:
        if isinstance(obj, t):
            return obj

    return None
