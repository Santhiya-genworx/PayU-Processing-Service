import cloudinary

from src.config.settings import settings

"""This module configures the Cloudinary client using the settings defined in the application's configuration. It initializes the Cloudinary client with the necessary credentials, including the cloud name, API key, and API secret, which are required for authenticating and interacting with the Cloudinary service for media management tasks such as uploading and processing images and videos. The configuration is set up to allow the application to seamlessly integrate with Cloudinary for handling media-related operations"""
cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
)
