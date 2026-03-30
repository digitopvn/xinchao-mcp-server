"""Shared upload helpers — CDN upload, image download, field processing."""

import logging
from typing import Any

logger = logging.getLogger("xinchao-mcp.upload")

_IMAGE_FIELDS = {"image", "imageMb", "thumbImage", "thumbImageMb", "thumbMaster", "thumbMasterMb", "meta_image"}

_VALID_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml", "image/bmp", "image/tiff"}


def _ext_from_content_type(content_type: str) -> str:
    """Extract file extension from content type (e.g. 'image/jpeg' -> 'jpg')."""
    ext = content_type.split("/")[-1]
    if ext == "jpeg":
        return "jpg"
    if ext == "svg+xml":
        return "svg"
    return ext


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
            return {"content": resp.content, "content_type": content_type, "ext": _ext_from_content_type(content_type)}
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
            del data[field]
            continue
        result = await _upload_to_cdn(dl["content"], dl["content_type"], dl["ext"], filename_prefix=field)
        if "error" in result:
            logger.warning("Failed to upload %s to CDN: %s — REMOVING field to prevent broken URL", field, result["error"])
            del data[field]
            continue
        logger.info("CDN upload response for %s: %s", field, result)
        cdn_path = _extract_cdn_path(result)
        if cdn_path:
            logger.info("Uploaded %s -> %s", field, cdn_path)
            data[field] = cdn_path
        else:
            logger.error("Upload succeeded but CANNOT find path in response for %s: %s — REMOVING field", field, result)
            del data[field]
    return data
