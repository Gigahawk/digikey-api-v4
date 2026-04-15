import json

from digikey_api_v4.api import DigikeyClient

import pytest


@pytest.fixture
def creds():
    with open("creds.json", "r") as f:
        return json.load(f)


@pytest.fixture
def client(creds):
    return DigikeyClient(
        client_id=creds["CLIENT_ID"],
        client_secret=creds["CLIENT_SECRET"],
        sandbox=creds["SANDBOX"],
    )
