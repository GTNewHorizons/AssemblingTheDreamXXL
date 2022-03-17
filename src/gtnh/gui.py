import os
import tkinter as tk
from pathlib import Path
from shutil import copy, rmtree
from tkinter.messagebox import showerror, showinfo, showwarning
from tkinter.ttk import Progressbar
from typing import Any, Callable, List, Optional, Tuple
from zipfile import ZipFile

import pydantic
import requests
from github import Github
from github.Organization import Organization

from gtnh.add_mod import get_repo, new_mod_from_repo
from gtnh.exceptions import LatestReleaseNotFound, PackingInterruptException, RepoNotFoundException
from gtnh.mod_info import GTNHModpack, ModInfo
from gtnh.pack_downloader import download_mod, ensure_cache_dir
from gtnh.utils import get_latest_release, get_token, load_gtnh_manifest, save_gtnh_manifest


def download_mods(
    gtnh_modpack: GTNHModpack,
    github: Github,
    organization: Organization,
    callback: Optional[Callable[[float, str], None]] = None,
) -> Tuple[List[Path], List[Path]]:
    """
    method to download all the mods required for the pack.

    :param gtnh_modpack: GTNHModpack object. Represents the metadata of the modpack.
    :param github: Github object.
    :param organization: Organization object. Represent the GTNH organization.
    :param callback: Callable that takes a float and a string in parameters. (mainly the method to update the
                progress bar that takes a progress step per call and the label used to display infos to the user)
    :return: a list holding all the paths to the clientside mods and a list holding all the paths to the serverside
            mod.
    """
    # computation of the progress per mod for the progressbar
    delta_progress = 100 / len(gtnh_modpack.github_mods)

    # lists holding the paths to the mods
    client_paths = []
    server_paths = []

    # download of the mods
    for mod in gtnh_modpack.github_mods:
        if callback is not None:
            callback(delta_progress, f"downloading mods. current mod: {mod.name} Progress: {{0}}%")

        # do the actual work
        paths = download_mod(github, organization, mod)
        if mod.side == "BOTH":
            client_paths.extend(paths)
            server_paths.extend(paths)
        elif mod.side == "CLIENT":
            client_paths.extend(paths)
        elif mod.side == "SERVER":
            server_paths.extend(paths)

    # todo: make a similar thing for the curse mods

    return client_paths, server_paths


def pack_clientpack(client_paths: List[Path], pack_version: str, callback: Optional[Callable[[float, str], None]] = None) -> None:
    """
    Method used to pack all the client files into a client archive.

    :param client_paths: a list containing all the Path objects refering to the files needed client side.
    :param pack_version: the version of the pack.
    :param callback: Callable that takes a float and a string in parameters. (mainly the method to update the
            progress bar that takes a progress step per call and the label used to display infos to the user)
    :return: None
    """

    # computation of the progress per mod for the progressbar
    delta_progress = 100 / len(client_paths)

    # remembering the cwd because it'll be changed during the zip operation
    cwd = os.getcwd()
    cache_dir = Path(ensure_cache_dir())
    os.chdir(cache_dir)

    # archive name
    archive_name = f"client-{pack_version}.zip"

    # deleting any previous client archive
    if os.path.exists(archive_name):
        os.remove(archive_name)
        print("previous client archive deleted")

    print("zipping client archive")
    # zipping the files in the archive
    with ZipFile(archive_name, "w") as client_archive:
        for mod_path in client_paths:
            if callback is not None:
                callback(delta_progress, f"Packing client archive version {pack_version}: {mod_path.name}. Progress: {{0}}%")

            # writing the file in the zip
            client_archive.write(mod_path, mod_path.relative_to(cache_dir / "client_archive"))

    print("success!")

    # restoring the cwd
    os.chdir(cwd)


