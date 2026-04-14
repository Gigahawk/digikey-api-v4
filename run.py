from time import sleep
from pprint import pprint
import json

from bravado.exception import HTTPGatewayTimeout, HTTPBadGateway

from digikey_api_v4.api import DigikeyClient

# creds.json should contain:
#
#
# {
#   "CLIENT_ID": "<your_client_id>",
#   "CLIENT_SECRET": "<your_client_secret>",
#   "SANDBOX": false
# }
#
# Note that product search (product details??) doesn't seem to work with sandbox creds

with open("creds.json", "r") as f:
    creds = json.load(f)

client = DigikeyClient(
    client_id=creds["CLIENT_ID"],
    client_secret=creds["CLIENT_SECRET"],
    sandbox=creds["SANDBOX"],
)


z = client.categories_by_id(233)
pprint(z.response().result)
