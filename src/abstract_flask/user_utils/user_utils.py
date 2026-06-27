from .imports import get_request_info

def get_user_name(req=None,user_name=None):
    return get_request_info(req=req,
                         obj=user_name,
                         res_type='user')

