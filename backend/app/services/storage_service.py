import os
import shutil
import uuid
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile
from backend.app.config import settings


class StorageService:
    @staticmethod
    def save_upload_file(upload_file: UploadFile, folder: Path) -> Tuple[str, Path]:
        """
        Saves uploaded file to disk with unique filename and returns (relative_url, absolute_path)
        """
        folder.mkdir(parents=True, exist_ok=True)
        ext = Path(upload_file.filename).suffix or ".png"
        unique_name = f"{uuid.uuid4()}{ext}"
        target_path = folder / unique_name

        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        # Build accessible URL relative to backend
        rel_folder = folder.name
        rel_url = f"/uploads/{rel_folder}/{unique_name}"
        return rel_url, target_path

    @staticmethod
    def save_bytes(data: bytes, filename: str, folder: Path) -> Tuple[str, Path]:
        folder.mkdir(parents=True, exist_ok=True)
        safe_filename = os.path.basename(filename or "screenshot.png")
        ext = Path(safe_filename).suffix or ".png"
        unique_name = f"{uuid.uuid4()}_{safe_filename}"
        target_path = folder / unique_name

        with open(target_path, "wb") as f:
            f.write(data)

        rel_folder = folder.name
        rel_url = f"/uploads/{rel_folder}/{unique_name}"
        return rel_url, target_path
