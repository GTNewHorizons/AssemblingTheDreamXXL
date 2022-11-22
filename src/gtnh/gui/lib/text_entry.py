from tkinter import Entry, Frame, Label, StringVar
from typing import Any


class TextEntry(Frame):
    def __init__(self, master: Any, label_text: str, *args: Any, **kwargs: Any):
        Frame.__init__(self, master, *args, **kwargs)
        self.label_text: str = label_text
        self.label: Label = Label(self, text=self.label_text)
        self.string_var: StringVar = StringVar(self)
        self.entry: Entry = Entry(self, textvariable=self.string_var)

    def set(self, value: str) -> None:
        self.string_var.set(value)

    def get(self) -> str:
        return self.string_var.get()

    def grid_forget(self, *args: Any, **kwargs: Any) -> None:
        self.label.grid_forget()
        self.entry.grid_forget()
        super().grid_forget()

    def grid(self, *args: Any, **kwargs: Any) -> None:
        self.label.grid(row=0, column=0)
        self.entry.grid(row=0, column=1)
        super().grid(*args, **kwargs)
