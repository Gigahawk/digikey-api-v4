import pytest

from digikey_api_v4.models import KeywordRequest


def test_keyword_search(client):
    if client.sandbox:
        pytest.skip("ProductInformation API doesn't seem to work with sandbox keys")
    search_term = "RC0402JR"
    target = "311-0.0JRTR-ND"
    result = client.keyword_search(body=KeywordRequest(Keywords=search_term))
    products = result.Products
    for p in products:
        variations = p.ProductVariations
        for v in variations:
            pn = v.DigiKeyProductNumber
            if pn == target:
                return

    raise ValueError(
        f"Did not find DigiKey Part Number {target} from search {search_term}"
    )


def test_product_details(client):
    if client.sandbox:
        pytest.skip("ProductInformation API doesn't seem to work with sandbox keys")
    product_number = "311-0.0JRTR-ND"
    target = "RC0402JR-070RL"
    result = client.product_details(productNumber=product_number)
    assert result.Product.ManufacturerProductNumber == target


def test_manufacturers(client):
    if client.sandbox:
        pytest.skip("ProductInformation API doesn't seem to work with sandbox keys")
    target = "Adafruit Industries LLC"
    result = client.manufacturers()
    manufacturers = result.Manufacturers
    for m in manufacturers:
        if m.Name == target:
            return
    raise ValueError(f"Did not find manufacturer {target}")


def test_categories(client):
    if client.sandbox:
        pytest.skip("ProductInformation API doesn't seem to work with sandbox keys")
    target = "Resistors"
    target_id = 2
    result = client.categories()
    categories = result.Categories
    for c in categories:
        if c.Name == target and c.CategoryId == target_id:
            return
    raise ValueError(f"Did not find category {target} with ID {target_id}")


def test_media(client):
    if client.sandbox:
        pytest.skip("ProductInformation API doesn't seem to work with sandbox keys")
    product_number = "311-0.0JRTR-ND"
    target = "https://mm.digikey.com/Volume0/opasdata/d220001/medias/images/4849/13_0402-%281005-metric%29.jpg"
    result = client.media(productNumber=product_number)
    links = result.MediaLinks
    for ln in links:
        if ln.Url == target:
            return
    raise ValueError(f"Did not find media link '{target}' for product {product_number}")
