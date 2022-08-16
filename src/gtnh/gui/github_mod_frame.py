import asyncio
from tkinter import END, Button, Entry, Label, LabelFrame, Listbox, Scrollbar, StringVar
from tkinter.ttk import Combobox
from typing import Any, Callable, Coroutine, Dict, List, Optional

from gtnh.gui.mod_info_frame import ModInfoFrame
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import GTNHModInfo
from gtnh.modpack_manager import GTNHModpackManager


class GithubModList(LabelFrame):
    """
    Widget handling the list of github mods.
    """

    def __init__(
        self, master: Any, frame_name: str, callbacks: Dict[str, Any], width: Optional[int] = None, **kwargs: Any
    ):
        """
        Constructor of the GithubModList class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.get_gtnh_callback: Callable[[], Coroutine[Any, Any, GTNHModpackManager]] = callbacks["get_gtnh"]
        self.get_github_mods_callback: Callable[[], Dict[str, str]] = callbacks["get_github_mods"]
        self.ypadding: int = 0  # todo: tune this
        self.xpadding: int = 0  # todo: tune this

        new_repo_text: str = "enter the new repo here"
        add_repo_text: str = "add repository"
        del_repo_text: str = "delete highlighted"
        self.width: int = (
            width if width is not None else max(len(new_repo_text), len(add_repo_text), len(del_repo_text))
        )

        self.sv_repo_name: StringVar = StringVar(self, value="")

        self.mod_info_callback: Callable[[Any], None] = callbacks["mod_info"]

        self.lb_mods: Listbox = Listbox(self, exportselection=False)
        self.lb_mods.bind("<<ListboxSelect>>", lambda event: asyncio.ensure_future(self.on_listbox_click(event)))

        self.label_entry: Label = Label(self, text=new_repo_text)
        self.entry: Entry = Entry(self, textvariable=self.sv_repo_name)

        self.btn_add: Button = Button(self, text=add_repo_text)
        self.btn_rem: Button = Button(self, text=del_repo_text)

        self.scrollbar: Scrollbar = Scrollbar(self)
        self.lb_mods.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.configure(command=self.lb_mods.yview)

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.label_entry.configure(width=self.width)
        self.entry.configure(width=self.width + 4)

        self.btn_add.configure(width=self.width)
        self.btn_rem.configure(width=self.width)

    def set_width(self, width: int) -> None:
        """
        Method to set the widgets' width.

        :param width: the new width
        :return: None
        """
        self.width = width
        self.configure_widgets()

    def get_width(self) -> int:
        """
        Getter for self.width.

        :return: the width in character sizes of the normalised widgets
        """
        return self.width

    def update_widget(self) -> None:
        """
        Method to update the widget and all its childs

        :return: None
        """
        self.hide()
        self.configure_widgets()
        self.show()

    def hide(self) -> None:
        """
        Method to hide the widget and all its childs
        :return None:
        """
        self.lb_mods.grid_forget()
        self.scrollbar.grid_forget()
        self.label_entry.grid_forget()
        self.entry.grid_forget()
        self.btn_add.grid_forget()
        self.btn_rem.grid_forget()

        self.master.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.columnconfigure(1, weight=1, pad=self.ypadding)

        for i in range(0, 5):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        self.lb_mods.grid(row=x, column=y, columnspan=2, sticky="WE")
        self.scrollbar.grid(row=x, column=y + 2, columnspan=2, sticky="NS")
        self.label_entry.grid(row=x + 1, column=y)
        self.entry.grid(row=x + 1, column=y + 1, columnspan=2)
        self.btn_add.grid(row=x + 2, column=y)
        self.btn_rem.grid(row=x + 2, column=y + 1, columnspan=2)

        self.master.update_idletasks()

    def populate_data(self, data: List[str]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.lb_mods.insert(END, *data)

    async def on_listbox_click(self, event: Any) -> None:
        """
        Callback used when the user clicks on the github mods' listbox.

        :param event: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """

        index: int = self.lb_mods.curselection()[0]
        gtnh: GTNHModpackManager = await self.get_gtnh_callback()
        mod_info: GTNHModInfo = gtnh.assets.get_github_mod(self.lb_mods.get(index))
        name: str = mod_info.name
        mod_versions: list[GTNHVersion] = mod_info.versions
        latest_version: Optional[GTNHVersion] = mod_info.get_latest_version()
        assert latest_version
        current_version: str = (
            self.get_github_mods_callback()[name]
            if name in self.get_github_mods_callback()
            else latest_version.version_tag
        )
        license: str = mod_info.license or "No license detected"
        side: str = mod_info.side

        data = {
            "name": name,
            "versions": [version.version_tag for version in mod_versions],
            "current_version": current_version,
            "license": license,
            "side": side,
        }

        self.mod_info_callback(data)


class GithubModFrame(LabelFrame):
    """
    Main frame widget for the github mods' management.
    """

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: Dict[str, Any],
        **kwargs: Any,
    ):
        """
        Constructor of the GithubModFrame class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding: int = 0  # todo: tune this
        self.xpadding: int = 0  # todo: tune this

        modpack_version_callbacks: Dict[str, Any] = {"set_modpack_version": callbacks["set_modpack_version"]}

        self.modpack_version_frame: ModpackVersionFrame = ModpackVersionFrame(
            self, frame_name="Modpack version", callbacks=modpack_version_callbacks
        )

        mod_info_callbacks: Dict[str, Any] = {
            "set_mod_version": callbacks["set_github_mod_version"],
            "set_mod_side": callbacks["set_github_mod_side"],
        }

        self.mod_info_frame: ModInfoFrame = ModInfoFrame(
            self, frame_name="github mod info", callbacks=mod_info_callbacks
        )

        github_mod_list_callbacks: Dict[str, Any] = {
            "mod_info": self.mod_info_frame.populate_data,
            "get_github_mods": callbacks["get_github_mods"],
            "get_gtnh": callbacks["get_gtnh"],
        }

        self.github_mod_list: GithubModList = GithubModList(
            self, frame_name="github mod list", callbacks=github_mod_list_callbacks
        )

        width: int = self.github_mod_list.get_width()
        self.mod_info_frame.set_width(width)
        self.modpack_version_frame.set_width(width)
        self.update_widget()

    def update_widget(self) -> None:
        """
        Method to update the widget and all its childs

        :return: None
        """
        self.hide()
        self.configure_widgets()
        self.show()

        self.modpack_version_frame.update_widget()
        self.mod_info_frame.update_widget()
        self.github_mod_list.update_widget()

    def hide(self) -> None:
        """
        Method to hide the widget and all its childs
        :return None:
        """
        self.modpack_version_frame.grid_forget()
        self.github_mod_list.grid_forget()  # ref widget
        self.mod_info_frame.grid_forget()

        self.modpack_version_frame.hide()
        self.github_mod_list.hide()
        self.mod_info_frame.hide()

        self.master.update_idletasks()

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        pass

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.rowconfigure(0, weight=1, pad=self.xpadding)
        self.rowconfigure(1, weight=1, pad=self.xpadding)
        self.rowconfigure(2, weight=1, pad=self.xpadding)

        self.modpack_version_frame.grid(row=0, column=0, sticky="WE")
        self.github_mod_list.grid(row=1, column=0)  # ref widget
        self.mod_info_frame.grid(row=2, column=0, sticky="WE")
        self.master.update_idletasks()

        self.modpack_version_frame.show()
        self.github_mod_list.show()
        self.mod_info_frame.show()

    def populate_data(self, data: Dict[str, Any]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.github_mod_list.populate_data(data["github_mod_list"])
        self.modpack_version_frame.populate_data(data["modpack_version_frame"])


class ModpackVersionFrame(LabelFrame):
    """
    Frame to chose the gtnh modpack repo assets' version.
    """

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: Dict[str, Callable[[str], None]],
        width: Optional[int] = None,
        **kwargs: Any,
    ):
        """
        Constructor of the ModpackVersionFrame.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding: int = 0  # todo: tune this
        self.xpadding: int = 0  # todo: tune this
        modpack_version_text: str = "Modpack version:"
        self.width: int = width if width is not None else len(modpack_version_text)
        self.label_modpack_version: Label = Label(self, text=modpack_version_text)
        self.sv_version: StringVar = StringVar(value="")
        self.cb_modpack_version: Combobox = Combobox(self, textvariable=self.sv_version, values=[])
        self.cb_modpack_version.bind(
            "<<ComboboxSelected>>", lambda event: callbacks["set_modpack_version"](self.sv_version.get())
        )

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.label_modpack_version.configure(width=self.width)
        self.cb_modpack_version.configure(width=self.width)

    def set_width(self, width: int) -> None:
        """
        Method to set the widgets' width.

        :param width: the new width
        :return: None
        """
        self.width = width
        self.configure_widgets()

    def get_width(self) -> int:
        """
        Getter for self.width.

        :return: the width in character sizes of the normalised widgets
        """
        return self.width

    def update_widget(self) -> None:
        """
        Method to update the widget and all its childs

        :return: None
        """
        self.hide()
        self.configure_widgets()
        self.show()

    def hide(self) -> None:
        """
        Method to hide the widget and all its childs
        :return None:
        """
        self.label_modpack_version.grid_forget()
        self.cb_modpack_version.grid_forget()

        self.master.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.columnconfigure(1, weight=1, pad=self.ypadding)
        self.rowconfigure(0, weight=1, pad=self.xpadding)

        self.label_modpack_version.grid(row=0, column=0)
        self.cb_modpack_version.grid(row=0, column=1)

    def populate_data(self, data: Dict[str, Any]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.cb_modpack_version["values"] = data["combobox"]
        self.sv_version.set(data["stringvar"])
