import shutil
from pathlib import Path
from typing import Callable, Optional, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from gtnh.assembler.downloader import get_asset_version_cache_location
from gtnh.assembler.generic_assembler import GenericAssembler
from gtnh.defs import MMC_PACK_JSON, RELEASE_MMC_DIR, Side
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import GTNHModInfo
from gtnh.modpack_manager import GTNHModpackManager


class MMCAssembler(GenericAssembler):
    def __init__(
        self,
        gtnh_modpack: GTNHModpackManager,
        release: GTNHRelease,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ):
        GenericAssembler.__init__(self, gtnh_modpack=gtnh_modpack, release=release, progress_callback=progress_callback)
        self.mmc_archive_root: Path = Path(f"GT New Horizons {self.release.version}")
        self.mmc_modpack_files: Path = self.mmc_archive_root / ".minecraft"
        self.mmc_modpack_mods: Path = self.mmc_modpack_files / "mods"

    def add_mods(
        self, side: Side, mods: list[tuple[GTNHModInfo, GTNHVersion]], archive: ZipFile, verbose: bool = False
    ) -> None:

        for mod, version in mods:
            source_file: Path = get_asset_version_cache_location(mod, version)
            self.update_progress(side, source_file, verbose=verbose)
            archive_path: Path = self.mmc_modpack_mods / source_file.name
            print(archive_path)
            archive.write(source_file, arcname=archive_path)

    def add_config(
        self, side: Side, config: Tuple[GTNHConfig, GTNHVersion], archive: ZipFile, verbose: bool = False
    ) -> None:
        modpack_config: GTNHConfig
        config_version: Optional[GTNHVersion]
        modpack_config, config_version = config

        config_file: Path = get_asset_version_cache_location(modpack_config, config_version)

        with ZipFile(config_file, "r", compression=ZIP_DEFLATED) as config_zip:
            self.update_progress(side, config_file, verbose=verbose)

            for item in config_zip.namelist():
                if item in self.exclusions[side]:
                    continue
                with config_zip.open(item) as config_item:
                    with archive.open(
                        str(self.mmc_modpack_files) + "/" + item, "w"
                    ) as target:  # can't use Path for the whole
                        # path here as it strips leading / but those are used by
                        # zipfile to know if it's a file or a folder. If used here,
                        # Path objects will lead to the creation of empty files for
                        # every folder.
                        shutil.copyfileobj(config_item, target)

    def get_archive_path(self, side: Side) -> Path:
        return RELEASE_MMC_DIR / f"GT New Horizons {self.release.version} (MMC).zip"

    def assemble(self, side: Side, verbose: bool = False) -> None:
        if side != Side.CLIENT:
            raise ValueError(f"Only valid side is {Side.CLIENT}, got {side}")

        GenericAssembler.assemble(self, side, verbose)

        if side == Side.CLIENT:
            self.add_mmc_meta_data(side)

    def add_mmc_meta_data(self, side: Side) -> None:
        """
        Method used to add additional meta data to the mmc archive.

        :param side: client side
        :return: None
        """

        with ZipFile(self.get_archive_path(side), "a") as archive:
            archive.writestr(str(self.mmc_archive_root) + "/mmc-pack.json", MMC_PACK_JSON)
