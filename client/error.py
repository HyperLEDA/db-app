class APIError(Exception):
    code: str
    status: int
    message: str

    @classmethod
    def from_dict(cls, data: dict) -> "APIError":
        res = APIError()
        res.code = data["code"]
        res.status = data["status"]
        res.message = data["message"]

        return res
