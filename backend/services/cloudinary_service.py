"""
Cloudinary Configuration and Upload Service
All logos are stored in the USINAS folder on Cloudinary.
"""
import os
import logging
from typing import Optional, Tuple

import cloudinary
import cloudinary.uploader
import cloudinary.utils

logger = logging.getLogger(__name__)

def init_cloudinary():
    """Initialize Cloudinary with environment variables."""
    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
        api_key=os.environ.get('CLOUDINARY_API_KEY'),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
        secure=True,
    )
    logger.info(f"Cloudinary configured: cloud={os.environ.get('CLOUDINARY_CLOUD_NAME')}")


def upload_logo(file_bytes: bytes, filename: str, entity_type: str = 'client') -> dict:
    """
    Upload a logo image to Cloudinary in the USINAS folder.
    Returns dict with public_id and secure_url.
    """
    # Clean filename for public_id
    clean_name = filename.rsplit('.', 1)[0].replace(' ', '_').lower()[:50]
    public_id = f"USINAS/{entity_type}_{clean_name}"

    result = cloudinary.uploader.upload(
        file_bytes,
        folder='USINAS',
        public_id=f"{entity_type}_{clean_name}",
        overwrite=True,
        resource_type='image',
        transformation=[
            {'width': 400, 'height': 400, 'crop': 'limit', 'quality': 'auto'}
        ]
    )

    return {
        'public_id': result.get('public_id', ''),
        'secure_url': result.get('secure_url', ''),
        'url': result.get('url', ''),
        'width': result.get('width', 0),
        'height': result.get('height', 0),
    }


def get_logo_thumbnail_url(public_id: str, width: int = 200, height: int = 200) -> str:
    """Generate a thumbnail URL for a logo using Cloudinary transformations."""
    if not public_id:
        return ''
    url, _ = cloudinary.utils.cloudinary_url(
        public_id,
        width=width,
        height=height,
        crop="fill",
        quality="auto",
        format="auto",
    )
    return url


def delete_logo(public_id: str) -> bool:
    """Delete a logo from Cloudinary."""
    if not public_id:
        return False
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get('result') == 'ok'
    except Exception as e:
        logger.error(f"Cloudinary delete error: {e}")
        return False
