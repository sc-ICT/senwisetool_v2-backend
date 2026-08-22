import asyncio
import subprocess
import sys

import click


@click.group()
def cli():
    """SWT Servey — Commandes de gestion du projet."""
    pass


# ─── SERVEUR ──────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--host", default="0.0.0.0", help="Adresse d'écoute")
@click.option("--port", default=5000, help="Port d'écoute")
@click.option("--reload", is_flag=True, default=True, help="Rechargement automatique")
def dev(host: str, port: int, reload: bool):
    """Lancer le serveur en mode développement."""
    click.echo(f"🚀 Serveur démarré sur http://{host}:{port}")
    cmd = ["uvicorn", "app.main:app", f"--host={host}", f"--port={port}"]
    if reload:
        cmd.append("--reload")
    subprocess.run(cmd)


@cli.command()
@click.option("--host", default="0.0.0.0", help="Adresse d'écoute")
@click.option("--port", default=5000, help="Port d'écoute")
@click.option("--workers", default=4, help="Nombre de workers")
def start(host: str, port: int, workers: int):
    """Lancer le serveur en mode production."""
    click.echo(f"🚀 Serveur production démarré sur http://{host}:{port}")
    subprocess.run(
        [
            "uvicorn",
            "app.main:app",
            f"--host={host}",
            f"--port={port}",
            f"--workers={workers}",
        ]
    )


# ─── BASE DE DONNÉES ──────────────────────────────────────────────────────────


@cli.command()
@click.argument("message")
def makemigration(message: str):
    """Générer une nouvelle migration. Ex: poetry run cli makemigration 'add users table'"""
    click.echo(f"📦 Génération de la migration : {message}")
    subprocess.run(["alembic", "revision", "--autogenerate", "-m", message])


@cli.command()
def migrate():
    """Appliquer toutes les migrations en attente."""
    click.echo("⬆️  Application des migrations...")
    result = subprocess.run(["alembic", "upgrade", "head"])
    if result.returncode == 0:
        click.echo("✅ Migrations appliquées avec succès")


@cli.command()
def currentmigration():
    """Voir la migration actuelle."""
    click.echo("⬆️  Migration actuelle...")
    subprocess.run(["alembic", "current"])


@cli.command()
@click.option("--steps", default=1, help="Nombre de migrations à annuler")
def rollback(steps: int):
    """Annuler les dernières migrations."""
    click.echo(f"⬇️  Annulation de {steps} migration(s)...")
    subprocess.run(["alembic", "downgrade", f"-{steps}"])


@cli.command()
def migration_status():
    """Voir l'état actuel des migrations."""
    subprocess.run(["alembic", "current"])
    subprocess.run(["alembic", "history", "--verbose"])


# ─── BASE DE DONNÉES (RESET) ──────────────────────────────────────────────────


@cli.command()
@click.confirmation_option(prompt="⚠️  Cela va supprimer TOUTES les données. Confirmer ?")
def reset_db():
    """Réinitialiser la base de données (supprime tout et recrée)."""
    click.echo("🗑️  Réinitialisation de la base de données...")
    subprocess.run(["alembic", "downgrade", "base"])
    subprocess.run(["alembic", "upgrade", "head"])
    click.echo("✅ Base de données réinitialisée")


# ─── TESTS ────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Affichage détaillé")
def test(verbose: bool):
    """Lancer les tests."""
    cmd = ["pytest"]
    if verbose:
        cmd.append("-v")
    subprocess.run(cmd)


# ─── INFORMATIONS ─────────────────────────────────────────────────────────────


@cli.command()
def info():
    """Afficher les informations de configuration."""
    from app.config import settings

    click.echo("\n📋 Configuration actuelle :")
    click.echo(f"  APP_NAME  : {settings.APP_NAME}")
    click.echo(f"  APP_ENV   : {settings.APP_ENV}")
    click.echo(f"  DB URL    : {settings.DATABASE_URL[:40]}...")
    click.echo(f"  Docs      : http://127.0.0.1:5000/docs\n")


if __name__ == "__main__":
    cli()


# poetry run cli dev                          # lancer le serveur en dev
# poetry run cli makemigration "init"        # créer une migration
# poetry run cli migrate                      # appliquer les migrations
# poetry run cli rollback                     # annuler la dernière migration
# poetry run cli reset_db                     # réinitialiser la base
# poetry run cli test                         # lancer les tests
# poetry run cli info                         # voir la configuration

# poetry run alembic init alembic
