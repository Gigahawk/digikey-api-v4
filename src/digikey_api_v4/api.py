import time
import functools
import inspect
import warnings

import requests
from bravado.client import SwaggerClient
from bravado.requests_client import RequestsClient, Authenticator
from bravado.exception import (
    HTTPGatewayTimeout,
    HTTPBadGateway,
    HTTPInternalServerError,
)

from digikey_api_v4.constants import LocaleCurrency, LocaleLanguage, LocaleSite
from digikey_api_v4.utils import swagger_dict, swagger_client
from digikey_api_v4.models import KeywordRequest


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
                return swagger_func(**params).result()
            except (HTTPBadGateway, HTTPGatewayTimeout, HTTPInternalServerError) as err:
                # Handle random 504/502 errors
                print(f"Call {idx} to {swagger_func.operation} failed with {err}")
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

    def _swagger_dict(self, name: str) -> dict:
        data = swagger_dict(name)
        # TODO: do we actually need to change the host?
        data["host"] = self._api_host
        return data

    def _client(self, name: str) -> SwaggerClient:
        return swagger_client(
            _dict=self._swagger_dict(name),
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
        return self._client("ProductSearch.json").ProductSearch

    @swagger_call
    def keyword_search(
        self,
        includes: str | None = None,
        body: KeywordRequest = KeywordRequest(),
    ):
        return self._product_search.KeywordSearch

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

    @swagger_call
    def recommended_products(
        self,
        productNumber: str,
        limit: int = 1,
        searchOptionList: str | None = None,
        excludeMarketPlaceProducts: bool = True,
    ):
        return self._product_search.RecommendedProducts

    @swagger_call
    def substitutions(
        self,
        productNumber: str,
        includes: str | None = None,
    ):
        return self._product_search.Substitutions

    @swagger_call
    def associations(
        self,
        productNumber: str,
    ):
        return self._product_search.Associations

    @swagger_call
    def package_type_by_quantity(
        self,
        productNumber: str,
    ):
        warnings.warn(
            (
                "Deprecated - please use PricingByQuantity endpoint to receive "
                "pricing for all package types when you enter a product number "
                "and desired quantity"
            ),
            warnings.DeprecationWarning,
        )
        return self._product_search.PackageTypeByQuantity

    @swagger_call
    def media(
        self,
        productNumber: str,
    ):
        return self._product_search.Media

    @swagger_call
    def product_pricing(
        self,
        productNumber: str,
        limit: int = 5,
        offset: int = 0,
        inStock: bool = False,
        excludeMarketplace: bool = True,
        excludeTariff: bool = False,
    ):
        return self._product_search.ProductPricing

    @swagger_call
    def alternate_packaging(
        self,
        productNumber: str,
    ):
        return self._product_search.AlternatePackaging

    @swagger_call
    def pricing_options_by_quantity(
        self,
        productNumber: str,
        requestedQuantity: str,
        manufacturerId: str | None = None,
    ):
        return self._product_search.PricingOptionsByQuantity

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
