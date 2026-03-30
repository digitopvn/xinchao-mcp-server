"""XinChao.world MCP Server — admin API tools for GoClaw agents."""

import os
import sys
import logging
from typing import Any
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import TransportSecuritySettings
from xinchao_api import api
from config import PORT, UPLOAD_DIR
from upload_helpers import _download_image, _upload_to_cdn, _extract_cdn_path, _auto_upload_image_fields

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("xinchao-mcp")

VERSION = "2.5.0"
BUILD_DATE = "2026-03-30"

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


# --- Upload tools ---

@mcp.tool()
async def upload_image(image_url: str) -> dict[str, Any]:
    """Upload an image to XinChao CDN by providing a public URL.
    Returns the uploaded image path to use in create_post/update_post image fields.
    The server downloads the image from the URL, validates it, and uploads to CDN.

    IMPORTANT FOR DISCORD BOTS:
    When a user sends an image via Discord, the attachment already has a public URL like:
    https://cdn.discordapp.com/attachments/...
    Just pass that Discord attachment URL directly to this tool — NO need to create http servers
    or any workarounds. The URL is valid for several minutes, enough for download + CDN upload.

    DO NOT run shell commands like 'python3 -m http.server' to serve files.
    DO NOT create temporary HTTP servers. Just use the attachment URL directly."""
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


@mcp.tool()
async def upload_local_file(filename: str) -> dict[str, Any]:
    """Upload a file from the server's /uploads/ folder to XinChao CDN.
    Use this after a file has been placed in the uploads directory (e.g. via POST /upload HTTP endpoint).
    Returns CDN path on success.
    Args:
        filename: Name of the file in /uploads/ folder (e.g. 'photo.jpg'). No paths allowed."""
    import mimetypes
    from upload_helpers import _VALID_IMAGE_TYPES, _ext_from_content_type

    # Path traversal protection
    if "/" in filename or "\\" in filename or ".." in filename:
        return {"error": "Invalid filename. Must be a plain filename, no paths or '..' allowed."}

    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        return {"error": f"File not found: {filename}. Check /uploads/ folder."}

    # Detect mime type
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type or mime_type not in _VALID_IMAGE_TYPES:
        return {"error": f"Invalid or unsupported image type: {mime_type}. Allowed: {', '.join(sorted(_VALID_IMAGE_TYPES))}"}

    ext = _ext_from_content_type(mime_type)
    file_bytes = file_path.read_bytes()

    try:
        result = await _upload_to_cdn(file_bytes, mime_type, ext, filename_prefix=filename.rsplit(".", 1)[0])
        if "error" in result:
            return result

        cdn_path = _extract_cdn_path(result.get("data", result))
        if not cdn_path:
            return {"error": f"Upload succeeded but could not extract CDN path from response: {result}"}

        logger.info("upload_local_file: %s -> %s (deleted local)", filename, cdn_path)
        return {"cdn_path": cdn_path, "filename": filename, "size": len(file_bytes)}
    finally:
        # Always cleanup local file (success or failure)
        file_path.unlink(missing_ok=True)


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

    # Auto-create uploads directory for file upload endpoint
    UPLOAD_DIR.mkdir(exist_ok=True)

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

        # File upload endpoint (POST /upload with X-Upload-Key auth)
        from upload_endpoint import handle_upload
        app.add_route("/upload", handle_upload, methods=["POST"])

        logger.info("Starting XinChaoMCP (%s) on port %s", mode, port)
        uvicorn.run(app, host="0.0.0.0", port=port,
                    log_level="info",
                    timeout_keep_alive=120,
                    timeout_graceful_shutdown=30,
                    h11_max_incomplete_event_size=256 * 1024)
    else:
        mcp.run(transport="stdio")
