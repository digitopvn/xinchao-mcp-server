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

VERSION = "1.2.0"
BUILD_DATE = "2026-03-26"

mcp = FastMCP("XinChaoMCP", transport_security=TransportSecuritySettings(
    enable_dns_rebinding_protection=False
))


# --- Info ---

@mcp.tool()
async def server_info() -> dict[str, Any]:
    """Get XinChao MCP server version and status. Use this to verify the server is running the latest version."""
    from config import API_URL, AUTHOR_ID
    return {
        "version": VERSION,
        "build_date": BUILD_DATE,
        "api_url": API_URL,
        "author_id_configured": bool(AUTHOR_ID),
    }


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


# DELETE tools disabled for safety — uncomment when needed
# @mcp.tool()
# async def delete_shows(ids: str) -> dict[str, Any]:
#     """Delete shows by comma-separated IDs (e.g. '1,2,3')."""
#     return await api("DELETE", "/admin/show", data={"ids": [int(i.strip()) for i in ids.split(",")]})


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
    """Create a new post on XinChao platform.

    STEP-BY-STEP guide — ask user for each section:

    1. TITLE (required):
       - title_vn: Tiêu đề tiếng Việt
       - title_en: Title in English
       - titleNon_vn: Tiêu đề phụ VN (optional)
       - titleNon_en: Sub-title EN (optional)

    2. SLUG (auto-generated):
       - slug: Auto-generate from title_vn (lowercase, remove diacritics, replace spaces with hyphens)

    3. DESCRIPTION (required):
       - description_vn: Mô tả ngắn VN (hiện ở danh sách bài viết)
       - description_en: Short description EN

    4. CONTENT (required):
       - content_vn: Nội dung đầy đủ VN (HTML supported)
       - content_en: Full content EN (HTML supported)

    5. CATEGORY (required):
       - post_category_id: number — use list_post_categories to find ID

    6. IMAGES — ask user for each (không bắt buộc, bỏ qua nếu không cần):
       - image: Ảnh banner chính desktop (không bắt buộc)
       - imageMb: Ảnh banner mobile (không bắt buộc)
       - thumbImage: Thumbnail nhỏ desktop (không bắt buộc)
       - thumbImageMb: Thumbnail nhỏ mobile (không bắt buộc)
       - thumbMaster: Thumbnail lớn/master desktop (không bắt buộc)
       - thumbMasterMb: Thumbnail lớn/master mobile (không bắt buộc)
       - meta_image: Ảnh SEO/OG khi share link (không bắt buộc)
       For workspace files: pass path directly (e.g. /app/workspace/.../image.jpg)
       For external images: use upload_image tool with public URL first, then use returned path.

    7. SEO — ask user for each (không bắt buộc, bỏ qua nếu không cần):
       - meta_title: Tiêu đề SEO (không bắt buộc)
       - meta_keyword: Từ khóa SEO, comma-separated (không bắt buộc)
       - meta_description: Mô tả SEO (không bắt buộc)

    8. OTHER — ask user for each (không bắt buộc, bỏ qua nếu không cần):
       - publishedAt: Ngày xuất bản, ISO date e.g. "2026-03-26" (không bắt buộc)
       - order_no: Thứ tự hiển thị, number (không bắt buộc)
       - feature: Bài nổi bật, true/false (không bắt buộc)
       - tags: Tags/nhãn, array (không bắt buộc)

    IMPORTANT: Ask user about ALL sections above step by step. For optional fields, note "(không bắt buộc, bỏ qua nếu không cần)" so user knows they can skip.

    RULES:
    - status: only 'DRAFT' or 'PUBLISHED' (uppercase). Defaults to 'DRAFT'. Only set 'PUBLISHED' when user explicitly asks to publish.
    - slug: auto-generated from title_vn if not provided. Do NOT ask user for slug.
    - author_id: auto-injected from AUTHOR_ID env if not provided. Do NOT ask user for author_id.
    - image fields: accept workspace file paths (e.g. /app/workspace/...) OR public URLs. For workspace files, pass the path directly — no upload needed.
    - Do NOT ask user for fields that are auto-generated or have defaults."""
    import json
    import re
    import unicodedata
    from config import AUTHOR_ID
    post_data = json.loads(data)
    # Auto-generate slug from title_vn if not provided
    if "slug" not in post_data and "title_vn" in post_data:
        text = unicodedata.normalize("NFD", post_data["title_vn"])
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")
        text = re.sub(r"[đĐ]", "d", text)
        text = re.sub(r"[^a-zA-Z0-9\s-]", "", text.lower())
        post_data["slug"] = re.sub(r"[\s]+", "-", text.strip())
    if "status" not in post_data:
        post_data["status"] = "DRAFT"
    if AUTHOR_ID and "author_id" not in post_data:
        post_data["author_id"] = int(AUTHOR_ID)
    return await api("POST", "/admin/post", data=post_data)


