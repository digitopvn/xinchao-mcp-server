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

VERSION = "1.3.0"
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

    6. PUBLISHED DATE (required):
       - publishedAt: Ngày xuất bản, format dd/mm/yyyy (e.g. "26/03/2026"). Server auto-converts to ISO date.

    7. IMAGES — ask user for each (không bắt buộc, bỏ qua nếu không cần):
       - image: Ảnh banner chính desktop (không bắt buộc)
       - imageMb: Ảnh banner mobile (không bắt buộc)
       - thumbImage: Thumbnail nhỏ desktop (không bắt buộc)
       - thumbImageMb: Thumbnail nhỏ mobile (không bắt buộc)
       - thumbMaster: Thumbnail lớn/master desktop (không bắt buộc)
       - thumbMasterMb: Thumbnail lớn/master mobile (không bắt buộc)
       - meta_image: Ảnh SEO/OG khi share link (không bắt buộc)
       For workspace files: pass path directly (e.g. /app/workspace/.../image.jpg)
       For external images: use upload_image tool with public URL first, then use returned path.

    8. SEO — ask user for each (không bắt buộc, bỏ qua nếu không cần):
       - meta_title: Tiêu đề SEO (không bắt buộc)
       - meta_keyword: Từ khóa SEO, comma-separated (không bắt buộc)
       - meta_description: Mô tả SEO (không bắt buộc)

    9. OTHER — ask user for each (không bắt buộc, bỏ qua nếu không cần):
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
    # Convert dd/mm/yyyy to ISO date for publishedAt
    if "publishedAt" in post_data and "/" in str(post_data["publishedAt"]):
        parts = post_data["publishedAt"].split("/")
        if len(parts) == 3:
            post_data["publishedAt"] = f"{parts[2]}-{parts[1]}-{parts[0]}"
    if "status" not in post_data:
        post_data["status"] = "DRAFT"
    if AUTHOR_ID and "author_id" not in post_data:
        post_data["author_id"] = int(AUTHOR_ID)
    # Auto-upload external URLs in image fields to CDN
    post_data = await _auto_upload_image_fields(post_data)
    return await api("POST", "/admin/post", data=post_data)


@mcp.tool()
async def update_post(post_id: str, data: str) -> dict[str, Any]:
    """Update a post by ID. Pass data as JSON string with fields to update.
    External URLs in image fields are auto-uploaded to CDN before updating."""
    import json
    post_data = json.loads(data)
    # Auto-upload external URLs in image fields to CDN
    post_data = await _auto_upload_image_fields(post_data)
    return await api("PUT", f"/admin/post/{post_id}", data=post_data)


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


# --- Upload helpers ---

_IMAGE_FIELDS = {"image", "imageMb", "thumbImage", "thumbImageMb", "thumbMaster", "thumbMasterMb", "meta_image"}

_VALID_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml", "image/bmp", "image/tiff"}


def _is_external_url(value: str) -> bool:
    """Check if value is an external URL (not a workspace/CDN relative path)."""
    if not isinstance(value, str):
        return False
    return value.startswith("http://") or value.startswith("https://")


async def _get_token_for_upload():
    """Get valid token, auto re-login if expired."""
    from xinchao_api import _get_token
    return await _get_token()


