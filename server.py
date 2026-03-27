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

VERSION = "2.4.0"
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


# --- Shows ---

@mcp.tool()
async def list_shows(page: str = "1", limit: str = "10", keyword: str = "") -> dict[str, Any]:
    """List all shows with pagination and search.

    IMPORTANT: Before calling this tool, you MUST ask the user whether they want:
    - Shows that have ALREADY HAPPENED (past/completed shows)
    - Shows that are UPCOMING / NOT YET HAPPENED (future shows)
    - Or ALL shows regardless of date
    This helps filter results and provide relevant information to the user."""
    params = {"page": page, "limit": limit}
    if keyword: params["keyword"] = keyword
    return await api("GET", "/admin/show", params=params)


@mcp.tool()
async def get_show(show_id: str) -> dict[str, Any]:
    """Get details of a specific show by ID."""
    return await api("GET", f"/admin/show/{show_id}")



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
