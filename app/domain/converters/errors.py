class ConverterError(Exception):
    """
    Error assosiated with conversion.
    """


class ConverterNoColumnError(ConverterError):
    """
    Error that indicates that none of the provided columns satisfy the condition of the converter.
    """
