from pathlib import Path
from typing import Optional, Callable

from gtnh.assembler.generic_assembler import GenericAssembler
from gtnh.defs import RELEASE_MODRINTH_DIR, Side
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.modpack_manager import GTNHModpackManager


class ModrinthAssembler(GenericAssembler):
    """
    Modrinth assembler class. Allows for the assembling of modrinth archives.
    """
    def __init__(
        self,
        gtnh_modpack: GTNHModpackManager,
        release: GTNHRelease,
        task_progress_callback: Optional[Callable[[float, str], None]] = None,
        global_progress_callback: Optional[Callable[[float, str], None]] = None,
    ):
        """
        Constructor of the ModrinthAssembler class.

        :param gtnh_modpack: the modpack manager instance
        :param release: the target release object
        :param task_progress_callback: the callback to report the progress of the task
        :param global_progress_callback: the callback to report the global progress
        """
        GenericAssembler.__init__(
            self,
            gtnh_modpack=gtnh_modpack,
            release=release,
            task_progress_callback=task_progress_callback,
            global_progress_callback=global_progress_callback,
        )

    def get_archive_path(self, side: Side) -> Path:
        return RELEASE_MODRINTH_DIR / f"GTNewHorizons-{side}-{self.release.version}.zip"
