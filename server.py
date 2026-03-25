"""XinChao.world MCP Server — admin API tools for GoClaw agents."""

import sys
from typing import Any
from mcp.server.fastmcp import FastMCP
from xinchao_api import api
from config import PORT

mcp = FastMCP("XinChaoMCP")


# --- Shows ---

@mcp.tool()
def list_shows(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all shows from XinChao platform with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword:
        params["keyword"] = keyword
    return api("GET", "/admin/show", params=params)


@mcp.tool()
def get_show(show_id: str) -> dict[str, Any]:
    """Get details of a specific show by ID."""
    return api("GET", f"/admin/show/{show_id}")


@mcp.tool()
def create_show(name: str, slug: str = "", show_day: str = "", description: str = "", status: str = "") -> dict[str, Any]:
    """Create a new show on XinChao platform."""
    data = {"name": name}
    if slug: data["slug"] = slug
    if show_day: data["showDay"] = show_day
    if description: data["description"] = description
    if status: data["status"] = status
    return api("POST", "/admin/show", data=data)


@mcp.tool()
def update_show(show_id: str, data: str) -> dict[str, Any]:
    """Update an existing show. Pass data as JSON string with fields to update."""
    import json
    return api("PUT", f"/admin/show/{show_id}", data=json.loads(data))


@mcp.tool()
def delete_shows(ids: str) -> dict[str, Any]:
    """Delete shows by comma-separated IDs (e.g. '1,2,3')."""
    return api("DELETE", "/admin/show", data={"ids": [int(i.strip()) for i in ids.split(",")]})


# --- Tickets ---

@mcp.tool()
def list_tickets(page: str = "1", limit: str = "10", keyword: str = "", show_id: str = "") -> dict[str, Any]:
    """List all tickets with pagination. Filter by show_id if provided."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    if show_id: params["showId"] = show_id
    return api("GET", "/admin/ticket", params=params)


@mcp.tool()
def get_ticket(ticket_id: str) -> dict[str, Any]:
    """Get details of a specific ticket by ID."""
    return api("GET", f"/admin/ticket/{ticket_id}")


@mcp.tool()
def create_ticket(data: str) -> dict[str, Any]:
    """Create a new ticket. Pass data as JSON string: {name, price, showId, quantity, ...}"""
    import json
    return api("POST", "/admin/ticket", data=json.loads(data))


@mcp.tool()
def update_ticket(ticket_id: str, data: str) -> dict[str, Any]:
    """Update a ticket by ID. Pass data as JSON string with fields to update."""
    import json
    return api("PUT", f"/admin/ticket/{ticket_id}", data=json.loads(data))


# --- Orders ---

@mcp.tool()
def list_orders(page: str = "1", limit: str = "10", keyword: str = "", status: str = "", show_id: str = "") -> dict[str, Any]:
    """List all orders with pagination. Filter by status or show_id."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    if status: params["status"] = status
    if show_id: params["showId"] = show_id
    return api("GET", "/admin/order", params=params)


@mcp.tool()
def get_order(order_id: str) -> dict[str, Any]:
    """Get details of a specific order by ID."""
    return api("GET", f"/admin/order/{order_id}")


@mcp.tool()
def change_order_status(order_id: str, data: str) -> dict[str, Any]:
    """Change order status (e.g. confirmed, cancelled). Pass data as JSON: {status: '...'}"""
    import json
    return api("PUT", f"/admin/order/status/{order_id}", data=json.loads(data))


@mcp.tool()
def checkin_order(data: str) -> dict[str, Any]:
    """Check in an order at the event venue. Pass data as JSON string."""
    import json
    return api("POST", "/admin/order/checkin", data=json.loads(data))


# --- Posts ---

@mcp.tool()
def list_posts(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all news/blog posts with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return api("GET", "/admin/post", params=params)


@mcp.tool()
def get_post(post_id: str) -> dict[str, Any]:
    """Get details of a specific post by ID."""
    return api("GET", f"/admin/post/{post_id}")


@mcp.tool()
def create_post(data: str) -> dict[str, Any]:
    """Create a new post. Pass data as JSON: {title, slug, content, postCategoryId, ...}"""
    import json
    return api("POST", "/admin/post", data=json.loads(data))


@mcp.tool()
def update_post(post_id: str, data: str) -> dict[str, Any]:
    """Update a post by ID. Pass data as JSON string with fields to update."""
    import json
    return api("PUT", f"/admin/post/{post_id}", data=json.loads(data))


@mcp.tool()
def delete_posts(ids: str) -> dict[str, Any]:
    """Delete posts by comma-separated IDs (e.g. '1,2,3')."""
    return api("DELETE", "/admin/post", data={"ids": [int(i.strip()) for i in ids.split(",")]})


@mcp.tool()
def list_post_categories(page: str = "1", limit: str = "10") -> dict[str, Any]:
    """List all post/news categories."""
    return api("GET", "/admin/post-category", params={"page": page, "limit": limit})


# --- Pages ---

@mcp.tool()
def list_pages(page: str = "1", limit: str = "10") -> dict[str, Any]:
    """List all static pages (About, Terms, FAQ, etc.)."""
    return api("GET", "/admin/pages", params={"page": page, "limit": limit})


@mcp.tool()
def get_page(code: str) -> dict[str, Any]:
    """Get a static page by code (e.g. 'about', 'terms', 'faq', 'privacy')."""
    return api("GET", f"/admin/pages/{code}")


@mcp.tool()
def update_page(page_id: str, data: str) -> dict[str, Any]:
    """Update a static page by ID. Pass data as JSON: {title, content, metaTitle, ...}"""
    import json
    return api("PUT", f"/admin/pages/{page_id}", data=json.loads(data))


# --- Customers & Artists ---

@mcp.tool()
def list_customers(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all customers with pagination and search by name/email/phone."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return api("GET", "/admin/customer", params=params)


@mcp.tool()
def list_artists(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all artists with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return api("GET", "/admin/artist", params=params)


# --- Entry point ---

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    if mode == "sse":
        import uvicorn
        from starlette.middleware import Middleware
        from starlette.middleware.trustedhost import TrustedHostMiddleware
        app = mcp.sse_app()
        # Allow all hosts for Render proxy
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
        uvicorn.run(app, host="0.0.0.0", port=PORT)
    else:
        mcp.run(transport="stdio")
