from __future__ import annotations

import click
from flask.cli import with_appcontext
from sqlalchemy import select

from contester.extensions import db
from contester.models.user import User, UserRole


def _get_user_by_username(username: str) -> User | None:
    statement = select(User).where(User.username == username)
    return db.session.scalar(statement)


def _get_user_by_email(email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return db.session.scalar(statement)


@click.command("create-admin")
@click.option("--username", prompt=True, help="Admin username.")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.option("--email", default=None, help="Admin email.")
@click.option("--full-name", default=None, help="Admin full name.")
@with_appcontext
def create_admin_command(
    username: str,
    password: str,
    email: str | None,
    full_name: str | None,
) -> None:
    normalized_email = email.strip().lower() if email else None

    if _get_user_by_username(username.strip()) is not None:
        raise click.ClickException(f"User with username {username!r} already exists.")

    if normalized_email and _get_user_by_email(normalized_email) is not None:
        raise click.ClickException(f"User with email {normalized_email!r} already exists.")

    admin = User.create(
        username=username,
        password=password,
        role=UserRole.ADMIN,
        email=normalized_email,
        full_name=full_name,
    )

    db.session.add(admin)
    db.session.commit()

    click.echo(f"Admin user {admin.username!r} created successfully.")