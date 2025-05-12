# Abstract Flask v0.0.0.23

## Description
Abstract Flask is a Python module developed to streamline application development in Flask. Its comprehensive set of singleton classes and utility methods help manage files, directories, and Flask requests, making it easier to create secure and efficient network applications. 

## Features
- Singleton classes for file and directory management.
- Utility methods to handle incoming Flask requests, including argument extraction, key matching, error handling, and JSON conversion.
- Methods for file and directory management.


### internal Scripts Overview


-`network_tools`
src/abstract_flask/network_tools.py
network_tools.py in the abstract_flask package is a Python script designed to determine the host's IP address. The function "get_host_ip" attempts to connect to an Internet host to discover the local IP. If it cannot connect to a specified public DNS server, it defaults to the local host IP ("127.0.0.1"). The script leverages Python's socket library to create a socket object, set its timeout, and establish a connection to retrieve the IP address. The object is closed after the IP address is retrieved to free up resources. If an error occurs during this process, the function will print the error and return the localhost IP. This script is instrumental in finding out the IP address of the host machine, which in turn could be crucial in web development settings or network-related operations within the abstract_flask package.



-`file_utils`
src/abstract_flask/file_utils.py
file_utils.py is a Python script, part of the abstract_flask v0.0.0.23 package. The script features a SingletonMeta metaclass and two Python singleton classes, fileManager and AbsManager, for managing files and directories. fileManager class is concerned with managing file extensions, while AbsManager handles various directory tasks. Using the SingletonMeta, these classes ensure that a single instance is initialized and can be reused without creating multiple instances. The fileManager class has an attribute "allowed_extentions" used for managing allowed file extensions. The AbsManager class has initialization and methods for creating and accessing various directories, both general ones (such as converts, users, uploads, downloads) and user-specific ones (such as uploads, downloads, processes, converts for each user). There are also methods to check and create directories if they do not exist. This Python script, in conjunction with others, assists in providing useful routines and utilities in file and directory management for developing flask applications.



-`abstract_flask`
src/abstract_flask/abstract_flask.py
abstract_flask.py is a Python script in the abstract_flask v0.0.0.23 package. It includes several functionalities, starting with important imports such as the flask library, which help streamline the development of web applications. The script features various utility functions for handling flask request, among them, parsing incoming flask requests, extracting arguments and keyword arguments, case-insensitive matching of keys, handling required keys, and error handling. The script operates by defining functions that manage flask Blueprint creation and a specific function (execute_request) that facilitates secure and error-handled execution of requests. Other functions in the script deal with JSON conversion, matching and filtering of keyword arguments and error generation. In summary, abstract_flask.py is a crucial part of the abstract_flask package that provides crucial utility functions for the handling of flask-based requests and responses including JSON conversion, argument extraction and validation, and error handling.


## Installation
```python
pip install abstract_flask
```

## Usage
```python
from abstract_flask import *
```

## Dependencies
Abstract Flask requires:
- flask

## License
This project is licensed under the MIT License.

## Author
Created by putkoff, partners@abstractendeavors.com.

## Contributing
Feel free to fork this repository and make improvements. When ready, submit a pull request.
