import os,time,random,hashlib,shutil
from flask import (Blueprint,
                   request,
                   render_template_string,
                   url_for,
                   jsonify
                   )
from abstract_utilities import SingletonMeta
from werkzeug.utils import secure_filename
from abstract_pandas import (get_df,
                             safe_excel_save,
                             is_file)
from werkzeug.datastructures import FileStorage

class fileManager(metaclass=SingletonMeta):
    def __init__(self, allowed_extentions=None):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.allowed_extentions = allowed_extentions or {'ods','csv','xls','xlsx','xlsb'}        
class AbsManager(metaclass=SingletonMeta):
    def __init__(self, base_path=None):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.base_path = base_path or os.getcwd()
    def _make_dir(self, path):
        """ Create directory if it doesn't exist. """
        os.makedirs(path, exist_ok=True)
        return path

    # Basic directories
    def get_base_path(self):
        return self.base_path
    
    def get_converts_dir(self):
        return self._make_dir(os.path.join(self.get_base_path(), 'converts'))
    
    def get_users_dir(self):
        return self._make_dir(os.path.join(self.get_base_path(), 'users'))

    def get_uploads_dir(self):
        return self._make_dir(os.path.join(self.get_base_path(), 'uploads'))

    def get_downloads_dir(self):
        return self._make_dir(os.path.join(self.get_base_path(), 'downloads'))
    
    # User-specific directories
    def get_user_dir(self, user,sub_path=None):
        user_path = os.path.join(self.get_users_dir(), user)
        if sub_path:
            user_path = os.path.join(user_path,sub_path)
        return user_path
    def check_user_dir(self,user,sub_path=None):
        user_file_dir = self.get_user_dir(user,sub_path=sub_path)
        return os.path.isdir(user_file_dir)
    def make_user_dir(self,user,sub_path=None):
        self._make_dir(self.get_user_dir(user))
        return self._make_dir(self.get_user_dir(user,sub_path))
    def get_user_converts_dir(self, user):
        return self.make_user_dir(user, 'converts')

    def get_user_uploads_dir(self, user):
        return self.make_user_dir(user, 'uploads')

    def get_user_downloads_dir(self, user):
        return self.make_user_dir(user,  'downloads')

    def get_user_process_dir(self, user):
        return self.make_user_dir(user,'process')

    def get_user_saved_dir(self, user):
        return self.make_user_dir(user, 'saved')
    # File path generation (without creating directories)
    def get_file_path(self, directory, fileName):
        return os.path.join(directory, fileName)
def get_user_downloads_file_path(user,fileName):
    abs_manager = AbsManager()
    user_downloads_dir = abs_manager.get_user_downloads_dir(user)
    return abs_manager.get_file_path(user_downloads_dir, fileName)
def get_user_process_file_path(user,fileName):
    abs_manager = AbsManager()
    user_process_dir = abs_manager.get_user_process_dir(user)
    return abs_manager.get_file_path(user_process_dir, fileName)
def get_user_uploads_file_path(user,fileName):
    abs_manager = AbsManager()
    user_uploads_dir = abs_manager.get_user_uploads_dir(user)
    return abs_manager.get_file_path(user_uploads_dir, fileName)
def get_user_saved_file_path(user,fileName):
    abs_manager = AbsManager()
    user_saved_dir = abs_manager.get_user_saved_dir(user)
    return abs_manager.get_file_path(user_saved_dir, fileName)
def get_user_converts_file_path(user,fileName):
    abs_manager = AbsManager()
    user_converts_dir = abs_manager.get_user_converts_dir(user)
    return abs_manager.get_file_path(user_converts_dir, fileName)
def copy_to(path_1,path_2):
    if os.path.isfile(path_1):
        shutil.copy(path_1,path_2)
        print(f"copyd from {path_1}\n to {path_2}\n\n")
        return path_2
    print(f"not copyd from {path_1}\n to {path_2}\n\n")
    return False
def manual_move(path_1,path_2):
    try:
        if os.path.isfile(path_1):
            save_file(file=read_file(path_1),file_path=path_2)
        cleanup_files(path_1)
    except Exception as e:
       print(f"{e}")
       return False
    return path_2
