"""XinChao.world MCP Server — admin API tools for GoClaw agents."""

import os
import sys
import logging
from typing import Any
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import TransportSecuritySettings
from xinchao_api import api
from config import PORT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("xinchao-mcp")

mcp = FastMCP("XinChaoMCP", transport_security=TransportSecuritySettings(
    enable_dns_rebinding_protection=False
))


# --- Shows ---

@mcp.tool()
async def list_shows(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all shows from XinChao platform with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword:
        params["keyword"] = keyword
    return await api("GET", "/admin/show", params=params)


@mcp.tool()
async def get_show(show_id: str) -> dict[str, Any]:
    """Get details of a specific show by ID."""
    return await api("GET", f"/admin/show/{show_id}")


@mcp.tool()
async def create_show(data: str) -> dict[str, Any]:
    """Create a new show. Pass data as JSON with fields:
    Required: title_vn, title_en, slug, categoryId (number), sortOrder (number), status (number), showDay, currency.
    Optional: image, shortDescription_vn, shortDescription_en, detailContent_vn, detailContent_en, location, priceRange, stageId, isFree, isShowHome, metaTitle, metaDescription."""
    import json
    return await api("POST", "/admin/show", data=json.loads(data))


@mcp.tool()
async def update_show(show_id: str, data: str) -> dict[str, Any]:
    """Update an existing show. Pass data as JSON string with fields to update."""
    import json
    return await api("PUT", f"/admin/show/{show_id}", data=json.loads(data))


@mcp.tool()
async def delete_shows(ids: str) -> dict[str, Any]:
    """Delete shows by comma-separated IDs (e.g. '1,2,3')."""
    return await api("DELETE", "/admin/show", data={"ids": [int(i.strip()) for i in ids.split(",")]})


# --- Tickets ---

@mcp.tool()
async def list_tickets(page: str = "1", limit: str = "10", keyword: str = "", show_id: str = "") -> dict[str, Any]:
    """List all tickets with pagination. Filter by show_id if provided."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    if show_id: params["showId"] = show_id
    return await api("GET", "/admin/ticket", params=params)


@mcp.tool()
async def get_ticket(ticket_id: str) -> dict[str, Any]:
    """Get details of a specific ticket by ID."""
    return await api("GET", f"/admin/ticket/{ticket_id}")


@mcp.tool()
async def create_ticket(data: str) -> dict[str, Any]:
    """Create a new ticket. Pass data as JSON with fields:
    Required: name, type, price, showId (number), active ('true'/'false').
    Optional: sortOrder, color, description_vn, description_en, image, salePrices."""
    import json
    return await api("POST", "/admin/ticket", data=json.loads(data))


@mcp.tool()
async def update_ticket(ticket_id: str, data: str) -> dict[str, Any]:
    """Update a ticket by ID. Pass data as JSON string with fields to update."""
    import json
    return await api("PUT", f"/admin/ticket/{ticket_id}", data=json.loads(data))


# --- Orders ---

@mcp.tool()
async def list_orders(page: str = "1", limit: str = "10", keyword: str = "", status: str = "", show_id: str = "") -> dict[str, Any]:
    """List all orders with pagination. Filter by status or show_id."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    if status: params["status"] = status
    if show_id: params["showId"] = show_id
    return await api("GET", "/admin/order", params=params)


@mcp.tool()
async def get_order(order_id: str) -> dict[str, Any]:
    """Get details of a specific order by ID."""
    return await api("GET", f"/admin/order/{order_id}")


@mcp.tool()
async def change_order_status(order_id: str, data: str) -> dict[str, Any]:
    """Change order status (e.g. confirmed, cancelled). Pass data as JSON: {status: '...'}"""
    import json
    return await api("PUT", f"/admin/order/status/{order_id}", data=json.loads(data))


@mcp.tool()
async def checkin_order(data: str) -> dict[str, Any]:
    """Check in an order at the event venue. Pass data as JSON string."""
    import json
    return await api("POST", "/admin/order/checkin", data=json.loads(data))


# --- Posts ---

@mcp.tool()
async def list_posts(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all news/blog posts with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/post", params=params)


@mcp.tool()
async def get_post(post_id: str) -> dict[str, Any]:
    """Get details of a specific post by ID."""
    return await api("GET", f"/admin/post/{post_id}")


@mcp.tool()
async def create_post(data: str) -> dict[str, Any]:
    """Create a new post. Pass data as JSON with snake_case fields:
    Required: title_vn, title_en, slug, description_vn, description_en, content_vn, content_en, status (string), post_category_id (number), author_id (number).
    Optional: image, publishedAt, order_no, tags, meta_title, meta_description.
    author_id is auto-injected from AUTHOR_ID env if not provided."""
    import json
    from config import AUTHOR_ID
    post_data = json.loads(data)
    if AUTHOR_ID and "author_id" not in post_data:
        post_data["author_id"] = int(AUTHOR_ID)
    return await api("POST", "/admin/post", data=post_data)


@mcp.tool()
async def update_post(post_id: str, data: str) -> dict[str, Any]:
    """Update a post by ID. Pass data as JSON string with fields to update."""
    import json
    return await api("PUT", f"/admin/post/{post_id}", data=json.loads(data))


@mcp.tool()
async def delete_posts(ids: str) -> dict[str, Any]:
    """Delete posts by comma-separated IDs (e.g. '1,2,3')."""
    return await api("DELETE", "/admin/post", data={"ids": [int(i.strip()) for i in ids.split(",")]})


@mcp.tool()
async def list_post_categories(page: str = "1", limit: str = "10") -> dict[str, Any]:
    """List all post/news categories."""
    return await api("GET", "/admin/post-category", params={"page": page, "limit": limit})


# --- Pages ---

@mcp.tool()
async def list_pages(page: str = "1", limit: str = "10") -> dict[str, Any]:
    """List all static pages (About, Terms, FAQ, etc.)."""
    return await api("GET", "/admin/pages", params={"page": page, "limit": limit})


@mcp.tool()
async def get_page(code: str) -> dict[str, Any]:
    """Get a static page by code (e.g. 'about', 'terms', 'faq', 'privacy')."""
    return await api("GET", f"/admin/pages/{code}")


@mcp.tool()
async def update_page(page_id: str, data: str) -> dict[str, Any]:
    """Update a static page by ID. Pass data as JSON: {title, content, metaTitle, ...}"""
    import json
    return await api("PUT", f"/admin/pages/{page_id}", data=json.loads(data))


# --- Customers & Artists ---

@mcp.tool()
async def list_customers(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all customers with pagination and search by name/email/phone."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/customer", params=params)


@mcp.tool()
async def list_artists(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all artists with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/artist", params=params)


# --- Entry point ---

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    port = int(os.environ.get("PORT", PORT))

    if mode in ("sse", "streamable-http"):
        import uvicorn

        if mode == "sse":
            app = mcp.sse_app()
        else:
            app = mcp.streamable_http_app()

        # Health check endpoint
        from starlette.requests import Request as StarletteRequest
        from starlette.responses import JSONResponse
        from config import ADMIN_EMAIL, ADMIN_PASSWORD

        async def health(request: StarletteRequest):
            return JSONResponse({
                "status": "ok",
                "api_url": os.getenv("XINCHAO_API_URL", ""),
                "email_configured": bool(ADMIN_EMAIL),
                "password_configured": bool(ADMIN_PASSWORD),
            })

        app.add_route("/health", health)

        logger.info("Starting XinChaoMCP (%s) on port %s", mode, port)
        uvicorn.run(app, host="0.0.0.0", port=port,
                    log_level="info",
                    timeout_keep_alive=120,
                    timeout_graceful_shutdown=30,
                    h11_max_incomplete_event_size=256 * 1024)
    else:
        mcp.run(transport="stdio")
