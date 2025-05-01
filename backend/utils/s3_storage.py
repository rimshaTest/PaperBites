# utils/s3_storage.py
import logging
import boto3
from botocore.exceptions import ClientError
import os
from typing import Optional, Dict, Any
from config import Config

logger = logging.getLogger("paperbites.s3_storage")

class S3Storage:
    """
    Handles storage and retrieval of videos from AWS S3 with cost control.
    """
    
    def __init__(
        self, 
        bucket_name: Optional[str] = None,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ):
        """
        Initialize S3 storage handler.
        
        Args:
            bucket_name: Name of the S3 bucket
            region_name: AWS region name
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
        """
        config = Config()
        
        self.bucket_name = bucket_name or config.get("storage.s3.bucket_name", "paperbites-videos")
        self.region_name = region_name or config.get("storage.s3.region", "us-east-1")
        
        # Use provided credentials or get from config/environment variables
        self.aws_access_key_id = aws_access_key_id or config.get("storage.s3.access_key_id") or os.environ.get('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = aws_secret_access_key or config.get("storage.s3.secret_access_key") or os.environ.get('AWS_SECRET_ACCESS_KEY')
        
        # Check if credentials are available
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            logger.warning("AWS credentials not provided. S3 functionality will be limited to local fallback.")
            self.s3_client = None
        else:
            try:
                # Initialize S3 client
                self.s3_client = boto3.client(
                    's3',
                    region_name=self.region_name,
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key
                )
                logger.info(f"S3 client initialized for region {self.region_name}")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
                self.s3_client = None
    
    def check_bucket_exists(self) -> bool:
        """Check if the specified bucket exists and is accessible."""
        if not self.s3_client:
            return False
            
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket '{self.bucket_name}' exists and is accessible")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            
            if error_code == '404':
                logger.warning(f"Bucket '{self.bucket_name}' does not exist")
            elif error_code == '403':
                logger.warning(f"Access denied to bucket '{self.bucket_name}'")
            else:
                logger.error(f"Error checking bucket: {e}")
            
            return False
    
    def create_bucket(self) -> bool:
        """Create the S3 bucket if it doesn't exist."""
        if not self.s3_client:
            logger.error("Cannot create bucket: S3 client not initialized")
            return False
            
        try:
            # Check if bucket already exists
            if self.check_bucket_exists():
                return True
                
            logger.info(f"Creating S3 bucket '{self.bucket_name}'")
            
            # Create the bucket in the specified region
            if self.region_name != 'us-east-1':
                self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={
                        'LocationConstraint': self.region_name
                    }
                )
            else:
                # us-east-1 doesn't use LocationConstraint
                self.s3_client.create_bucket(Bucket=self.bucket_name)
                
            logger.info(f"S3 bucket '{self.bucket_name}' created successfully")
            
            # Set lifecycle policy to manage costs
            self._set_lifecycle_policy()
            
            return True
            
        except ClientError as e:
            logger.error(f"Failed to create S3 bucket: {e}")
            return False
    
    def _set_lifecycle_policy(self) -> bool:
        """Set lifecycle policy on the bucket to manage costs."""
        if not self.s3_client:
            return False
            
        try:
            # Define lifecycle policy
            lifecycle_config = {
                'Rules': [
                    {
                        'ID': 'AutoCleanup',
                        'Status': 'Enabled',
                        'Prefix': 'videos/',
                        'Expiration': {'Days': 90},  # Delete files after 90 days
                        'Transitions': [
                            {
                                'Days': 30,
                                'StorageClass': 'STANDARD_IA'  # Move to cheaper storage after 30 days
                            }
                        ]
                    }
                ]
            }
            
            # Apply the policy
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket_name,
                LifecycleConfiguration=lifecycle_config
            )
            
            logger.info("Lifecycle policy applied to bucket for cost management")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to set lifecycle policy: {e}")
            return False
    
    def upload_video(
        self, 
        file_path: str, 
        object_key: Optional[str] = None,
        content_type: str = 'video/mp4',
        make_public: bool = True,
        metadata: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Upload a video file to S3.
        
        Args:
            file_path: Path to the local video file
            object_key: S3 object key (default: use file name)
            content_type: MIME type of the file
            make_public: Whether to make the file publicly accessible
            metadata: Additional metadata to attach to the object
            
        Returns:
            str: Public URL of the uploaded file or local path if upload failed
        """
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
            
        # If S3 client not available, return local path
        if not self.s3_client:
            logger.warning("S3 client not available. Using local file path.")
            return f"file://{os.path.abspath(file_path)}"
            
        # Set default object key if not provided
        if not object_key:
            object_key = os.path.basename(file_path)
            
        # Add 'videos/' prefix for better organization
        if not object_key.startswith('videos/'):
            object_key = f"videos/{object_key}"
        
        try:
            # Create bucket if it doesn't exist
            if not self.check_bucket_exists():
                if not self.create_bucket():
                    logger.error("Failed to create bucket")
                    return f"file://{os.path.abspath(file_path)}"
            
            # Set extra args for upload
            extra_args = {
                'ContentType': content_type
            }
            
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Upload the file
            logger.info(f"Uploading {file_path} to S3 bucket {self.bucket_name}")
            self.s3_client.upload_file(
                file_path, 
                self.bucket_name, 
                object_key,
                ExtraArgs=extra_args
            )
            
            # Return the public URL
            if make_public:
                url = f"https://{self.bucket_name}.s3.amazonaws.com/{object_key}"
            else:
                # Generate a pre-signed URL that expires in 7 days
                url = self.generate_presigned_url(object_key, expiration_seconds=604800)
                
            logger.info(f"File uploaded successfully to {url}")
            return url
            
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            # Note: If AWS budget limit is reached, this will catch the error
            return f"file://{os.path.abspath(file_path)}"  # Return local path as fallback
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {e}")
            return f"file://{os.path.abspath(file_path)}"
    
    def generate_presigned_url(
        self, 
        object_key: str, 
        expiration_seconds: int = 3600
    ) -> Optional[str]:
        """
        Generate a pre-signed URL for a private S3 object.
        
        Args:
            object_key: S3 object key
            expiration_seconds: URL expiration time in seconds
            
        Returns:
            str: Pre-signed URL or None if generation failed
        """
        if not self.s3_client:
            return None
            
        try:
            # Add 'videos/' prefix if not present
            if not object_key.startswith('videos/'):
                object_key = f"videos/{object_key}"
                
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expiration_seconds
            )
            return url
        except Exception as e:
            logger.error(f"Error generating pre-signed URL: {e}")
            return None
    
    def list_videos(self, prefix: str = 'videos/', max_items: int = 100) -> list[Dict[str, Any]]:
        """
        List videos in the S3 bucket.
        
        Args:
            prefix: Object key prefix to filter by
            max_items: Maximum number of items to return
            
        Returns:
            list: List of dictionaries with video information
        """
        if not self.s3_client:
            return []
            
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_items
            )
            
            if 'Contents' not in response:
                return []
                
            videos = []
            for obj in response['Contents']:
                # Get object metadata
                try:
                    metadata_response = self.s3_client.head_object(
                        Bucket=self.bucket_name,
                        Key=obj['Key']
                    )
                    
                    video_info = {
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'url': f"https://{self.bucket_name}.s3.amazonaws.com/{obj['Key']}",
                        'metadata': metadata_response.get('Metadata', {})
                    }
                    
                    videos.append(video_info)
                except Exception as e:
                    logger.error(f"Error getting metadata for {obj['Key']}: {e}")
            
            return videos
            
        except Exception as e:
            logger.error(f"Error listing videos: {e}")
            return []
    
    def delete_video(self, object_key: str) -> bool:
        """
        Delete a video from S3.
        
        Args:
            object_key: S3 object key
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        if not self.s3_client:
            return False
            
        try:
            # Add 'videos/' prefix if not present
            if not object_key.startswith('videos/'):
                object_key = f"videos/{object_key}"
                
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            logger.info(f"Deleted {object_key} from bucket {self.bucket_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file from S3: {e}")
            return False