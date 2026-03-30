"""HTTP upload endpoint — receives multipart file, pushes to XinChao CDN, returns CDN path."""

import hmac
import logging
from uuid import uuid4
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse
from config import UPLOAD_API_KEY, UPLOAD_DIR, MAX_UPLOAD_SIZE
from upload_helpers import _upload_to_cdn, _extract_cdn_path, _ext_from_content_type, _VALID_IMAGE_TYPES

logger = logging.getLogger("xinchao-mcp.upload")


async def handle_upload(request: StarletteRequest) -> JSONResponse:
    """POST /upload — multipart file upload to XinChao CDN.

    Headers: X-Upload-Key: <UPLOAD_API_KEY>
    Body: multipart/form-data with field "file"
    Returns: {cdn_path, filename, size} or {error}
    """
    # 1. Auth check (timing-safe comparison to prevent timing attacks)
    api_key = request.headers.get("x-upload-key", "")
    if not UPLOAD_API_KEY or not hmac.compare_digest(api_key, UPLOAD_API_KEY):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    # 2. Parse multipart form (use async context manager to prevent file handle leaks)
    try:
        async with request.form() as form:
            upload_file = form.get("file")
            if not upload_file or not hasattr(upload_file, "read"):
                return JSONResponse({"error": "No file provided. Use field name 'file'."}, status_code=400)

            # 3. Validate content type
            content_type = (upload_file.content_type or "").split(";")[0].strip().lower()
            if content_type not in _VALID_IMAGE_TYPES:
                return JSONResponse(
                    {"error": f"Invalid image type: {content_type}. Allowed: {', '.join(sorted(_VALID_IMAGE_TYPES))}"},
                    status_code=400,
                )

            # 4. Read file bytes and validate size
            file_bytes = await upload_file.read()
            if len(file_bytes) > MAX_UPLOAD_SIZE:
                return JSONResponse(
                    {"error": f"File too large: {len(file_bytes)} bytes. Max: {MAX_UPLOAD_SIZE} bytes ({MAX_UPLOAD_SIZE // 1024 // 1024}MB)"},
                    status_code=400,
                )
            if len(file_bytes) < 100:
                return JSONResponse({"error": "File too small, likely not a valid image"}, status_code=400)

            # 5. Determine extension from content type
            ext = _ext_from_content_type(content_type)
            original_filename = getattr(upload_file, "filename", "upload") or "upload"
    except Exception as e:
        return JSONResponse({"error": f"Invalid form data: {e}"}, status_code=400)

    # 6. Save temp file, push to CDN, cleanup
    temp_name = f"{uuid4().hex}.{ext}"
    temp_path = UPLOAD_DIR / temp_name

    try:
        temp_path.write_bytes(file_bytes)
        logger.info("Saved temp file: %s (%d bytes) from %s", temp_name, len(file_bytes), original_filename)

        # 7. Upload to CDN via existing helper
        result = await _upload_to_cdn(file_bytes, content_type, ext, filename_prefix=temp_name.split(".")[0])
        if "error" in result:
            logger.error("CDN upload failed for %s: %s", temp_name, result["error"])
            return JSONResponse({"error": f"CDN upload failed: {result['error']}"}, status_code=500)

        # 8. Extract CDN path
        cdn_path = _extract_cdn_path(result.get("data", result))
        if not cdn_path:
            logger.error("CDN upload succeeded but no path in response: %s", result)
            return JSONResponse({"error": "CDN upload succeeded but could not extract path from response"}, status_code=500)

        logger.info("Upload success: %s -> %s", original_filename, cdn_path)
        return JSONResponse({
            "cdn_path": cdn_path,
            "filename": original_filename,
            "size": len(file_bytes),
        })

    finally:
        # Always cleanup temp file
        if temp_path.exists():
            temp_path.unlink()
            logger.info("Cleaned up temp file: %s", temp_name)
