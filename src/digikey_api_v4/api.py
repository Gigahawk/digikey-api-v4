import time
from pathlib import Path
import json
import functools
import inspect

import requests
from bravado.client import SwaggerClient
from bravado.requests_client import RequestsClient, Authenticator
from bravado.exception import HTTPGatewayTimeout, HTTPBadGateway

from digikey_api_v4.constants import LocaleCurrency, LocaleLanguage, LocaleSite


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


def swagger_call(func):
    @functools.wraps(func)
    def _wrapper(self: "DigikeyClient", *args, **kwargs):
        # Extract call specific arguments
        sig = inspect.signature(func)
        bound = sig.bind(self, *args, **kwargs)
        bound.apply_defaults()
        params = bound.arguments
        params.pop("self")
        params = self._params(**params)

        retries = self.retries
        retry_delay = self.retry_delay

        swagger_func = func(self, *args, **kwargs)
        for idx in range(retries):
            idx += 1
            try:
                return swagger_func(**params)
            except (HTTPBadGateway, HTTPGatewayTimeout):
                # Handle random 504/502 errors
                print(f"Call {idx} to {swagger_func} failed")
                if idx < retries:
                    print(f"Retrying after {retry_delay} seconds...")
                    time.sleep(retry_delay)

    return _wrapper


class DigikeyClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        sandbox: bool = False,
        locale_lang: LocaleLanguage = LocaleLanguage.EN,
        locale_currency: LocaleCurrency = LocaleCurrency.CAD,
        locale_site: LocaleSite = LocaleSite.CA,
        account_id: str | None = None,
        retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.__client_id = client_id
        self.__client_secret = client_secret
        self.sandbox: bool = sandbox
        self.locale_lang: LocaleLanguage = locale_lang
        self.locale_currency: LocaleCurrency = locale_currency
        self.locale_site: LocaleSite = locale_site
        self.account_id = None
        self.__token2_json = None
        self.retries = retries
        self.retry_delay = retry_delay

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
            config={
                # Sometimes returns invalid responses?
                "validate_responses": False,
            },
        )

    def _params(self, **kwargs) -> dict:
        out = {
            "X-DIGIKEY-Client-Id": self.__client_id,
            "X-DIGIKEY-Locale-Language": self.locale_lang.value,
            "X-DIGIKEY-Locale-Currency": self.locale_currency.value,
            "X-DIGIKEY-Locale-Site": self.locale_site.value,
        }
        if self.account_id:
            out["X-DIGIKEY-Account-Id"] = self.account_id

        out |= kwargs
        out = {k: v for k, v in out.items() if v is not None}
        for k, v in out.copy().items():
            if k.startswith("_no"):
                out.pop(v)
        out = {k: v for k, v in out.items() if not k.startswith("_no")}

        return out

    @property
    def _product_search(self):
        import pdb

        pdb.set_trace()
        return self._client("ProductSearch.json").ProductSearch

    # TODO: how to handle the weird keyword search schema???

    @swagger_call
    def product_details(
        self,
        productNumber: str,
        manufacturerId: str | None = None,
        includes: str | None = None,
    ):
        return self._product_search.ProductDetails

    @swagger_call
    def manufacturers(self):
        return self._product_search.Manufacturers

    @swagger_call
    def categories(
        self,
        _no1="X-DIGIKEY-Client-Id",
        _no2="X-DIGIKEY-Locale-Language",
        _no3="X-DIGIKEY-Locale-Currency",
        _no4="X-DIGIKEY-Locale-Site",
    ):
        return self._product_search.Categories

    @swagger_call
    def categories_by_id(
        self,
        categoryId: int,
        _no1="X-DIGIKEY-Client-Id",
        _no2="X-DIGIKEY-Locale-Language",
        _no3="X-DIGIKEY-Locale-Currency",
        _no4="X-DIGIKEY-Locale-Site",
    ):
        return self._product_search.CategoriesById

    @swagger_call
    def digireel_pricing(
        self,
        productNumber: str,
        requestedQuantity: int,
    ):
        return self._product_search.DigiReelPricing

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