@mcp.tool()
async def update_post(post_id: str, data: str) -> dict[str, Any]:
    """Update a post by ID. Pass data as JSON string with fields to update."""
    import json
    return await api("PUT", f"/admin/post/{post_id}", data=json.loads(data))


# @mcp.tool()
# async def delete_posts(ids: str) -> dict[str, Any]:
#     """Delete posts by comma-separated IDs (e.g. '1,2,3')."""
#     return await api("DELETE", "/admin/post", data={"ids": [int(i.strip()) for i in ids.split(",")]})


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


# --- Upload ---

@mcp.tool()
async def upload_image(image_url: str) -> dict[str, Any]:
    """Upload an image to XinChao platform by providing a public URL. Returns the uploaded image path to use in create_post/update_post image field.
    The server downloads the image from the URL and uploads it to XinChao."""
    import httpx
    from config import API_URL, AUTHOR_ID
    token = await _get_token_for_upload()
    # Download image from URL
    async with httpx.AsyncClient(timeout=30) as client:
        img_resp = await client.get(image_url)
        if img_resp.status_code >= 400:
            return {"error": f"Cannot download image from {image_url}", "status": img_resp.status_code}
        content_type = img_resp.headers.get("content-type", "image/jpeg")
        ext = content_type.split("/")[-1].split(";")[0]
        filename = f"upload.{ext}"
        # Upload to XinChao
        upload_resp = await client.post(
            f"{API_URL}/admin/filemanagers/single",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (filename, img_resp.content, content_type)},
        )
        if upload_resp.status_code >= 400:
            return {"error": upload_resp.status_code, "message": upload_resp.text[:500]}
        return upload_resp.json()


@mcp.tool()
async def update_post_images(post_id: str, image_url: str, field: str = "image") -> dict[str, Any]:
    """Upload an image and attach it to a post via multipart form update.
    API uploads to Cloudflare R2 automatically.
    Args:
        post_id: Post ID to update
        image_url: Public URL of the image to download and attach
        field: Image field name (image, imageMb, thumbImage, thumbImageMb, thumbMaster, thumbMasterMb, meta_image)
    Returns updated post data."""
    import httpx
    from config import API_URL
    token = await _get_token_for_upload()
    async with httpx.AsyncClient(timeout=60) as client:
        # Download image from URL
        img_resp = await client.get(image_url)
        if img_resp.status_code >= 400:
            return {"error": f"Cannot download image from {image_url}", "status": img_resp.status_code}
        content_type = img_resp.headers.get("content-type", "image/jpeg")
        ext = content_type.split("/")[-1].split(";")[0]
        if ext == "jpeg": ext = "jpg"
        filename = f"{field}.{ext}"
        # Update post with multipart file upload — hasFile middleware handles R2 upload
        upload_resp = await client.put(
            f"{API_URL}/admin/post/{post_id}",
            headers={"Authorization": f"Bearer {token}"},
            files={field: (filename, img_resp.content, content_type)},
        )
        if upload_resp.status_code >= 400:
            return {"error": upload_resp.status_code, "message": upload_resp.text[:500]}
        return upload_resp.json()


async def _get_token_for_upload():
    """Get token for upload — reuse from xinchao_api module."""
    from xinchao_api import _get_token
    return await _get_token()


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