def pack_serverpack(server_paths: List[Path], pack_version: str, callback: Optional[Callable[[float, str], None]] = None) -> None:
    """
    Method used to pack all the server files into a client archive.

    :param server_paths: a list containing all the Path objects refering to the files needed server side.
    :param pack_version: the version of the pack.
    :param callback: Callable that takes a float and a string in parameters. (mainly the method to update the
            progress bar that takes a progress step per call and the label used to display infos to the user)
    :return: None
    """

    # computation of the progress per mod for the progressbar
    delta_progress = 100 / len(server_paths)

    # remembering the cwd because it'll be changed during the zip operation
    cwd = os.getcwd()
    cache_dir = Path(ensure_cache_dir())
    os.chdir(cache_dir)

    # archive name
    archive_name = f"server-{pack_version}.zip"

    # deleting any previous client archive
    if os.path.exists(archive_name):
        os.remove(archive_name)
        print("previous server archive deleted")

    print("zipping client archive")
    # zipping the files in the archive
    with ZipFile(archive_name, "w") as server_archive:
        for mod_path in server_paths:
            if callback is not None:
                callback(delta_progress, f"Packing server archive version {pack_version}: {mod_path.name}. Progress: {{0}}%")

            # writing the file in the zip
            server_archive.write(mod_path, mod_path.relative_to(cache_dir / "server_archive"))

    print("success!")

    # restoring the cwd
    os.chdir(cwd)


