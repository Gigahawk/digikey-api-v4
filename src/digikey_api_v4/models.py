from digikey_api_v4.utils import swagger_client

KeywordRequest = swagger_client("ProductSearch.json").get_model("KeywordRequest")
