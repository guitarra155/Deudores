import ssl

def aplicar_parche_ssl():
    """Permite conexiones HTTPS en entornos con certificados SSL locales caducados."""
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context

def main_exception_handler(loop, context):
    """Silencia los errores de red residuales cuando Flet cierra sus sockets de golpe."""
    exception = context.get("exception")
    if isinstance(exception, (ConnectionResetError, OSError)) or \
            "connection_lost" in context.get("message", ""):
        return
    loop.default_exception_handler(context)
