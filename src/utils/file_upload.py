from fastapi import UploadFile
import cloudinary.uploader

async def upload(image: UploadFile, folder: str):
    file = await image.read()
    result = cloudinary.uploader.upload(
        file,
        folder=folder
    )

    return result["secure_url"]