import nox

# Todas las sesiones usarán el entorno de Poetry
nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["lint", "tests"]


@nox.session
def lint(session):
    session.run("poetry", "install", external=True)
    session.run("poetry", "run", "black", "--check", "src", external=True)
    session.run("poetry", "run", "isort", "--check-only", "src", external=True)
    session.run("poetry", "run", "flake8", "src", external=True)


@nox.session
def tests(session):
    session.run("poetry", "install", external=True)
    session.run("poetry", "run", "pytest", "--cov=src", external=True)


@nox.session
def format(session):
    session.run("poetry", "install", external=True)
    session.run("poetry", "run", "black", "src", external=True)
    session.run("poetry", "run", "isort", "src", external=True)


@nox.session
def typecheck(session):
    session.run("poetry", "install", external=True)
    session.run("poetry", "run", "mypy", "src", "tests", external=True)