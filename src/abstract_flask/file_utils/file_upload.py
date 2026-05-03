import os
from flask import Flask, request, flash, redirect
from werkzeug.utils import secure_filename
from abstract_utilities import *
from abstract_utilities import derive_media_type
logger = get_logFile(__name__)
UPLOAD_FOLDER = 'uploads'
def get_ext(file_path):
    return os.path.splitext(str(file_path))[-1]
class UPOLOADMANAGER(metaclass=SingletonMeta):
    def __init__(self,
                 upload_folder=None,
                 allowed_exts=None,
                 allowed_types=None,
                 allowed_size=None
                 ):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.upload_folder = upload_folder or 'uploads'
            if not allowed_exts and not allowed_types:
                allowed_types = ['image','video','spreadsheet','document']
                allowed_exts= get_media_exts(categories=allowed_types)
            if allowed_types and not allowed_exts:
                allowed_exts= get_media_exts(categories=allowed_types)
            self.allowed_exts = allowed_exts
            self.allowed_types = allowed_types
            self.allowed_size = allowed_size
            
    def get_media_type(self,file_path):
        ext = os.path.splitext(str(file_path))[-1]
        if ext:
            return derive_media_type(ext)
    def is_allowed_ext(self,obj):
        ext = get_ext(str(obj))
        return ext and ext in self.allowed_exts
    def is_allowed_file(self,obj):
        return self.is_allowed_ext(obj)
    def get_user_folder(self,req):
        user_ip = req.remote_addr
        return os.path.join(self.upload_folder, user_ip.replace('.', '_'))
    def get_upload_dir(self, req, file_storage,upload_dir=None,upload_path=None):
        if upload_dir:
            return upload_dir
        filename = file_storage.filename
        if not self.is_allowed_file(filename):
            # Pass the filename specifically to get the extension for the error
            raise ValueError(f"Unsupported file type: {Path(filename).suffix}")
            
        # Use pathlib for easy folder joining and creation
        base_path = Path(self.upload_folder)
        user_folder = base_path / req.remote_addr.replace('.', '_')
        
        file_type = self.get_media_type(filename) or 'other'
        output_dir = user_folder / file_type
        
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def get_upload_path(self, req, file_storage,upload_dir=None,upload_path=None):
        if upload_path:
            return upload_path
        upload_dir = self.get_upload_dir(req, file_storage,upload_dir=upload_dir)
        ext = Path(file_storage.filename).suffix.lower()
        unique_name = f"{uuid.uuid4().hex}{ext}"
        return upload_dir / unique_name
def get_upload_mgr(
    upload_folder=None,
    allowed_exts=None,
    allowed_types=None,
    allowed_size=None
    ):
    return UPOLOADMANAGER(
        upload_folder=upload_folder,
        allowed_exts=allowed_exts,
        allowed_types=allowed_types,
        allowed_size=allowed_size
        )
def get_upload_dir(req,file_storage,upload_dir=None,upload_path=None):
    return get_upload_mgr().get_upload_dir(req,file_storage,upload_dir=upload_dir,upload_path=upload_path)
def get_upload_path(req,file_storage,upload_dir=None,upload_path=None):
    return get_upload_mgr().get_upload_path(req,file_storage,upload_dir=upload_dir,upload_path=upload_path)
def get_user_folder(file_storage):
    return get_upload_mgr().get_user_folder(req)
def is_allowed_file(obj):
    return get_upload_mgr().is_allowed_file(obj)
def is_allowed_ext(obj):
    return get_upload_mgr().is_allowed_file(obj)
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_flask_uploaded_file(req,file_storage,upload_dir=None,upload_path=None) -> str:
    if not file_storage or not file_storage.filename:
        raise ValueError("Missing uploaded image file")
    original_name = None
    if upload_path:
        if not upload_dir:
            upload_dir = os.path.dirname(str(upload_dir))
        original_name = os.path.basename(str(upload_path))
        
    original_name = original_name or secure_filename(file_storage.filename)
    ext = Path(original_name).suffix.lower()
    output_path = upload_path or get_upload_path(req,file_storage,upload_dir=upload_dir)
    file_storage.save(output_path)
    return str(output_path)

def upload_flask_files(upload_dir=None,upload_path=None):
    # 1. Access multiple files from the client request
    files = request.files.getlist('files')
    logger.info(f"files= {files}")
    if not files or files[0].filename == '':
        return {"message": "No files selected", "status_code": 400}, 400

    file_chart = {
        "ip": request.remote_addr,
        "time": time.time(),
        "files": {}
    }
    try:

        for file in files:
            logger.info(file)
            # Important: is_allowed_file needs the filename string
            if file and is_allowed_file(file.filename):
                # save_uploaded_image handles the directory creation and naming
                saved_path_str = save_flask_uploaded_file(request, file,upload_dir=upload_dir,upload_path=upload_path)
                logger.info(saved_path_str)
                # Log metadata
                file_chart["files"][file.filename] = {
                    "time": time.time(),
                    "path": saved_path_str,
                    "type": get_upload_mgr().get_media_type(saved_path_str)
                }
            else:
                return {"message": f"File {file.filename} type not allowed", "status_code": 400}, 400
                
        return {"uploads": file_chart, "message": "Batch upload successful", "status_code": 200}, 200

    except Exception as e:
        return {"message": str(e), "status_code": 500}, 500
