from invoke import task


@task
def install(ctx):
    ctx.run("uv sync", pty=True)


@task
def migrate(ctx):
    ctx.run("uv run python manage.py migrate", pty=True)


@task
def makemigrations(ctx):
    ctx.run("uv run python manage.py makemigrations", pty=True)


@task
def collectstatic(ctx):
    ctx.run("uv run python manage.py collectstatic --noinput", pty=True)


@task
def test(ctx):
    ctx.run("uv run pytest", pty=True)


@task
def runserver(ctx, host="127.0.0.1", port=8000):
    ctx.run(f"uv run python manage.py runserver {host}:{port}", pty=True)


@task
def gunicorn(ctx, bind="0.0.0.0:8000"):
    ctx.run(f"uv run gunicorn wifi_portal.wsgi:application --bind {bind}", pty=True)