def move_to(path_1,path_2):
    if os.path.isfile(path_1):
        try:
            shutil.move(path_1,path_2)
        except:
            return manual_move(path_1,path_2)
        print(f"moved from {path_1} to {path_2}\n\n")
        return path_2
    print(f"not moved from {path_1} to {path_2}\n\n")
    return False
def move_to_download(user,fileName,success=True,directory=None):
    process_file_path = get_user_process_file_path(user,fileName)
    downloads_file_path = get_user_downloads_file_path(user,fileName)
    if move_to(process_file_path,downloads_file_path) == False:
        return {'success': False, 'fileName': fileName, "user": user,"directory":"process"}
    return {'success': True, 'fileName': fileName, "user": user,"directory":"downloads"}
def move_to_process(user,fileName,success=True,directory=None):
    uploads_file_path = get_user_uploads_file_path(user,fileName)
    process_file_path = get_user_process_file_path(user,fileName)
    if move_to(uploads_file_path,process_file_path) == False:
        return {'success': False, 'fileName': fileName, "user": user,"directory":"uploads"}
    return {'success': True, 'fileName': fileName, "user": user,"directory":"process"}
def copy_to_saved(user,fileName,success=True,directory=None):
    downloads_file_path = get_user_downloads_file_path(user,fileName)
    saved_file_path = get_user_saved_file_path(user,fileName)
    if copy_to(downloads_file_path,saved_file_path) == False:
        return {'success': False, 'fileName': fileName, "user": user,"directory":"downloads"}
    return {'success': True, 'fileName': fileName, "user": user,"directory":"saved"}
def convert_file(file_path,converts_file_path):
    original_dirName = get_dirname(file_path)
    conv_file_name = get_file_name(converts_file_path)
    new_file_path = os.path.join(original_dirName,conv_file_name)
    moved = move_to(converts_file_path,new_file_path)
    if moved:
        cleanup_files(file_path)
        return moved
    return False
def is_storage(obj):
    """Check if an object is of type FileStorage."""
    return isinstance(obj, FileStorage)
def get_file_name(obj):
    if is_storage(obj):
        try:
            # Read the file directly from the file object
            file_name = secure_filename(obj.filename)
            return file_name
        except Exception as e:
            print(f"Failed to read file: {e}")
    if isinstance(obj,str) and (os.path.isfile(obj) or os.path.isdir(os.path.dirname(obj))):
         return os.path.basename(obj)
    return obj
def generate_custom_uid():
    """Generate a custom unique identifier."""
    timestamp = int(time.time() * 1000)  # Current time in milliseconds
    random_int = random.randint(0, 999999)  # Random integer
    raw_uid = f"{timestamp}-{random_int}"
    hash_uid = hashlib.sha256(raw_uid.encode()).hexdigest()
    return hash_uid[:16]  # Return the first 16 characters for a shorter UID
def insert_into_tail(file_path,string):
    dirName = os.path.dirname(file_path)
    baseName = os.path.basename(file_path)
    fileName,ext=os.path.splitext(baseName)
    newName = f"{fileName}_{string}{ext}"
    if dirName:
        newName = os.path.join(dirName,baseName)
    return newName
def get_unique_file_name(obj):
    dirname = get_dirname(obj)
    fileName= insert_into_tail(get_file_name(obj),generate_custom_uid())
    if dirname:
        return os.path.join(dirname,fileName)
    return fileName

def validate_user_and_filename(user, filename):
    """Validate presence of user and filename."""
    if not user or not filename:
        return jsonify({'error': True, 'message': "User or filename not specified"}), 400
    return None

def file_exists(file_path):
    """Check if a file exists at the specified path and return appropriate responses."""
    if not os.path.isfile(file_path):
        if os.path.isdir(os.path.dirname(file_path)):
            message = f'File {os.path.basename(file_path)} does not exist'
        else:
            message = 'User directory does not exist'
        return jsonify({'error': True, "message": message}), 400
    return None

def cleanup_files(*paths):
    """Remove files from the filesystem as a cleanup process."""
    for path in paths:
        if os.path.isfile(path):
            os.remove(path)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in fileManager().allowed_extentions

