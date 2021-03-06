from django.core.cache import caches


def _make_cache_key_from_function(fn, *args, **kwargs):
    return '%s.%s(%s,%s)' % (
        fn.__module__,
        fn.__name__,
        '(args:%s)' % ','.join(map(str, map(hash, args))),
        '(kwargs:%s)' % ','.join(map(str, map(hash, kwargs.items()))),
    )


def cache_page_per_user(fn, *args, **kwargs):
    def key(request, *args, **kwargs):
        return (_make_cache_key_from_function(fn, *args, **kwargs) +
                'querystring(%s),user(pk=%s,username=%s)' % (
                    request.META['QUERY_STRING'] or '',
                    request.user.pk
                    if request.user.is_authenticated()
                    else 'None', request.user.username))

    return cache(fn, key)


def cache_model_method(fn):
    def key(self, *args, **kwargs):
        if self.pk is None:
            return None
        return (_make_cache_key_from_function(fn, *args, **kwargs) +
                '%s(pk=%s)' % (type(self).__name__, self.pk))
    return cache(fn, key)


def cache(fn=None, key=None):
    django_cache = caches['default']

    if fn is None:
        return lambda fn: cache(fn=fn, key=key)

    def inner(*args, **kwargs):
        if key is None:
            cache_key = _make_cache_key_from_function(fn, *args, **kwargs)
        elif hasattr(key, '__call__'):
            cache_key = key(*args, **kwargs)
        else:
            cache_key = str(key)
        if cache_key is None:
            return fn(*args, **kwargs)
        cached = django_cache.get(cache_key)
        if cached is not None:
            return cached
        result = fn(*args, **kwargs)
        django_cache.set(cache_key, result)
        return result
    return inner
