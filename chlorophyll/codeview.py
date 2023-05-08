from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from tkinter import BaseWidget, Event, Misc, TclError, Text, ttk
from tkinter.font import Font
from typing import Any

from pygments import lex
import pygments.lexers
from pyperclip import copy
from tklinenums import TkLineNumbers
from toml import load

from .schemeparser import _parse_scheme

color_schemes_dir = Path(__file__).parent / "colorschemes"

def return_self(func):
    def wrapper(self=None, *args, **kwargs):
        func(self, *args, **kwargs)
        return self

    return wrapper
class CodeView(Text):
    _w: str
    _builtin_color_schemes = {"ayu-dark", "ayu-light", "dracula", "mariana", "monokai"}

    def __init__(
        self,
        master: Misc | None = None,
        lexer: pygments.lexers.Lexer = pygments.lexers.TextLexer,
        color_scheme: dict[str, dict[str, str | int]] | str | None = None,
        tab_width: int = 4,
        **kwargs,
    ) -> None:
        self._frame = ttk.Frame(master)
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_columnconfigure(1, weight=1)

        kwargs.setdefault("wrap", "none")
        kwargs.setdefault("font", ("monospace", 11))

        super().__init__(self._frame, **kwargs)
        super().grid(row=0, column=1, sticky="nswe")

        self._line_numbers = TkLineNumbers(self._frame, self, justify=kwargs.get("justify", "left"))
        self._vs = ttk.Scrollbar(self._frame, orient="vertical", command=self.yview)
        self._hs = ttk.Scrollbar(self._frame, orient="horizontal", command=self.xview)

        self._line_numbers.grid(row=0, column=0, sticky="ns")
        self._vs.grid(row=0, column=2, sticky="ns")
        self._hs.grid(row=1, column=1, sticky="we")

        super().configure(
            yscrollcommand=self.vertical_scroll,
            xscrollcommand=self.horizontal_scroll,
            tabs=Font(font=kwargs["font"]).measure(" " * tab_width),
        )

        contmand = "Command" if self._windowingsystem == "aqua" else "Control"

        super().bind(f"<{contmand}-c>", self._copy, add=True)
        super().bind(f"<{contmand}-v>", self._paste, add=True)
        super().bind(f"<{contmand}-a>", self._select_all, add=True)
        super().bind(f"<{contmand}-Shift-Z>", self.redo, add=True)
        super().bind("<<ContentChanged>>", self.scroll_line_update, add=True)

        self._orig = f"{self._w}_widget"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._cmd_proxy)

        self._set_lexer(lexer)
        self._set_color_scheme(color_scheme)

    def _select_all(self, *_) -> str:
        self.tag_add("sel", "1.0", "end")
        self.mark_set("insert", "end")
        return "break"

    @return_self
    def redo(self, event: Event | None = None) -> CodeView:
        try:
            self.edit_redo()
        except TclError:
            pass

    def _paste(self, *_) -> str:
        insert = self.index(f"@0,0 + {self.cget('height') // 2} lines")

        with suppress(TclError):
            self.delete("sel.first", "sel.last")
            self.tag_remove("sel", "1.0", "end")
            self.insert("insert", self.clipboard_get())

        self.see(insert)

        return "break"

    def _copy(self, *_) -> str:
        text = self.get("sel.first", "sel.last")
        if not text:
            text = self.get("insert linestart", "insert lineend")

        copy(text)

        return "break"

    def _cmd_proxy(self, command: str, *args) -> Any:
        try:
            result = self.tk.call(self._orig, command, *args)
        except TclError as e:
            error = str(e)
            if 'tagged with "sel"' in error or "nothing to" in error:
                return ""
            raise e from None

        if command in ("insert", "replace", "delete"):
            self.highlight()
            self.event_generate("<<ContentChanged>>")

        return result

    @return_self
    def _setup_tags(self, tags: dict[str, str]) -> CodeView:
        for key, value in tags.items():
            if isinstance(value, str):
                self.tag_configure(f"Token.{key}", foreground=value)

    @return_self
    def highlight(self) -> CodeView:
        # Only highlights the visible area
        
        # Get visible area, text, and line offset
        visible_area: tuple[str] = self.index("@0,0"), self.index(f"@0,{self.winfo_height()}")
        visible_text: str = self.get(*visible_area)
        line_offset: int = visible_text.count("\n") - visible_text.lstrip().count("\n")

        # Update MLCDS tags where necessary

        # Remove Token tags from 1.0 to end (MLCDS - Multi Line Comment | Docstring tag is not removed)
        for tag in self.tag_names(index=None):
            if tag.startswith("Token"):
                self.tag_remove(tag, "1.0", "end")

        # Work with MLCDS tags, add the necessary ends and starts to visible_text
        # Then lex the visible_text
        # Splice the tags to remove parts that are not visible (columns to the left or right of the visible area)
        # Remove any tags that are on emoji characters
        # Then add the tags to the text widget


    @return_self
    def _set_color_scheme(self, color_scheme: dict[str, dict[str, str | int]] | str | None) -> CodeView:
        if isinstance(color_scheme, str) and color_scheme in self._builtin_color_schemes:
            color_scheme = load(color_schemes_dir / f"{color_scheme}.toml")
        elif color_scheme is None:
            color_scheme = load(color_schemes_dir / "dracula.toml")

        assert isinstance(color_scheme, dict), "Must be a dictionary or a built-in color scheme"

        config, tags = _parse_scheme(color_scheme)
        self.configure(**config)
        self._setup_tags(tags)

        self.highlight()

    @return_self
    def _set_lexer(self, lexer: pygments.lexers.Lexer) -> CodeView:
        self._lexer = lexer

        self.highlight()

    @return_self
    def __setitem__(self, key: str, value) -> CodeView:
        self.configure(**{key: value})

    def __getitem__(self, key: str) -> Any:
        return self.cget(key)

    @return_self
    def configure(self, **kwargs) -> CodeView:
        lexer = kwargs.pop("lexer", None)
        color_scheme = kwargs.pop("color_scheme", None)

        if lexer is not None:
            self._set_lexer(lexer)

        if color_scheme is not None:
            self._set_color_scheme(color_scheme)

        super().configure(**kwargs)

    config = configure

    @return_self
    def pack(self, *args, **kwargs) -> CodeView:
        self._frame.pack(*args, **kwargs)

    @return_self
    def grid(self, *args, **kwargs) -> CodeView:
        self._frame.grid(*args, **kwargs)

    @return_self
    def place(self, *args, **kwargs) -> CodeView:
        self._frame.place(*args, **kwargs)

    @return_self
    def pack_forget(self) -> CodeView:
        self._frame.pack_forget()

    @return_self
    def grid_forget(self) -> CodeView:
        self._frame.grid_forget()

    @return_self
    def place_forget(self) -> CodeView:
        self._frame.place_forget()

    def destroy(self) -> None:
        for widget in self._frame.winfo_children():
            BaseWidget.destroy(widget)
        BaseWidget.destroy(self._frame)

    @return_self
    def horizontal_scroll(self, first: str | float, last: str | float) -> CodeView:
        self._hs.set(first, last)

    @return_self
    def vertical_scroll(self, first: str | float, last: str | float) -> CodeView:
        self.highlight()
        self._vs.set(first, last)
        self._line_numbers.redraw()

    @return_self
    def scroll_line_update(self, event: Event | None = None) -> CodeView:
        self.horizontal_scroll(*self.xview())
        self.vertical_scroll(*self.yview())
