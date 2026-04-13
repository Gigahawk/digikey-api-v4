import time
from pathlib import Path
import json

import requests
from bravado.client import SwaggerClient
from bravado.requests_client import RequestsClient, Authenticator


class DigikeyAuthenticator(Authenticator):
    def __init__(self, host: str, client_id: str, token: str):
        super().__init__(host=host)
        self.__client_id = client_id
        self.__token = token

    def apply(self, req: requests.Request) -> requests.Request:
        req.headers.setdefault(
            "X-DIGIKEY-Client-Id",
            self.__client_id,
        )
        req.headers.setdefault(
            "Authorization",
            f"Bearer {self.__token}",
        )
        return req


class DigikeyClient:
    def __init__(self, client_id: str, client_secret: str, sandbox: bool = False):
        self.__client_id = client_id
        self.__client_secret = client_secret
        self.sandbox: bool = sandbox
        self.__token2_json = None

    @property
    def _http_client(self) -> RequestsClient:
        client = RequestsClient()
        client.authenticator = DigikeyAuthenticator(
            host=self._api_host,
            client_id=self.__client_id,
            token=self._token2,
        )
        return client

    def _swagger_path(self, name: str) -> str:
        return str(Path(__file__).absolute().parent / "swagger" / name)

    def _swagger_dict(self, name: str) -> dict:
        with open(self._swagger_path(name), "r") as f:
            data = json.load(f)
            data["host"] = self._api_host
            return data

    def _client(self, name: str) -> SwaggerClient:
        return SwaggerClient.from_spec(
            self._swagger_dict(name),
            http_client=self._http_client,
            config={"validate_responses": False},
        )

    @property
    def product_search(self):
        return self._client("ProductSearch.json")

    @property
    def _api_host(self) -> str:
        if self.sandbox:
            return "sandbox-api.digikey.com"
        else:
            return "api.digikey.com"

    @property
    def _api_host_https(self) -> str:
        return f"https://{self._api_host}"

    @property
    def _token_endpoint(self) -> str:
        return f"{self._api_host_https}/v1/oauth2/token"

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
