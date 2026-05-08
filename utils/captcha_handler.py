from dataclasses import dataclass


@dataclass
class CaptchaResult:
    token: str
    provider: str


class CaptchaSolver:
    """Integration seam for CAPTCHA providers like 2Captcha."""

    def __init__(self, provider_api_key: str | None = None) -> None:
        self.provider_api_key = provider_api_key

    def solve(self, site_key: str, page_url: str) -> CaptchaResult:
        if not self.provider_api_key:
            raise RuntimeError(
                "CAPTCHA challenge detected. Configure 2Captcha and implement API call in CaptchaSolver.solve()."
            )
        # 2Captcha integration would post site_key/page_url, poll for completion, and return the token here.
        raise NotImplementedError("2Captcha API integration is not enabled in this demo project.")
