import click
from structlog import get_logger

from gtnh.assembler.downloader import download_release
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


@click.command()
@click.argument("release-name")
def do_download_release(release_name: str) -> None:
    m = GTNHModpackManager()
    release = m.get_release(release_name)
    if release:
        download_release(mod_manager=m, release=release)


if __name__ == "__main__":
    do_download_release()
