import functools

from aiohttp import web


def template(env, template_name):
    def _decorator(func):
        @functools.wraps(func)
        async def _wrapper(*args, **kwargs):
            return web.Response(
                text=await env.get_template(template_name).render_async(
                    **func(*args, **kwargs)
                ),
                content_type="text/html",
            )

        return _wrapper

    return _decorator