async def _download_image(url: str) -> dict[str, Any]:
    """Download image from URL with validation and redirect support.
    Returns {content, content_type, ext, filename} or {error}."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                return {"error": f"Cannot download image from {url} (status={resp.status_code})"}
            content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
            if content_type not in _VALID_IMAGE_TYPES:
                return {"error": f"URL returned non-image content-type: {content_type} (expected image/*). URL may be behind auth or redirect."}
            if len(resp.content) < 100:
                return {"error": f"Downloaded content too small ({len(resp.content)} bytes), likely not a valid image"}
            ext = content_type.split("/")[-1]
            if ext == "jpeg":
                ext = "jpg"
            elif ext == "svg+xml":
                ext = "svg"
            return {"content": resp.content, "content_type": content_type, "ext": ext}
    except httpx.TimeoutException:
        return {"error": f"Timeout downloading image from {url}"}
    except httpx.HTTPError as e:
        return {"error": f"HTTP error downloading image from {url}: {e}"}


async def _upload_to_cdn(image_bytes: bytes, content_type: str, ext: str, filename_prefix: str = "upload") -> dict[str, Any]:
    """Upload image bytes to XinChao CDN via /admin/filemanagers/single.
    Returns API response with uploaded path, or {error}."""
    import httpx
    from config import API_URL
    filename = f"{filename_prefix}.{ext}"
    for attempt in range(2):
        token = await _get_token_for_upload()
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{API_URL}/admin/filemanagers/single",
                    headers={"Authorization": f"Bearer {token}"},
                    files={"file": (filename, image_bytes, content_type)},
                )
            if resp.status_code == 401 and attempt == 0:
                from xinchao_api import _token_cache
                _token_cache["token"] = None
                logger.info("Upload got 401, re-login and retry...")
                continue
            if resp.status_code >= 400:
                return {"error": f"CDN upload failed (status={resp.status_code}): {resp.text[:500]}"}
            return resp.json()
        except httpx.TimeoutException:
            return {"error": "Timeout uploading to CDN"}
        except httpx.HTTPError as e:
            return {"error": f"HTTP error uploading to CDN: {e}"}
    return {"error": "Upload failed after retries"}


async def _auto_upload_image_fields(data: dict) -> dict:
    """For any image field containing an external URL, download and upload to CDN,
    then replace the URL with the CDN path. Returns updated data dict."""
    for field in _IMAGE_FIELDS:
        value = data.get(field)
        if not _is_external_url(value):
            continue
        logger.info("Auto-uploading %s from external URL: %s", field, value)
        dl = await _download_image(value)
        if "error" in dl:
            logger.warning("Failed to download %s for field %s: %s", value, field, dl["error"])
            continue
        result = await _upload_to_cdn(dl["content"], dl["content_type"], dl["ext"], filename_prefix=field)
        if "error" in result:
            logger.warning("Failed to upload %s to CDN: %s", field, result["error"])
            continue
        # Extract CDN path from response
        cdn_path = result.get("data", {}).get("filePath") or result.get("data", {}).get("path") or result.get("filePath") or result.get("path")
        if cdn_path:
            logger.info("Uploaded %s -> %s", field, cdn_path)
            data[field] = cdn_path
        else:
            logger.warning("Upload succeeded but no path in response for %s: %s", field, result)
    return data


# --- Upload tools ---

@mcp.tool()
async def upload_image(image_url: str) -> dict[str, Any]:
    """Upload an image to XinChao CDN by providing a public URL.
    Returns the uploaded image path (e.g. /uploads/xxx.jpg) to use in create_post/update_post image fields.
    The server downloads the image from the URL, validates it, and uploads to CDN."""
    dl = await _download_image(image_url)
    if "error" in dl:
        return dl
    return await _upload_to_cdn(dl["content"], dl["content_type"], dl["ext"])


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
    dl = await _download_image(image_url)
    if "error" in dl:
        return dl
    filename = f"{field}.{dl['ext']}"
    for attempt in range(2):
        token = await _get_token_for_upload()
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.put(
                    f"{API_URL}/admin/post/{post_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    files={field: (filename, dl["content"], dl["content_type"])},
                )
            if resp.status_code == 401 and attempt == 0:
                from xinchao_api import _token_cache
                _token_cache["token"] = None
                logger.info("update_post_images got 401, re-login and retry...")
                continue
            if resp.status_code >= 400:
                return {"error": resp.status_code, "message": resp.text[:500]}
            return resp.json()
        except httpx.TimeoutException:
            return {"error": "Timeout uploading to post"}
        except httpx.HTTPError as e:
            return {"error": f"HTTP error: {e}"}
    return {"error": "Upload failed after retries"}


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
