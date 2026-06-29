import io
import base64
import logging
from huggingface_hub import InferenceClient
from config import HF_TOKEN

logger = logging.getLogger("talentree.services.image")

def generate_logo_image(logo_prompt: str) -> str:
    """Generates logo image from prompt using FLUX Schnell model."""
    try:
        logger.info(f"Invoking FLUX model for prompt: {logo_prompt}")
        client = InferenceClient("black-forest-labs/FLUX.1-schnell", token=HF_TOKEN)
        image = client.text_to_image(logo_prompt)
        
        # Save to buffer
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        base64_encoded = base64.b64encode(img_bytes).decode('utf-8')
        return base64_encoded
    except Exception as e:
        logger.error(f"Failed to generate image via HF client: {e}")
        return ""

def upload_to_cloudflare_r2(base64_data: str, session_id: str) -> str:
    """
    Placeholder service for backend team to upload images to Cloudflare R2.
    Returns the public HTTP URL of the uploaded image asset.
    """
    logger.info(f"Cloudflare R2 Upload triggered for session: {session_id}")
    # Backend team integration:
    # 1. Decode base64_data into raw bytes
    # 2. Upload to Cloudflare R2 bucket using boto3 (S3 SDK) or Cloudflare SDK
    # 3. Return the public HTTPS URL (e.g. "https://pub-xxxx.r2.dev/logos/{session_id}.png")
    
    # For now, return the mock local serving file URL or public placeholder
    return f"https://pub-mock-r2.dev/logos/{session_id}.png"
