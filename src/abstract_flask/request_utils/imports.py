import inspect
from flask import jsonify
from ..imports import (
    json,
    get_only_kwargs,
    get_desired_key_values,
    makeParams,
    dump_if_json,
    make_list
    )
from typing import *
from flask import Request
import inspect
from abstract_queries import UserIPManager,UserManager
