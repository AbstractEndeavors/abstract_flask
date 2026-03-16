def get_blueprints_from_routes(url_prefix=None):
    bps = {}
    for name, obj in vars(routes).items():
        
        if name.endswith("_bp"):           # match your naming convention
            if isinstance(obj, Blueprint): # ensure it's actually a Blueprint
                if url_prefix:
                    obj = (obj,f"/{url_prefix}/")
                bps[name] = obj
    return list(bps.values())
