import os

from ecoapp import app


def run_debug_safe():
    """Single-process mode for stable VS Code debugging."""
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


def run_hot_reload_dev():
    """Hot-reload mode for fast local UI iteration during development.

    It first tries to run with livereload for template watching and quicker feedback.
    If livereload is unavailable or fails to start, execution falls back to Flask's
    built-in reloader so development can continue without additional tooling.
    """
    try:
        from livereload import Server

        app.debug = True
        server = Server(app.wsgi_app)
        server.watch("templates/**/*.html")
        server.serve(host="127.0.0.1", port=5000)
    except Exception:
        app.run(host="127.0.0.1", port=5000, debug=True)


if __name__ == "__main__":
    mode = os.getenv("APP_MODE", "dev").strip().lower()
    if mode == "debug":
        run_debug_safe()
    else:      
        run_hot_reload_dev()
