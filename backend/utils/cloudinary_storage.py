import cloudinary
import cloudinary.uploader
import os
from config import Config  # Your existing config module


class CloudinaryStorage:
    """Handles storage operations with Cloudinary."""
    
    def __init__(self, cloud_name=None, api_key=None, api_secret=None):
        """Initialize with credentials from config or environment vars."""
        # Get config instance
        config_instance = Config()

        # Configure Cloudinary - use your config object or environment variables
        cloudinary.config(
            cloud_name = config_instance.get("storage.cloudinary.cloud_name"),
            api_key = config_instance.get("storage.cloudinary.api_key"),
            api_secret = config_instance.get("storage.cloudinary.api_secret")
        )
        
    def upload_video(self, file_path, **options):
        """Upload video with proper error handling."""
        try:
            # Attempt upload
            result = cloudinary.uploader.upload(
                file_path,
                resource_type="video",
                **options
            )
            return result['secure_url']
        except Exception as e:
            print(f"Cloudinary upload error: {e}")
            return None
            
    def health_check(self):
        """Check if Cloudinary connection is working."""
        try:
            # Ping the API with a simple request
            cloudinary.api.ping()
            return True
        except Exception:
            return False