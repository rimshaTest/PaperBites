import config from '../config';
import { v2 } from 'cloudinary';
const cloudinary = v2;

const CLOUDINARY_CLOUD_NAME = config.cloudinary.cloud_name;
const CLOUDINARY_API_KEY = config.cloudinary.api_key;
const CLOUDINARY_API_SECRET = config.cloudinary.api_secret;

cloudinary.config({
  cloud_name: CLOUDINARY_CLOUD_NAME,
  api_key: CLOUDINARY_API_KEY,
  api_secret: CLOUDINARY_API_SECRET,
  secure: true // Use HTTPS for security
});

export const fetchCloudinaryVideos = async () => {
  // Function to fetch videos from Cloudinary
  cloudinary.search.expression('resource_type: video').sort_by('public_id', 'desc').max_results(30).execute()
    .then((result: any) => {
      console.log(result);
    })
    .catch((err: unknown) => {
      console.log(err);
    });
}