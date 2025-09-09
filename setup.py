from time import time
import setuptools
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
setuptools.setup(
    name='abstract_flask',
    version='0.0.0.952',
    author='putkoff',
    author_email='partners@abstractendeavors.com',
    description="Utilities for building Flask apps faster: structured request parsing, safe argument extraction, user/IP introspection, logging helpers, and light-weight file/directory utilities — all packaged as small, composable modules.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/AbstractEndeavors/abstract_flask",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
    ],
    install_requires=['abstract_pandas' , 'abstract_queries' , 'abstract_security' ,
                      'abstract_utilities' , 'flask' , 'flask_cors' ,'werkzeug'],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    # Add this line to include wheel format in your distribution
    setup_requires=['wheel'],
)