def download_pack_archive() -> Path:
    """
    Method used to download the latest gtnh modpack archive.

    :return: the path of the downloaded archive. None is returned if somehow it wasn't able to download any release.
    """
    gtnh_modpack_repo = get_repo("GT-New-Horizons-Modpack")

    gtnh_archive_release = get_latest_release(gtnh_modpack_repo)
    print("***********************************************************")
    print(f"Downloading {'GT-New-Horizons-Modpack'}:{gtnh_archive_release.title}")

    if not gtnh_archive_release:
        print(f"*** No release found for {'GT-New-Horizons-Modpack'}:{gtnh_archive_release.title}")
        raise LatestReleaseNotFound

    release_assets = gtnh_archive_release.get_assets()
    for asset in release_assets:
        if not asset.name.endswith(".zip"):
            continue

        print(f"Found Release at {asset.browser_download_url}")
        cache_dir = ensure_cache_dir()
        gtnh_archive_path = cache_dir / asset.name

        if os.path.exists(gtnh_archive_path):
            print(f"Skipping re-redownload of {asset.name}")
            continue

        print(f"Downloading {asset.name} to {gtnh_archive_path}")

        headers = {"Authorization": f"token {get_token()}", "Accept": "application/octet-stream"}

        with requests.get(asset.url, stream=True, headers=headers) as r:
            r.raise_for_status()
            with open(gtnh_archive_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print("Download successful")
    return gtnh_archive_path


def copy_file_to_folder(path_list: List[Path], source_root: Path, destination_root: Path) -> None:
    """
    Function used to move files from the source folder to the destination folder, while keeping the relative path.

    :param path_list: the list of files to move.
    :param source_root: the root folder of the files to move. It is assumed that path_list has files comming from the
                        same root folder.
    :param destination_root: the root folder for the destination.
    :return: None
    """
    for file in path_list:
        dst = destination_root / file.relative_to(source_root)
        if not dst.parent.is_dir():
            os.makedirs(dst.parent)
        copy(file, dst)


def crawl(path: Path) -> List[Path]:
    """
    Function that will recursively list all the files of a folder.

    :param path: The folder to scan
    :return: The list of all the files contained in that folder
    """
    files = [x for x in path.iterdir() if x.is_file()]
    for folder in [x for x in path.iterdir() if x.is_dir()]:
        files.extend(crawl(folder))
    return files


def move_mods(client_paths: List[Path], server_paths: List[Path]) -> None:
    """
    Method used to move the mods in their correct archive folder after they have been downloaded.

    :param client_paths: the paths for the mods clientside
    :param server_paths: the paths for the mods serverside
    :return: None
    """
    client_folder = Path(__file__).parent / "cache" / "client_archive"
    server_folder = Path(__file__).parent / "cache" / "server_archive"
    source_root = Path(__file__).parent / "cache"

    if client_folder.exists():
        rmtree(client_folder)
        os.makedirs(client_folder)

    if server_folder.exists():
        rmtree(server_folder)
        os.makedirs(server_folder)

    copy_file_to_folder(client_paths, source_root, client_folder)
    copy_file_to_folder(server_paths, source_root, server_folder)


def handle_pack_extra_files() -> None:
    """
    Method used to handle all the files needed by the pack like the configs or the scripts.

    :return: None
    """

    # download the gtnh modpack archive
    # catch is overkill but we never know
    try:
        gtnh_archive_path = download_pack_archive()
    except LatestReleaseNotFound:
        showerror("release not found", "The gtnh modpack repo has no release. Aborting.")
        raise PackingInterruptException

    # prepare for the temp dir receiving the unzip of the archive
    temp_dir = Path(gtnh_archive_path.parent / "temp")
    if temp_dir.exists():
        rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    # unzip
    with ZipFile(gtnh_archive_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)
    print("unzipped the pack")

    # load gtnh metadata
    gtnh_metadata = load_gtnh_manifest()

    # path for the prepared archives
    client_folder = Path(__file__).parent / "cache" / "client_archive"
    server_folder = Path(__file__).parent / "cache" / "server_archive"

    # exclusion lists
    client_exclusions = [temp_dir / exclusion for exclusion in gtnh_metadata.client_exclusions]
    server_exclusions = [temp_dir / exclusion for exclusion in gtnh_metadata.server_exclusions]

    # listing of all the files for the archive
    availiable_files = set(crawl(temp_dir))
    client_files = list(availiable_files - set(client_exclusions))
    server_files = list(availiable_files - set(server_exclusions))

    # moving the files where they must go
    print("moving files for the client archive")
    copy_file_to_folder(client_files, temp_dir, client_folder)
    print("moving files for the server archive")
    copy_file_to_folder(server_files, temp_dir, server_folder)
    print("success")


class MainFrame(tk.Tk):
    """
    Main windows of DreamAssemblerXXL. Lets you select what you want to do with it via the buttons. Each button spawns
    a new window allowing you to do the selected task(s).
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Constructor of the MainFrame class.

        :return: None
        """
        tk.Tk.__init__(self, *args, **kwargs)
        self.title("DreamAssemblerXXL")

        # setting up a gtnh metadata instance
        self.gtnh_modpack = load_gtnh_manifest()

        # setting up the icon of the window
        imgicon = tk.PhotoImage(file=Path(__file__).parent / "icon.png")
        # getattr hack to please mypy instead of self._w
        self.tk.call("wm", "iconphoto", getattr(self, "_w"), imgicon)

        # widgets in the window
        self.repo_popup: AddRepoFrame = AddRepoFrame(self)
        self.archive_popup: ArchiveFrame = ArchiveFrame(self)
        self.exclusion_popup: HandleFileExclusionFrame = HandleFileExclusionFrame(self)
        self.dependencies_popup: HandleDepUpdateFrame = HandleDepUpdateFrame(self)
        self.curse_popup: AddCurseModFrame = AddCurseModFrame(self)

        # grid manager
        self.repo_popup.grid(row=0, column=0, sticky="WE")
        self.archive_popup.grid(row=0, column=1, sticky="WENS")
        self.curse_popup.grid(row=0, column=2, sticky="WE")
        self.exclusion_popup.grid(row=1, column=0, columnspan=2, sticky="WE")
        self.dependencies_popup.grid(row=1, column=1, sticky="WE")

    def handle_dependencies_update(self) -> None:
        """
        Opens a new HandleDepUpdateFrame popup window. While this window is still open, the main window can't spawn a
        new one of this type.

        :return: None
        """
        pass


class BaseFrame(tk.LabelFrame):
    """
    Base popup class.
    """

    def __init__(self, root: MainFrame, popup_name: str = "DreamAssemblerXXL", *args: Any, **kwargs: Any) -> None:
        """
        Constructor of the BaseFrame class.

        :param root: the MainFrame widget.
        :param popup_name: Name of the popup window
        :param window_width: width in pixel of the window by default
        :param window_height: height in pixel of the window by default
        :param enforce_window_size: activate windows size setup or not
        :param args:
        :param kwargs:
        :return: None
        """
        tk.LabelFrame.__init__(self, root, text=popup_name, *args, **kwargs)
        self.root = root

    def reload_gtnh_metadata(self) -> None:
        """
        Method to reload the metadata from disk.

        :return: None
        """
        self.root.gtnh_modpack = load_gtnh_manifest()
        print("metadata loaded!")

    def save_gtnh_metadata(self) -> None:
        """
        Method to save the metadata to disk.

        :return: None
        """
        save_gtnh_manifest(self.root.gtnh_modpack)
        print("metadata saved!")


class AddRepoFrame(BaseFrame):
    """
    Frame allowing you to manage repositories in the github list contained in DreamAssemblerXXL.
    When adding a new Repository, the following things can happen:
    - Will raise you a tkinter error messagebox when the repository is not found.
    - Will raise you a tkinter warning messagebox when the repository is already added.
    - Will raise you a tkinter info messagebox when the repository is successfully added to the list.
    """

    def __init__(self, root: MainFrame) -> None:
        """
        Constructor of the AddRepoFrame class.

        :param root: the MainFrame instance
        :return: None
        """
        BaseFrame.__init__(self, root, popup_name="Repository adder")

        # widgets in the window
        self.custom_frame = CustomLabelFrame(self, self.get_repos(), False, add_callback=self.validate_callback)

        # grid manager
        self.custom_frame.grid(row=0, column=0)

        # state control vars
        self.is_messagebox_open = False

    def get_repos(self) -> List[str]:
        return [repo.name for repo in self.root.gtnh_modpack.github_mods]

    def validate_callback(self, repo_name: str) -> bool:
        """
        Method executed when self.btn_validate is pressed by the user.

        :return: if the repo was added or not.
        """
        repo_added = False

        # if no messagebox had been opened
        if not self.is_messagebox_open:
            self.is_messagebox_open = True

            # checking the repo on github
            try:
                new_repo = get_repo(repo_name)

            # let the user know that the repository doesn't exist
            except RepoNotFoundException:
                showerror("repository not found", f"the repository {repo_name} was not found on github.")

            else:
                # let the user know that the repository is already added
                if self.root.gtnh_modpack.has_github_mod(new_repo.name):
                    showwarning("repository already added", f"the repository {repo_name} is already added.")

                # adding the repo
                else:
                    try:
                        new_mod = new_mod_from_repo(new_repo)
                        self.root.gtnh_modpack.github_mods.append(new_mod)
                        self.root.gtnh_modpack.github_mods.sort()
                        self.save_gtnh_metadata()
                        showinfo("repository added successfully", f"the repo {repo_name} was added successfully!")
                        repo_added = True

                    # let the user know that the repository has no release, therefore it won't be added to the list
                    except LatestReleaseNotFound:
                        showerror("no release availiable on the repository", f"the repository {repo_name} has no release, aborting")

            # releasing the blocking
            self.is_messagebox_open = False
        return repo_added


class AddCurseModFrame(BaseFrame):
    """
    Frame allowing you to add a curse mod in the metadata.
    """

    def __init__(self, root:MainFrame) -> None:
        BaseFrame.__init__(self, root, popup_name="Curse mods management")

        #widgets
        self.label_name = tk.Label(self, text="mod name")
        self.label_page_url = tk.Label(self, text="project url")
        self.label_license = tk.Label(self, text="license")
        self.label_version = tk.Label(self, text="mod version")
        self.label_browser_url = tk.Label(self, text="url of the download page")
        self.label_download_url = tk.Label(self, text="direct download url of the mod file")
        self.label_release_date = tk.Label(self, text="release date")
        self.label_file_name = tk.Label(self, text="file name")
        self.label_maven_url = tk.Label(self, text="maven url")

        self.sv_name = tk.StringVar(self)
        self.sv_page_url = tk.StringVar(self)
        self.sv_license = tk.StringVar(self)
        self.sv_version = tk.StringVar(self)
        self.sv_browser_url = tk.StringVar(self)
        self.sv_download_url = tk.StringVar(self)
        self.sv_release_date = tk.StringVar(self)
        self.sv_file_name = tk.StringVar(self)
        self.sv_maven_url = tk.StringVar(self)

        self.entry_name = tk.Entry(self, textvariable=self.sv_name)
        self.entry_page_url = tk.Entry(self, textvariable=self.sv_page_url)
        self.entry_license = tk.Entry(self, textvariable=self.sv_license)
        self.entry_version = tk.Entry(self, textvariable=self.sv_version)
        self.entry_browser_url = tk.Entry(self, textvariable=self.sv_browser_url)
        self.entry_download_url = tk.Entry(self, textvariable=self.sv_download_url)
        self.entry_release_date = tk.Entry(self, textvariable=self.sv_release_date)
        self.entry_file_name = tk.Entry(self, textvariable=self.sv_file_name)
        self.entry_maven_url = tk.Entry(self, textvariable=self.sv_maven_url)

        self.custom_label_frame = CustomLabelFrame(self, [x.name for x in self.root.gtnh_modpack.external_mods], False, add_callback=self.add_callback, delete_callback=self.delete_callback)

        #dirty hack to reshape the custom label frame without making a new class
        self.custom_label_frame.listbox.configure(height=20)
        self.custom_label_frame.btn_add.grid_forget()
        self.custom_label_frame.btn_remove.grid_forget()
        self.custom_label_frame.btn_remove.grid(row=3, column=0, columnspan=2, sticky="WE")
        self.custom_label_frame.listbox.bind('<<ListboxSelect>>', self.fill_fields)

        self.btn_add = tk.Button(self, text="add/update", command=self.add)

        #grid manager
        self.custom_label_frame.grid(row=0, column=0, rowspan=19, sticky="NS")
        self.label_name.grid(row=0, column=1, sticky="WE")
        self.entry_name.grid(row=1, column=1, sticky="WE")
        self.label_page_url.grid(row=2, column=1, sticky="WE")
        self.entry_page_url.grid(row=3, column=1, sticky="WE")
        self.label_license.grid(row=4, column=1, sticky="WE")
        self.entry_license.grid(row=5, column=1, sticky="WE")
        self.label_version.grid(row=6, column=1, sticky="WE")
        self.entry_version.grid(row=7, column=1, sticky="WE")
        self.label_browser_url.grid(row=8, column=1, sticky="WE")
        self.entry_browser_url.grid(row=9, column=1, sticky="WE")
        self.label_download_url.grid(row=10, column=1, sticky="WE")
        self.entry_download_url.grid(row=11, column=1, sticky="WE")
        self.label_release_date.grid(row=12, column=1, sticky="WE")
        self.entry_release_date.grid(row=13, column=1, sticky="WE")
        self.label_file_name.grid(row=14, column=1, sticky="WE")
        self.entry_file_name.grid(row=15, column=1, sticky="WE")
        self.label_maven_url.grid(row=16, column=1, sticky="WE")
        self.entry_maven_url.grid(row=17, column=1, sticky="WE")
        self.btn_add.grid(row=18, column=1, sticky="WE")

    def add(self):
        try:
            new_mod = ModInfo(name=self.sv_name.get(),
                              repo_url=self.sv_page_url.get(),
                              license=self.sv_license.get(),
                              version=self.sv_version.get(),
                              browser_download_url=self.sv_browser_url.get(),
                              download_url=self.sv_download_url.get(),
                              tagged_at=self.sv_release_date.get(),
                              filename=self.sv_file_name.get(),
                              maven=self.sv_maven_url.get())
        except pydantic.error_wrappers.ValidationError:
            showerror("invalid date format", f"{self.sv_release_date.get()} is an invalid format. It must be written as: YYYY-MM-DD hh:mm:ss")
            return

        # refreshing the modlist in case the mod is already in the list
        external_mods = [mod for mod in self.root.gtnh_modpack.external_mods if not mod.name == new_mod.name]
        external_mods.append(new_mod)
        self.root.gtnh_modpack.external_mods=external_mods

        #save/reload because the cached properties doesn't update otherwise
        self.save_gtnh_metadata()
        self.reload_gtnh_metadata()

        content = self.custom_label_frame.get_listbox_content()
        content.append(new_mod.name)
        content = list(set(content))
        self.custom_label_frame.listbox.delete(0, tk.END)
        for entry in sorted(content):
            self.custom_label_frame.listbox.insert(tk.END, entry)





    def fill_fields(self, *args):
        listbox=self.custom_label_frame.listbox
        name = listbox.get(listbox.curselection()[0])
        modinfo = self.root.gtnh_modpack.get_external_mod(name)
        bindings = (("name", self.sv_name),
                    ("repo_url", self.sv_page_url),
                    ("license", self.sv_license),
                    ("version", self.sv_version),
                    ("browser_download_url", self.sv_browser_url),
                    ("download_url", self.sv_download_url),
                    ("tagged_at", self.sv_release_date),
                    ("filename", self.sv_file_name),
                    ("maven", self.sv_maven_url))

        for modinfo_field, stringvar in bindings:
            stringvar.set(getattr(modinfo, modinfo_field))


    def add_callback(self):
        return self.save

    def delete_callback(self):
        return self.save()

    def save(self):
        return True

class ArchiveFrame(BaseFrame):
    """
    Window allowing you to pack the archives for all the supported plateforms.
    """

    def __init__(self, root: MainFrame) -> None:
        """
        Constructor of the ArchiveFrame class.

        :param root: the MainFrame instance
        :return: None
        """
        BaseFrame.__init__(self, root, popup_name="Archive packager")

        # widgets on the window
        self.progress_bar = Progressbar(self, orient="horizontal", mode="determinate", length=500)
        self.progress_bar_global = Progressbar(self, orient="horizontal", mode="determinate", length=500)
        self.progress_label_global = tk.Label(self, text="")
        self.progress_label = tk.Label(self, text="")
        self.btn_start = tk.Button(self, text="start", command=self.start, width=20)

        # grid manager
        self.progress_bar_global.grid(row=0, column=0)
        self.progress_label_global.grid(row=1, column=0)
        self.progress_bar.grid(row=2, column=0)
        self.progress_label.grid(row=3, column=0)
        self.btn_start.grid(row=4, column=0)

    def start(self) -> None:
        """
        Method called when self.btn_start is pressed by the user. It starts the packaging process.

        :return: None
        """
        github = Github(get_token())
        organization = github.get_organization("GTNewHorizons")
        client_folder = Path(__file__).parent / "cache" / "client_archive"
        server_folder = Path(__file__).parent / "cache" / "server_archive"

        try:
            delta_progress_global = 100 / 8

            self._progress_callback(delta_progress_global, "dowloading mods", self.progress_bar_global, self.progress_label_global)
            client_paths, server_paths = self.download_mods_client(self.root.gtnh_modpack, github, organization)

            self._progress_callback(delta_progress_global, "sort client/server side mods", self.progress_bar_global, self.progress_label_global)
            move_mods(client_paths, server_paths)

            self._progress_callback(delta_progress_global, "adding extra files", self.progress_bar_global, self.progress_label_global)
            handle_pack_extra_files()

            self._progress_callback(delta_progress_global, "generating client archive", self.progress_bar_global, self.progress_label_global)
            self.pack_clientpack_client(crawl(client_folder), self.root.gtnh_modpack.modpack_version)

            self._progress_callback(delta_progress_global, "generating server archive", self.progress_bar_global, self.progress_label_global)
            self.pack_serverpack_client(crawl(server_folder), self.root.gtnh_modpack.modpack_version)

            self._progress_callback(delta_progress_global, "generating technic assets", self.progress_bar_global, self.progress_label_global)
            self.pack_technic()

            self._progress_callback(delta_progress_global, "generating deploader for curse", self.progress_bar_global, self.progress_label_global)
            self.make_deploader_json()

            self._progress_callback(delta_progress_global, "generating curse archive", self.progress_bar_global, self.progress_label_global)
            self.pack_curse()
        except PackingInterruptException:
            pass

    def _progress_callback(self, delta_progress: float, label: str, progress_bar_w: Optional[Progressbar] = None, label_w: Optional[tk.Label] = None) -> None:
        """
        Method used to update a progress bar.

        :param delta_progress: progress to add
        :param label: text to display
        :param progress_bar_w: the progress bar widget
        :param label_w: the label widget
        :return: None
        """
        progress_bar_widget = self.progress_bar if progress_bar_w is None else progress_bar_w
        label_widget = self.progress_label if label_w is None else label_w

        # updating the progress bar
        progress_bar_widget["value"] += delta_progress
        progress_bar_widget["value"] = min(100.0, float(format(progress_bar_widget["value"], ".2f")))
        label_widget["text"] = label.format(progress_bar_widget["value"])
        self.update()

    def download_mods_client(self, gtnh_modpack: GTNHModpack, github: Github, organization: Organization) -> Tuple[List[Path], List[Path]]:
        """
        client version of download_mods.

        :param gtnh_modpack: GTNHModpack object. Represents the metadata of the modpack.
        :param github: Github object.
        :param organization: Organization object. Represent the GTNH organization.
        :return: a list holding all the paths to the clientside mods and a list holding all the paths to the serverside
                mod.
        """
        return download_mods(gtnh_modpack, github, organization, self._progress_callback)

    def pack_clientpack_client(self, client_paths: List[Path], pack_version: str) -> None:
        """
        Client version of pack_clientpack.

        :param client_paths: a list containing all the Path objects refering to the files needed client side.
        :param pack_version: the pack version.
        :return: None
        """
        pack_clientpack(client_paths, pack_version, self._progress_callback)

    def pack_serverpack_client(self, server_paths: List[Path], pack_version: str) -> None:
        """
        Client version of pack_serverpack

        :param server_paths: a list containing all the Path objects refering to the files needed server side.
        :param pack_version: the pack version.
        :return: None
        """
        pack_serverpack(server_paths, pack_version, self._progress_callback)

    def make_deploader_json(self) -> None:
        """
        Method used to update the deploader config for curse archives.

        :return: None
        """
        pass

    def pack_curse(self) -> None:
        """
        Method used to generate the curse client and server archives.

        :return: None
        """
        pass

    def pack_technic(self) -> None:
        """
        Method used to generate all the zips needed for solder to update the pack on technic.

        :return: None
        """
        pass


class HandleDepUpdateFrame(BaseFrame):
    """
    Window allowing you to update the dependencies.
    """

    def __init__(self, root: MainFrame) -> None:
        """
        Constructor of HandleDepUpdateFrame class.

        :param root: the MainFrame instance
        :return: None
        """
        BaseFrame.__init__(self, root, popup_name="gradle updater")


class HandleFileExclusionFrame(BaseFrame):
    """
    Window allowing you to update the files dedicated to clientside or serverside.
    """

    def __init__(self, root: MainFrame) -> None:
        """
        Constructor of HandleFileExclusionFrame class.

        :param root: the MainFrame instance
        :return: None
        """

        BaseFrame.__init__(self, root, popup_name="Exclusions editor")

        # widgets
        self.exclusion_frame_client = CustomLabelFrame(
            self, sorted(self.root.gtnh_modpack.client_exclusions), True, text="client entries", add_callback=self.add_client, delete_callback=self.del_client
        )
        self.exclusion_frame_server = CustomLabelFrame(
            self, sorted(self.root.gtnh_modpack.server_exclusions), True, text="server entries", add_callback=self.add_server, delete_callback=self.del_server
        )

        # grid manager
        self.exclusion_frame_client.grid(row=0, column=0)
        self.exclusion_frame_server.grid(row=0, column=1)

    def save(self, entry: str, mode: str = "client", *args: Any, **kwargs: Any) -> bool:
        """
        Method called to save the metadata.

        :return: true
        """
        if mode == "client":
            exclusions = self.exclusion_frame_client.get_listbox_content()
            if entry == "":
                exclusions.append(entry)
            self.root.gtnh_modpack.client_exclusions = sorted(exclusions)

        elif mode == "server":
            exclusions = self.exclusion_frame_server.get_listbox_content()
            if entry == "":
                exclusions.append(entry)
            self.root.gtnh_modpack.server_exclusions = sorted(exclusions)

        self.save_gtnh_metadata()
        return True

    def add_client(self, entry: str, *args: Any, **kwargs: Any) -> bool:
        """
        called when the button add of the client exclusion list is called.
        :param entry: the new exclusion
        :param args:
        :param kwargs:
        :return: true
        """
        return self.save(entry, "client", *args, **kwargs)

    def add_server(self, entry: str, *args: Any, **kwargs: Any) -> bool:
        """
        called when the button add of the server exclusion list is called.
        :param entry: the new exclusion
        :param args:
        :param kwargs:
        :return: true
        """
        return self.save(entry, "server", *args, **kwargs)

    def del_client(self, _: str, *args: Any, **kwargs: Any) -> bool:
        """
        called when the button remove of the client exclusion list is called.
        :param _: the deleted exclusion
        :param args:
        :param kwargs:
        :return: true
        """
        return self.save("", "client", *args, **kwargs)

    def del_server(self, _: str, *args: Any, **kwargs: Any) -> bool:
        """
        called when the button remove of the server exclusion list is called.
        :param _: the deleted exclusion
        :param args:
        :param kwargs:
        :return: true
        """
        return self.save("", "server", *args, **kwargs)


class CustomLabelFrame(tk.LabelFrame):
    """
    Widget providing a basic set of subwidgets to make an editable listbox.
    """

    def __init__(self, master: Any, entries: List[str], framed: bool, add_callback: Any = None, delete_callback: Any = None, *args: Any, **kwargs: Any) -> None:
        """
        Constructor of CustomLabelFrame class.
        """
        # select the appropriate frame
        if framed:
            tk.LabelFrame.__init__(self, master, *args, **kwargs)
        else:
            tk.LabelFrame.__init__(self, master, relief="flat", *args, **kwargs)

        # callback memory
        self.add_callback = add_callback
        self.delete_callback = delete_callback

        # widgets
        self.listbox = tk.Listbox(self, width=80)
        self.scrollbar_vertical = tk.Scrollbar(self)
        self.scrollbar_horizontal = tk.Scrollbar(self, orient=tk.HORIZONTAL)
        self.stringvar = tk.StringVar(self, value="")
        self.entry = tk.Entry(self, textvariable=self.stringvar)
        self.btn_add = tk.Button(self, text="add", command=self.add)
        self.btn_remove = tk.Button(self, text="remove", command=self.remove)

        # bind the scrollbars
        self.scrollbar_vertical.config(command=self.listbox.yview)
        self.listbox.config(yscrollcommand=self.scrollbar_vertical.set)

        self.scrollbar_horizontal.config(command=self.listbox.xview)
        self.listbox.config(xscrollcommand=self.scrollbar_horizontal.set)

        # populate the listbox
        for entry in entries:
            self.listbox.insert(tk.END, entry)

        # grid manager
        self.listbox.grid(row=0, column=0, columnspan=2, sticky="WE")
        self.scrollbar_vertical.grid(row=0, column=2, sticky="NS")
        self.scrollbar_horizontal.grid(row=1, column=0, columnspan=2, sticky="WE")
        self.entry.grid(row=2, column=0, columnspan=2, sticky="WE")
        self.btn_add.grid(row=3, column=0, sticky="WE")
        self.btn_remove.grid(row=3, column=1, sticky="WE")

    def add(self) -> None:
        """
        Method bound to self.btn_add. Let the user add the text in the entry in the listbox.

        :return: None
        """
        # duplicate handling is supposed to be made in the callback
        if self.add_callback is not None:
            if self.add_callback(self.entry.get()):
                self.listbox.insert(tk.END, self.entry.get())
        else:
            self.listbox.insert(tk.END, self.entry.get())

    def remove(self) -> None:
        """
        Method bound to self.btn_remove. Let the user remove the selected entry in the listbox. Does nothing if no entry
        had been selected in the listbox.

        :return: None
        """
        # ignoring errors if the delete button had been pressed without selecting an item in the listbox
        try:
            index = self.listbox.curselection()[0]
            if self.delete_callback is not None:
                if self.delete_callback(self.listbox.get(index)):
                    self.listbox.delete(index)
            else:
                self.listbox.delete(index)
        except IndexError:
            pass

    def get_listbox_content(self) -> List[str]:
        """
        Method to return the list of the entries contained in the listbox.

        :return: the list of entries contained in the listbox.
        """
        return [str(item) for item in self.listbox.get(0, tk.END)]


if __name__ == "__main__":
    m = MainFrame()
    m.mainloop()
