"""Shopify GraphQL tool — queries order and inventory data."""
import httpx
from langchain_core.tools import tool
from ..core.config import settings

SHOPIFY_GQL = f"https://{settings.shopify_shop_domain}/admin/api/2024-10/graphql.json"
HEADERS = {
    "X-Shopify-Access-Token": settings.shopify_access_token,
    "Content-Type": "application/json",
}

ORDER_QUERY = """
query GetOrder($id: ID!) {
  order(id: $id) {
    id
    name
    displayFulfillmentStatus
    displayFinancialStatus
    tags
    lineItems(first: 50) {
      edges {
        node {
          id
          title
          quantity
          variant {
            id
            inventoryQuantity
            sku
          }
        }
      }
    }
    fulfillments {
      status
      trackingInfo { number company url }
    }
  }
}
"""


@tool
async def get_order(order_gid: str) -> dict:
    """Fetch full order details from Shopify including line items and fulfillment status.

    Args:
        order_gid: Shopify global ID, e.g. gid://shopify/Order/12345
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            SHOPIFY_GQL,
            headers=HEADERS,
            json={"query": ORDER_QUERY, "variables": {"id": order_gid}},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            return {"error": data["errors"]}
        return data["data"]["order"]


@tool
async def check_inventory(variant_gid: str) -> dict:
    """Check current inventory level for a variant.

    Args:
        variant_gid: Shopify variant GID, e.g. gid://shopify/ProductVariant/99999
    """
    query = """
    query InventoryCheck($id: ID!) {
      productVariant(id: $id) {
        id
        sku
        inventoryQuantity
        inventoryItem {
          id
          tracked
        }
      }
    }
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            SHOPIFY_GQL,
            headers=HEADERS,
            json={"query": query, "variables": {"id": variant_gid}},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            return {"error": data["errors"]}
        return data["data"]["productVariant"]
