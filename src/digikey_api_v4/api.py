import requests
import time


class DigikeyClient:
    def __init__(self, client_id: str, client_secret: str, sandbox: bool = False):
        self.__client_id = client_id
        self.__client_secret = client_secret
        self.sandbox: bool = sandbox
        self.__token2_json = None

    @property
    def _api_host(self) -> str:
        if self.sandbox:
            return "https://sandbox-api.digikey.com"
        else:
            return "https://api.digikey.com"

    @property
    def _token_endpoint(self) -> str:
        return f"{self._api_host}/v1/oauth2/token"

    @property
    def _token2_expired(self) -> bool:
        if self.__token2_json is None:
            return True
        try:
            if time.time() >= self.__token2_json["expires_at"]:
                return True
            return False
        except KeyError:
            return True

    @property
    def _token2_json(self) -> dict:
        """2 legged auth token"""
        if self._token2_expired:
            print("Requesting new 2 legged auth token")
            resp = requests.post(
                self._token_endpoint,
                data={
                    "client_id": self.__client_id,
                    "client_secret": self.__client_secret,
                    "grant_type": "client_credentials",
                },
            )
            resp.raise_for_status()
            self.__token2_json = resp.json()
            self.__token2_json["expires_at"] = (
                self.__token2_json["expires_in"] + time.time()
            )

        return self.__token2_json

    @property
    def _token2(self) -> str:
        return self._token2_json["access_token"]
