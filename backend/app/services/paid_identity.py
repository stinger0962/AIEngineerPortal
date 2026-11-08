"""In-process identity type; callers cannot authenticate by supplying its string."""


class PaidPrincipal(str):
    def __new__(cls, account_id: int):
        principal = super().__new__(cls, f"paid-account:{account_id}")
        principal.account_id = account_id
        return principal