def read_file(file=None,file_path=None):
    if file and is_storage(file):
        return file.read()
    elif file_path and os.path.splitext(file_path)[-1][1:] in ['ods','csv','xls','xlsx','xlsb']:
         return get_df(file_path)
    else:
        return safe_read_from_json(file_path)


def save_file(file=None,file_path=None):
    if file and is_storage(file):
        file.save(file_path)
    elif file_path and os.path.splitext(file_path)[-1][1:] in ['ods','csv','xls','xlsx','xlsb']:
         safe_excel_save(get_df(file_path),file_path)
    else:
        write_to_file(contents=file,file_path=file_path)
def get_dirname(obj):
    if isinstance(obj,str) and (os.path.isfile(obj) or os.path.isdir(os.path.dirname(obj))):
        return os.path.dirname(obj)
def get_file_name(obj):
    """Get a safe filename from a file or string path."""
    if is_storage(obj):
        return secure_filename(obj.filename)
    if isinstance(obj, str) and (os.path.isfile(obj) or os.path.isdir(os.path.dirname(obj))):
        return os.path.basename(obj)
    return str(obj)


def get_path_from_result(user,fileName,success=True,directory=None):
    abs_manager = AbsManager()
    return os.path.join(abs_manager.make_user_dir(user,directory),fileName)
def save_to_directory(contents,user,fileName,success=True,directory=None):
    abs_manager = AbsManager()
    if (directory != 'process' and success != 'override') or (abs_manager.check_user_dir(user,directory) == False and success != 'override'):
        return {'success': False, 'fileName': fileName, "user": user,"directory":directory}
    
    safe_excel_save(get_df(contents),os.path.join(abs_manager.make_user_dir(user,directory),fileName))
    return {'success': True, 'fileName': fileName, "user": user,"directory":directory}

def upload_file(file, user=None):
    """Main file upload function to handle different types of files."""
    if file is None:
        return jsonify({'error': True, 'message': "No file uploaded"}), 400
    
        
    # Determine a safe filename
    filename = get_file_name(file)
    if not allowed_file(filename):
        return jsonify({'error': True, 'message': "File type not allowed"}), 400
    
    # Set a default user if not specified
    user = user or 'Default'
    
    # Generate a unique file name and the upload path
    unique_name = get_unique_file_name(filename)
    upload_file_path = get_user_uploads_file_path(user, unique_name)
    if is_file(file):
        copy_to(file,upload_file_path)
    else:
        # Save the file at the specified path
        save_file(file, upload_file_path)

    return {'success': True, 'fileName': unique_name, "user": user,"directory":"upload"}
def download_user_file(user=None,fileName=None):
    upload_file_path = get_user_uploads_file_path(user, fileName)
    download_file_path = get_user_downloads_file_path(user, fileName)
    processed_file_path = get_user_process_file_path(user, fileName)
    upload_file_veri = os.path.isfile(upload_file_path)
    processed_file_veri = os.path.isfile(processed_file_path)
    download_file_veri = os.path.isfile(download_file_path)
    if upload_file_veri and processed_file_veri:
        return jsonify({'error': True, "message": "still processing"}), 400
    if not upload_file_veri and processed_file_veri:
        return jsonify({'error': True, "message": "possibly still processing"}), 400
    if upload_file_veri and not processed_file_veri and not download_file_veri or not upload_file_veri and not processed_file_veri and not download_file_veri:
        return jsonify({'error': True, "message": "file will not exist"}), 500
def make_path_from_download(file_path, static_folder_path):
    """
    Convert an absolute file path to a URL using Flask's static route.
    Assumes that file_path is under the static folder.
    """
    relative_path = os.path.relpath(file_path, static_folder_path)
    # Build URL via Flask's static route. If your app is configured to serve static files
    # with a prefix (e.g. /joben/static), url_for will include that.
    return url_for('static', filename=relative_path)

def get_download_dir(download_dir):
    """
    Return the directory where videos are downloaded.
    You can customize this function as needed.
    """
    # For example, using the static folder under videos/downloads:
    os.makedirs(download_dir, exist_ok=True)
    return download_dir
