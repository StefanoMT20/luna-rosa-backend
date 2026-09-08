from rest_framework.authentication import TokenAuthentication


class BearerTokenAuthentication(TokenAuthentication):
    """Igual que TokenAuthentication pero acepta 'Authorization: Bearer <token>'.

    DRF usa el keyword 'Token' por defecto; el front manda 'Bearer', y sin esto
    el header se ignora y toda ruta protegida responde 401.
    """

    keyword = "Bearer"
