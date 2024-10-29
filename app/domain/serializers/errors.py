class SerializerError(Exception):
    """
    Error assosiated with serialization.
    """


class SerializerNotEnoughInfoError(SerializerError):
    """
    Error that indicates, that object does not have some or all of the relevant properties
    to be saved to the layer 1.
    """
