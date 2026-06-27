import os,time,random,hashlib,shutil,tempfile,base64,os,json
from flask import (Blueprint,
                   request,
                   render_template_string,
                   url_for,
                   jsonify
                   )
from ..imports import SingletonMeta

try:
  from abstract_pandas import get_df, safe_excel_save     # heavy: pandas/geopandas/odf
except Exception:
  def _needs_data(*a, **k):
      raise RuntimeError(
          "This file/Excel feature needs abstract_pandas (pandas/geopandas). "
          "Install it with: pip install abstract_flask[data]"
      )
  get_df = safe_excel_save = _needs_data
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

