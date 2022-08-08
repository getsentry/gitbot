from typing import Optional, Any


class RepoUrl:
    """Represents a repository URL with some protections to avoid leaking secrets

    Shamelessly pulled and adapted from pydantic <3
    https://github.com/pydantic/pydantic/blob/ea870115b71c3c8843f454989d0ccffe3edc0279/pydantic/types.py#L801-L848


    """

    def __init__(
        self, repo: str, user: Optional[str] = None, pat: Optional[str] = None
    ):
        if pat and user:
            self._secret_value = f"https://{user}:{pat}@github.com/{repo}"
            self.has_pat = True
            self._pat = pat
            self._user = user
            self._repo = repo
        else:
            self._secret_value = f"git@github.com:/{repo}"
            self.has_pat = False

    def __str__(self) -> str:
        if not self._secret_value:
            return ""

        if self.has_pat:
            return f"https://{self._user}:**REDACTED**@github.com/{self._repo}"
        else:
            return f"git@github.com:/{self._repo}"

    def __repr__(self) -> str:
        return f"RepoUrl('{self}')"

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, RepoUrl)
            and self.get_secret_value() == other.get_secret_value()
        )

    def get_secret_value(self) -> str:
        """
        Returns the secret value as a plaintext string. Careful not to leak it!
        """
        return self._secret_value
