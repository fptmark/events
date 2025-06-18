# framework/contract.py

def expose_endpoint(method: str, route: str, summary: str = ""):
    def decorator(func):
        setattr(func, "_endpoint_metadata", {
            "method": method,
            "route": route,
            "summary": summary
        })
        return func
    return decorator

def expose_response(label: str = "", usage: str = "response"):
    def decorator(cls):
        setattr(cls, "_model_metadata", {
            "label": label,
            "usage": usage
        })
        return cls
    return decorator
