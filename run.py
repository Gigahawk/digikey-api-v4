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

ps = client.product_search


print(ps)


# Seems to randomly 504/502?
while True:
    try:
        # TODO: shouldn't need to provide client id here
        z = ps.ProductSearch.ProductDetails(
            productNumber="311-0.0JRCT-ND",
            **{"X-DIGIKEY-Client-Id": creds["CLIENT_ID"]},
        )
        pprint(z.response().result)
        break
    except (HTTPGatewayTimeout, HTTPBadGateway):
        print("Gateway timeout")
        sleep(1)
