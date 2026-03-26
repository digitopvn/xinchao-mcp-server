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

VERSION = "2.0.0"
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
       IMAGE UPLOAD: External URLs (https://...) are AUTO-UPLOADED to XinChao CDN.
       Just pass the URL directly in image fields — the server handles download + upload to CDN automatically.
       DO NOT pass raw external URLs expecting them to work as-is. They WILL be re-uploaded to CDN.
       Result: image field will contain CDN path like /uploads/xxx.jpg (NOT the original external URL).

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
    - image fields: accept public URLs (https://...) — they are AUTO-UPLOADED to CDN, no manual upload_image call needed.
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
    """Update a post by ID. Pass data as JSON string with ONLY the fields you want to change.
    Unspecified fields are preserved (fetched from existing post before updating).
    External URLs in image fields are auto-uploaded to CDN before updating."""
    import json
    new_data = json.loads(data)
    # Auto-upload external URLs in image fields to CDN
    new_data = await _auto_upload_image_fields(new_data)

    # Fetch existing post to preserve fields not being updated
    existing = await api("GET", f"/admin/post/{post_id}")
    existing_data = {}
    if isinstance(existing, dict):
        existing_data = existing.get("metadata") or existing.get("data") or existing
        # If response is wrapped in another layer
        if isinstance(existing_data, dict) and "metadata" in existing_data:
            existing_data = existing_data["metadata"]

    # Remove non-updatable / meta fields from existing data
    _SKIP_KEYS = {"_id", "id", "createdAt", "updatedAt", "__v", "slug", "post_category"}
    merged = {k: v for k, v in existing_data.items() if k not in _SKIP_KEYS}
    # Overlay new fields on top of existing
    merged.update(new_data)

    logger.info("update_post #%s: merging %d existing + %d new fields", post_id, len(existing_data), len(new_data))
    return await api("PUT", f"/admin/post/{post_id}", data=merged)


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
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) XinChaoMCP/1.3.0"}
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
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
    """Upload image to XinChao CDN via /admin/filemanagers/single (same as web admin CKEditor).
    POST multipart/form-data with field name 'upload'.
    Returns {data: {url: "..."}} or {error}."""
    import httpx
    from config import API_URL

    for attempt in range(2):
        token = await _get_token_for_upload()
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                filename = f"{filename_prefix}.{ext}"
                # Field name must be 'upload' — same as CKEditor SimpleUploadAdapter in CMS frontend
                files = {"upload": (filename, image_bytes, content_type)}

                resp = await client.post(
                    f"{API_URL}/admin/filemanagers/single",
                    files=files,
                    headers={"Authorization": f"Bearer {token}"},
                )
                logger.info("CDN upload response: status=%s, body=%s", resp.status_code, resp.text[:500])

                if resp.status_code == 401 and attempt == 0:
                    from xinchao_api import _token_cache
                    _token_cache["token"] = None
                    logger.info("Upload got 401, re-login and retry...")
                    continue
                if resp.status_code >= 400:
                    return {"error": f"Upload failed (status={resp.status_code}): {resp.text[:500]}"}

                resp_data = resp.json()
                return {"data": resp_data}

        except httpx.TimeoutException:
            return {"error": "Timeout during CDN upload"}
        except httpx.HTTPError as e:
            return {"error": f"HTTP error during CDN upload: {e}"}
    return {"error": "Upload failed after retries"}


def _extract_cdn_path(result: dict) -> str | None:
    """Extract CDN path from /admin/filemanagers/single response.
    CKEditor SimpleUploadAdapter expects {url: "..."} or {urls: {default: "..."}}.
    Backend may also wrap in {metadata: {...}} or {data: {...}}."""
    # Check common response keys at all nesting levels
    search_keys = ("url", "filePath", "path", "file_key", "key", "file", "src", "fileUrl", "file_path", "file_url")

    # Try nested: data.X, metadata.X
    for wrapper in ("data", "metadata"):
        d = result.get(wrapper)
        if isinstance(d, dict):
            for key in search_keys:
                val = d.get(key)
                if val and isinstance(val, str):
                    return val
            # CKEditor format: {urls: {default: "..."}}
            urls = d.get("urls")
            if isinstance(urls, dict) and urls.get("default"):
                return urls["default"]

    # Try flat
    for key in search_keys:
        val = result.get(key)
        if val and isinstance(val, str):
            return val
    # CKEditor format at top level
    urls = result.get("urls")
    if isinstance(urls, dict) and urls.get("default"):
        return urls["default"]
    return None


async def _auto_upload_image_fields(data: dict) -> dict:
    """For any image field containing an external URL, download and upload to CDN,
    then replace the URL with the CDN path. Returns updated data dict.
    CRITICAL: If upload fails, REMOVE the external URL to prevent broken CDN links."""
    for field in _IMAGE_FIELDS:
        value = data.get(field)
        if not _is_external_url(value):
            continue
        logger.info("Auto-uploading %s from external URL: %s", field, value)
        dl = await _download_image(value)
        if "error" in dl:
            logger.warning("Failed to download %s for field %s: %s — REMOVING field to prevent broken URL", value, field, dl["error"])
            del data[field]  # REMOVE to prevent https://cdn.gotest.apphttps://... broken URL
            continue
        result = await _upload_to_cdn(dl["content"], dl["content_type"], dl["ext"], filename_prefix=field)
        if "error" in result:
            logger.warning("Failed to upload %s to CDN: %s — REMOVING field to prevent broken URL", field, result["error"])
            del data[field]  # REMOVE to prevent broken URL
            continue
        # Extract CDN path from response — try all known key patterns
        logger.info("CDN upload response for %s: %s", field, result)
        cdn_path = _extract_cdn_path(result)
        if cdn_path:
            logger.info("Uploaded %s -> %s", field, cdn_path)
            data[field] = cdn_path
        else:
            logger.error("Upload succeeded but CANNOT find path in response for %s: %s — REMOVING field", field, result)
            del data[field]  # REMOVE to prevent broken URL
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
    """Upload an image to CDN, then update the post's image field.
    Preserves all existing post data (only the specified image field is changed).
    Args:
        post_id: Post ID to update
        image_url: Public URL of the image to download and upload to CDN
        field: Image field name (image, imageMb, thumbImage, thumbImageMb, thumbMaster, thumbMasterMb, meta_image)
    Returns updated post data."""
    # Step 1: Download image
    dl = await _download_image(image_url)
    if "error" in dl:
        return dl
    # Step 2: Upload to CDN
    result = await _upload_to_cdn(dl["content"], dl["content_type"], dl["ext"], filename_prefix=field)
    if "error" in result:
        return result
    cdn_path = _extract_cdn_path(result)
    if not cdn_path:
        return {"error": f"Upload succeeded but no path in response: {result}"}
    # Step 3: Update post with CDN path — use update_post to preserve existing data
    import json
    logger.info("Updating post %s field %s -> %s", post_id, field, cdn_path)
    return await update_post(post_id, json.dumps({field: cdn_path}))


# --- Customers ---

@mcp.tool()
async def list_customers(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all customers with pagination and search by name/email/phone."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/customer", params=params)


@mcp.tool()
async def get_customer(customer_id: str) -> dict[str, Any]:
    """Get details of a specific customer by ID."""
    return await api("GET", f"/admin/customer/{customer_id}")


@mcp.tool()
async def create_customer(data: str) -> dict[str, Any]:
    """Create a new customer. Pass data as JSON: {name, email, phone, address, ...}"""
    import json
    return await api("POST", "/admin/customer", data=json.loads(data))


@mcp.tool()
async def update_customer(customer_id: str, data: str) -> dict[str, Any]:
    """Update a customer by ID. Pass data as JSON with fields to update."""
    import json
    return await api("PUT", f"/admin/customer/{customer_id}", data=json.loads(data))


# --- Artists ---

@mcp.tool()
async def list_artists(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all artists with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/artist", params=params)


@mcp.tool()
async def get_artist(artist_id: str) -> dict[str, Any]:
    """Get details of a specific artist by ID."""
    return await api("GET", f"/admin/artist/{artist_id}")


@mcp.tool()
async def create_artist(data: str) -> dict[str, Any]:
    """Create a new artist. Pass data as JSON: {name, description, image, ...}"""
    import json
    return await api("POST", "/admin/artist", data=json.loads(data))


@mcp.tool()
async def update_artist(artist_id: str, data: str) -> dict[str, Any]:
    """Update an artist by ID. Pass data as JSON with fields to update."""
    import json
    return await api("PUT", f"/admin/artist/{artist_id}", data=json.loads(data))


# --- Tags ---

@mcp.tool()
async def list_tags(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all tags with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/tag", params=params)


@mcp.tool()
async def get_tag(tag_id: str) -> dict[str, Any]:
    """Get details of a specific tag by ID."""
    return await api("GET", f"/admin/tag/{tag_id}")


@mcp.tool()
async def create_tag(data: str) -> dict[str, Any]:
    """Create a new tag. Pass data as JSON: {name, slug, ...}"""
    import json
    return await api("POST", "/admin/tag", data=json.loads(data))


@mcp.tool()
async def update_tag(tag_id: str, data: str) -> dict[str, Any]:
    """Update a tag by ID. Pass data as JSON with fields to update."""
    import json
    return await api("PUT", f"/admin/tag/{tag_id}", data=json.loads(data))


# --- Categories (Product/General) ---

@mcp.tool()
async def list_categories(page: str = "1", limit: str = "10", keyword: str = "", get_all: str = "", parent: str = "") -> dict[str, Any]:
    """List categories. Use get_all='true' and parent='true' to get all parent categories (for dropdowns)."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    if get_all: params["get"] = get_all
    if parent: params["parent"] = parent
    return await api("GET", "/admin/categories", params=params)


@mcp.tool()
async def get_category(category_id: str) -> dict[str, Any]:
    """Get details of a specific category by ID."""
    return await api("GET", f"/admin/categories/{category_id}")


@mcp.tool()
async def create_category(data: str) -> dict[str, Any]:
    """Create a new category. Pass data as JSON: {name, slug, parent, image, ...}"""
    import json
    return await api("POST", "/admin/categories", data=json.loads(data))


@mcp.tool()
async def update_category(category_id: str, data: str) -> dict[str, Any]:
    """Update a category by ID. Pass data as JSON with fields to update."""
    import json
    return await api("PUT", f"/admin/categories/{category_id}", data=json.loads(data))


# --- Post Categories ---

@mcp.tool()
async def get_post_category(category_id: str) -> dict[str, Any]:
    """Get details of a specific post category by ID."""
    return await api("GET", f"/admin/post-category/{category_id}")


@mcp.tool()
async def create_post_category(data: str) -> dict[str, Any]:
    """Create a new post category. Pass data as JSON: {name, slug, ...}"""
    import json
    return await api("POST", "/admin/post-category", data=json.loads(data))


@mcp.tool()
async def update_post_category(category_id: str, data: str) -> dict[str, Any]:
    """Update a post category by ID. Pass data as JSON with fields to update."""
    import json
    return await api("PUT", f"/admin/post-category/{category_id}", data=json.loads(data))


# --- Show Categories ---

@mcp.tool()
async def list_show_categories(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all show categories with pagination."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/show-category", params=params)


@mcp.tool()
async def get_show_category(category_id: str) -> dict[str, Any]:
    """Get details of a specific show category by ID."""
    return await api("GET", f"/admin/show-category/{category_id}")


@mcp.tool()
async def create_show_category(data: str) -> dict[str, Any]:
    """Create a new show category. Pass data as JSON: {name, slug, ...}"""
    import json
    return await api("POST", "/admin/show-category", data=json.loads(data))


@mcp.tool()
async def update_show_category(category_id: str, data: str) -> dict[str, Any]:
    """Update a show category by ID. Pass data as JSON with fields to update."""
    import json
    return await api("PUT", f"/admin/show-category/{category_id}", data=json.loads(data))


# --- Clips ---

@mcp.tool()
async def list_clips(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all clips with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/clip", params=params)


@mcp.tool()
async def get_clip(clip_id: str) -> dict[str, Any]:
    """Get details of a specific clip by ID."""
    return await api("GET", f"/admin/clip/{clip_id}")


@mcp.tool()
async def create_clip(data: str) -> dict[str, Any]:
    """Create a new clip. Pass data as JSON: {title, url, description, ...}"""
    import json
    return await api("POST", "/admin/clip", data=json.loads(data))


@mcp.tool()
async def update_clip(clip_id: str, data: str) -> dict[str, Any]:
    """Update a clip by ID. Pass data as JSON with fields to update."""
    import json
    return await api("PUT", f"/admin/clip/{clip_id}", data=json.loads(data))


# --- Galleries ---

@mcp.tool()
async def list_galleries(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all galleries with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/gallery", params=params)


@mcp.tool()
async def get_gallery(gallery_id: str) -> dict[str, Any]:
    """Get details of a specific gallery by ID."""
    return await api("GET", f"/admin/gallery/{gallery_id}")


@mcp.tool()
async def create_gallery(data: str) -> dict[str, Any]:
    """Create a new gallery. Pass data as JSON: {title, images, ...}"""
    import json
    return await api("POST", "/admin/gallery", data=json.loads(data))


@mcp.tool()
async def update_gallery(gallery_id: str, data: str) -> dict[str, Any]:
    """Update a gallery by ID. Pass data as JSON with fields to update."""
    import json
    return await api("PUT", f"/admin/gallery/{gallery_id}", data=json.loads(data))


# --- FAQs ---

@mcp.tool()
async def list_faqs(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all FAQs with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/faq", params=params)


@mcp.tool()
async def get_faq(faq_id: str) -> dict[str, Any]:
    """Get details of a specific FAQ by ID."""
    return await api("GET", f"/admin/faq/{faq_id}")


@mcp.tool()
async def create_faq(data: str) -> dict[str, Any]:
    """Create a new FAQ. Pass data as JSON: {question, answer, ...}"""
    import json
    return await api("POST", "/admin/faq", data=json.loads(data))


@mcp.tool()
async def update_faq(faq_id: str, data: str) -> dict[str, Any]:
    """Update a FAQ by ID. Pass data as JSON with fields to update."""
    import json
    return await api("PUT", f"/admin/faq/{faq_id}", data=json.loads(data))


# --- Policies ---

@mcp.tool()
async def list_policies(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all policies with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/policy", params=params)


@mcp.tool()
async def get_policy(policy_id: str) -> dict[str, Any]:
    """Get details of a specific policy by ID."""
    return await api("GET", f"/admin/policy/{policy_id}")


@mcp.tool()
async def create_policy(data: str) -> dict[str, Any]:
    """Create a new policy. Pass data as JSON: {title, content, ...}"""
    import json
    return await api("POST", "/admin/policy", data=json.loads(data))


@mcp.tool()
async def update_policy(policy_id: str, data: str) -> dict[str, Any]:
    """Update a policy by ID. Pass data as JSON with fields to update."""
    import json
    return await api("PUT", f"/admin/policy/{policy_id}", data=json.loads(data))


# --- Products ---

@mcp.tool()
async def list_products(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all products with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/product", params=params)


@mcp.tool()
async def get_product(product_id: str) -> dict[str, Any]:
    """Get details of a specific product by ID."""
    return await api("GET", f"/admin/product/{product_id}")


@mcp.tool()
async def create_product(data: str) -> dict[str, Any]:
    """Create a new product. Pass data as JSON: {name, price, categoryId, description, image, ...}"""
    import json
    return await api("POST", "/admin/product", data=json.loads(data))


@mcp.tool()
async def update_product(product_id: str, data: str) -> dict[str, Any]:
    """Update a product by ID. Pass data as JSON with fields to update."""
    import json
    return await api("PUT", f"/admin/product/{product_id}", data=json.loads(data))


# --- Coupons ---

@mcp.tool()
async def list_coupons(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all coupons with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/coupon", params=params)


@mcp.tool()
async def get_coupon(coupon_id: str) -> dict[str, Any]:
    """Get details of a specific coupon by ID."""
    return await api("GET", f"/admin/coupon/{coupon_id}")


@mcp.tool()
async def create_coupon(data: str) -> dict[str, Any]:
    """Create a new coupon. Pass data as JSON: {code, discount, showId, ...}"""
    import json
    return await api("POST", "/admin/coupon", data=json.loads(data))


@mcp.tool()
async def update_coupon(coupon_id: str, data: str) -> dict[str, Any]:
    """Update a coupon by ID. Pass data as JSON with fields to update."""
    import json
    return await api("PUT", f"/admin/coupon/{coupon_id}", data=json.loads(data))


# --- Contacts ---

@mcp.tool()
async def list_contacts(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all contacts/messages with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/contact", params=params)


@mcp.tool()
async def get_contact(contact_id: str) -> dict[str, Any]:
    """Get details of a specific contact by ID."""
    return await api("GET", f"/admin/contact/{contact_id}")


@mcp.tool()
async def update_contact(contact_id: str, data: str) -> dict[str, Any]:
    """Update a contact by ID. Pass data as JSON with fields to update."""
    import json
    return await api("PUT", f"/admin/contact/{contact_id}", data=json.loads(data))


# --- Settings ---

@mcp.tool()
async def get_setting(setting_id: str) -> dict[str, Any]:
    """Get a specific setting by ID."""
    return await api("GET", f"/admin/setting/{setting_id}")


@mcp.tool()
async def update_setting(setting_id: str, data: str) -> dict[str, Any]:
    """Update a setting by ID. Pass data as JSON with fields to update."""
    import json
    return await api("PUT", f"/admin/setting/{setting_id}", data=json.loads(data))


# --- Bookings ---

@mcp.tool()
async def list_bookings(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all bookings with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/booking", params=params)


@mcp.tool()
async def get_booking(booking_id: str) -> dict[str, Any]:
    """Get details of a specific booking by ID."""
    return await api("GET", f"/admin/booking/{booking_id}")


@mcp.tool()
async def create_booking(data: str) -> dict[str, Any]:
    """Create a new booking. Pass data as JSON."""
    import json
    return await api("POST", "/admin/booking", data=json.loads(data))


# --- Groups ---

@mcp.tool()
async def list_groups(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all user groups with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/group", params=params)


@mcp.tool()
async def get_group(group_id: str) -> dict[str, Any]:
    """Get details of a specific group by ID."""
    return await api("GET", f"/admin/group/{group_id}")


# --- Users/Staff ---

@mcp.tool()
async def list_users(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all users/staff with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/users", params=params)


@mcp.tool()
async def get_user(user_id: str) -> dict[str, Any]:
    """Get details of a specific user by ID."""
    return await api("GET", f"/admin/users/{user_id}")


# --- Slots ---

@mcp.tool()
async def list_slots(page: str = "1", limit: str = "10", show_id: str = "") -> dict[str, Any]:
    """List all slots with pagination. Filter by show_id."""
    params = {"page": page, "limit": limit}
    if show_id: params["showId"] = show_id
    return await api("GET", "/admin/slot", params=params)


@mcp.tool()
async def get_slot(slot_id: str) -> dict[str, Any]:
    """Get details of a specific slot by ID."""
    return await api("GET", f"/admin/slot/{slot_id}")


@mcp.tool()
async def update_slot(slot_id: str, data: str) -> dict[str, Any]:
    """Update a slot by ID. Pass data as JSON with fields to update."""
    import json
    return await api("PUT", f"/admin/slot/{slot_id}", data=json.loads(data))


# --- Orders Third Party ---

@mcp.tool()
async def list_orders_third_party(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all third-party orders with pagination and search."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/order-third-party", params=params)


@mcp.tool()
async def get_orders_third_party_stats() -> dict[str, Any]:
    """Get third-party order statistics."""
    return await api("GET", "/admin/order-third-party/stats")


# --- Check-in ---

@mcp.tool()
async def list_checkins(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all check-in histories with pagination."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/checkin", params=params)


@mcp.tool()
async def list_checkins_third_party(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all third-party check-in histories with pagination."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/order-third-party/checkin", params=params)


# --- Tracking ---

@mcp.tool()
async def list_tracking(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all order tracking records with pagination."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/tracking", params=params)


@mcp.tool()
async def get_tracking(tracking_id: str) -> dict[str, Any]:
    """Get details of a specific tracking record by ID."""
    return await api("GET", f"/admin/tracking/{tracking_id}")


# --- Affiliate ---

@mcp.tool()
async def list_affiliate_histories(page: str = "1", limit: str = "10") -> dict[str, Any]:
    """List affiliate commission histories with pagination."""
    params = {"page": page, "limit": limit}
    return await api("GET", "/admin/affiliate/histories", params=params)


@mcp.tool()
async def get_affiliate_statistics(customer_id: str = "", from_date: str = "", to_date: str = "") -> dict[str, Any]:
    """Get affiliate statistics. Optionally filter by customerId, fromDate, toDate."""
    params: dict[str, str] = {}
    if customer_id: params["customerId"] = customer_id
    if from_date: params["fromDate"] = from_date
    if to_date: params["toDate"] = to_date
    return await api("GET", "/admin/affiliate/statistics", params=params)


@mcp.tool()
async def list_withdraw_requests(page: str = "1", limit: str = "10") -> dict[str, Any]:
    """List affiliate withdraw requests with pagination."""
    params = {"page": page, "limit": limit}
    return await api("GET", "/admin/affiliate/withdraw-requests", params=params)


@mcp.tool()
async def change_withdraw_request_status(request_id: str, data: str) -> dict[str, Any]:
    """Change the status of an affiliate withdraw request. Pass data as JSON: {status: '...'}"""
    import json
    return await api("PUT", f"/admin/affiliate/withdraw-request/{request_id}/status", data=json.loads(data))


# --- Zones (Location) ---

@mcp.tool()
async def list_provinces() -> dict[str, Any]:
    """List all provinces/zones."""
    return await api("GET", "/admin/zone-provinces", params={"limit": "100", "page": "1"})


@mcp.tool()
async def list_districts(province_id: str) -> dict[str, Any]:
    """List all districts in a province. Provide the province ID."""
    return await api("GET", "/admin/zone-districts", params={"get": "true", "zoneProvince": province_id})


@mcp.tool()
async def list_wards(district_id: str) -> dict[str, Any]:
    """List all wards in a district. Provide the district ID."""
    return await api("GET", "/admin/zone-wards", params={"get": "true", "zoneDistrict": district_id})


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
