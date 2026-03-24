"""Click-based CLI entry point for ytcli."""

import click

from ytcli import __version__
from ytcli.core.output import success, error, progress

# Import command groups
from ytcli.commands.download import download, audio, transcript, thumbnail, metadata
from ytcli.commands.channel import scan, channels, videos, search, refresh
from ytcli.commands.analytics import auth, stats, performance, top, comments
from ytcli.commands.compete import compare, gaps, hooks, calendar, niche
from ytcli.commands.create import ideas, titles, tags, batch_audio, export


@click.group()
@click.version_option(version=__version__)
@click.option("--data-dir", envvar="YTCLI_DATA_DIR", help="Data directory (default: ~/.ytcli)")
@click.pass_context
def cli(ctx, data_dir):
    """YouTube CLI for AI agents and creators."""
    ctx.ensure_object(dict)
    ctx.obj["data_dir"] = data_dir


# --- Meta commands ---


@cli.command()
@click.option("--dir", "data_dir_override", default=None, help="Override data directory path.")
@click.pass_context
def init(ctx, data_dir_override):
    """Create data directory and database."""
    from ytcli.core.db import init_db

    data_dir = data_dir_override or ctx.obj.get("data_dir")
    try:
        db_path = init_db(data_dir)
        success("init", {"db_path": str(db_path), "data_dir": str(db_path.parent)})
    except Exception as e:
        error("init", str(e))
        raise SystemExit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show tracked channels, video count, DB size."""
    from ytcli.core.db import get_connection, get_stats

    data_dir = ctx.obj.get("data_dir")
    try:
        conn = get_connection(data_dir)
        result = get_stats(conn)
        conn.close()
        success("status", result)
    except Exception as e:
        error("status", str(e))
        raise SystemExit(1)


@cli.command()
@click.argument("key")
@click.argument("value", required=False)
@click.pass_context
def config(ctx, key, value):
    """Get or set a config value. If VALUE provided, sets it. Otherwise, gets it."""
    from ytcli.core.db import get_connection, get_config, set_config

    data_dir = ctx.obj.get("data_dir")
    try:
        conn = get_connection(data_dir)
        if value is not None:
            set_config(conn, key, value)
            success("config", {"key": key, "value": value, "action": "set"})
        else:
            result = get_config(conn, key)
            success("config", {"key": key, "value": result, "action": "get"})
        conn.close()
    except Exception as e:
        error("config", str(e))
        raise SystemExit(1)


@cli.command()
@click.option("--port", default=8888, type=int, help="Port for dashboard server.")
@click.pass_context
def serve(ctx, port):
    """Launch localhost dashboard."""
    progress("Dashboard not yet implemented")
    raise SystemExit(1)


# --- Tier 1: Download & Extract ---
cli.add_command(download)
cli.add_command(audio)
cli.add_command(transcript)
cli.add_command(thumbnail)
cli.add_command(metadata)

# --- Tier 2: Channel Intelligence ---
cli.add_command(scan)
cli.add_command(channels)
cli.add_command(videos)
cli.add_command(search)
cli.add_command(refresh)

# --- Tier 3: Analytics ---
cli.add_command(auth)
cli.add_command(stats)
cli.add_command(performance)
cli.add_command(top)
cli.add_command(comments)

# --- Tier 4: Competitive Analysis ---
cli.add_command(compare)
cli.add_command(gaps)
cli.add_command(hooks)
cli.add_command(calendar)
cli.add_command(niche)

# --- Tier 5: Creation Assist ---
cli.add_command(ideas)
cli.add_command(titles)
cli.add_command(tags)
cli.add_command(batch_audio)
cli.add_command(export)


def main():
    cli()


if __name__ == "__main__":
    main()
