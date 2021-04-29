def protector(foo):
    """
    function used as decorator to avoid the app to crash because of basic errors
    """
    def inner(*args, **kwargs):
        try:
            return foo(*args, **kwargs)
        except Exception as e:
            return e
    return inner
