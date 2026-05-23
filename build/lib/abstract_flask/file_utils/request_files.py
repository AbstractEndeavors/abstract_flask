from .imports import secure_filename
def get_request_files(req=None):
    return req.files
def get_request_file(req=None,request_file=None):
    request_files = get_request_files(req=req) or {}
    request_file = request_files.get("file")
    return request_file
def get_request_filename(req=None,request_file=None):
    request_file = request_file or get_request_file(req=req,request_file=request_file)
    request_filename = request_file.filename
    return request_filename
def get_request_safe_filename(req=None,request_file=None):
    request_filename = get_request_filename(req=req,request_file=request_file)
    if request_filename == "":
        return request_filename
    safe_filename = secure_filename(request_filename)
    return safe_filename
def get_subdir(req=None):
    subdir = req.form.get("subdir", "").strip()
    return subdir
def get_safe_subdir(req=None):
    subdir = get_subdir(req=req)
    safe_subdir = secure_filename(subdir)
    return safe_subdir
def get_user_filename(req=None):
    safe_subdir = get_safe_subdir(req=req)
    safe_filename = get_request_safe_filename(req=req)
    return filename
def get_req_file(req=None):
    upload = req.files.get("files")
    if upload is None:
        raise ValueError("No uploaded file received. Expected multipart field 'files'.")
    suffix = os.path.splitext(upload.filename or "")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        upload.save(tmp.name)
        return tmp.name
