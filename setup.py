\import setuptools,glob,os
def make_list(obj:any) -> list:
    if isinstance(obj, list):
        return obj
    return [obj]
def read_from_file(file_path) -> str:
    with open(file_path, 'r', encoding='UTF-8') as f:
        return f.read()
def get_abs_path():
    return os.path.abspath(__name__)
def get_abs_dir():
    return os.path.dirname(get_abs_path())
def get_readme_file_paths(abs_dir=None):
    abs_dir = abs_dir or get_abs_dir()
    if os.path.isfile(abs_dir):
        abs_dir = os.path.dirname(abs_dir)

    pattern = os.path.join(abs_dir, '**', f'README.md')
    readme_file_paths = make_list(glob.glob(pattern, recursive=True) or '')
    return readme_file_paths
def get_readme_path(abs_path=None):
    readme_file_paths = get_readme_file_paths(abs_path)
    for readme_file_path in readme_file_paths:
        if os.path.isfile(readme_file_path):
            return readme_file_path
def get_readme_data(readme_file_path=None,abs_path=None):
    readme_file_path = readme_file_path or get_readme_path(abs_path)
    long_description = ''
    if os.path.isfile(readme_file_path):
        long_description = read_from_file(readme_file_path)
    return long_description
setuptools.setup(
    name='abstract_flask',
    version='0.0.0.23',
    author='putkoff',
    author_email='partners@abstractendeavors.com',
    description='Abstract Flask is an application development module in Python, offering utilities and classes for efficient handling of files, directories, and Flask requests.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/AbstractEndeavors/abstract_flask',
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    classifiers=['Development Status :: 3 - Alpha', 'Intended Audience :: Developers', 'License :: OSI Approved :: MIT License', 'Programming Language :: Python :: 3', 'Programming Language :: Python :: 3.11'],
    install_requires=['werkzeug', 'abstract_utilities', 'flask_cors', 'abstract_pandas', 'flask'],
    python_requires='>=3.6',
    setup_requires=['wheel'],
)