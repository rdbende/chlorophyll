from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from tkinter import BaseWidget, Event, Misc, TclError, Text, ttk
from tkinter.font import Font
from typing import Any

import pygments.lexers
from pygments import lex  # noqa: F401

# Currently not used while the highlight method is not implemented
from pyperclip import copy
from tklinenums import TkLineNumbers
from toml import load

from .schemeparser import _parse_scheme

color_schemes_dir = Path(__file__).parent / "colorschemes"


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

        self.tag_configure("MLCDS")
        self._set_lexer(lexer)
        self._set_color_scheme(color_scheme)

    def _select_all(self, *_) -> str:
        self.tag_add("sel", "1.0", "end")
        self.mark_set("insert", "end")
        return "break"

    def redo(self, event: Event | None = None) -> None:
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

    def _setup_tags(self, tags: dict[str, str]) -> None:
        for key, value in tags.items():
            if isinstance(value, str):
                self.tag_configure(f"Token.{key}", foreground=value)

    def highlight(self) -> None:
        """
        Plan:
        1. Create a new tag named "MLCDS" to remember where Docstrings (DS), Multi Line Comments (MLCs),
        and backstick code areas (markdown) start and end. This tag should not start with "Token" so
        that it is not deleted later.
        2. Make a method that takes the tokens and tags and areas to remove and returns the tags without
        those areas.
        3. When highlight() runs, check if anything has changed in the text widget. If not, return.
        (Things to look for include viewable area, text, and so on.)
        4. Update the code to add MLCDS tags to the text widget where necessary. If a line starts or
        ends with a Docstring or MLC, add an MLCDS tag to the entire line.
        5. When the visible area of the text widget changes, get the visible area, visible text, and
        line offset, as before.
        6. Work with the MLCDS tags to add the necessary starts and ends to the visible text and then lex
        it using Pygments.
        7. Splice the tags to remove parts that are not visible (columns to the left or right of the visible
        area) and remove any tags that are on emoji characters.
        8. Add the remaining tags to the visible text and display it in the text widget.
        9. Not in method: update the docs when this is done.
        10. Also not in method: Make sure that when typing, the typing area is viewable (see()).
        """

        # Get visible area, text, and line offset
        visible_area: tuple[str] = self.index("@0,0"), self.index(f"@0,{self.winfo_height()}")
        visible_text: str = self.get(*visible_area)
        line_offset: int = visible_text.count("\n") - visible_text.lstrip().count("\n")  # noqa: F841
        # Not used yet (remove F841 when used)

        # Update MLCDS tags where necessary

        # Remove Token tags from 1.0 to end (MLCDS - Multi Line Comment | Docstring tag is not removed)
        for tag in self.tag_names(index=None):
            if tag.startswith("Token"):
                self.tag_remove(tag, "1.0", "end")

    def _set_color_scheme(self, color_scheme: dict[str, dict[str, str | int]] | str | None) -> None:
        if isinstance(color_scheme, str) and color_scheme in self._builtin_color_schemes:
            color_scheme = load(color_schemes_dir / f"{color_scheme}.toml")
        elif color_scheme is None:
            color_scheme = load(color_schemes_dir / "dracula.toml")

        assert isinstance(color_scheme, dict), "Must be a dictionary or a built-in color scheme"

        config, tags = _parse_scheme(color_scheme)
        self.configure(**config)
        self._setup_tags(tags)

        self.highlight()

    def _set_lexer(self, lexer: pygments.lexers.Lexer) -> None:
        self._lexer = lexer

        self.highlight()

    def __setitem__(self, key: str, value) -> None:
        self.configure(**{key: value})

    def __getitem__(self, key: str) -> Any:
        return self.cget(key)

    def configure(self, **kwargs) -> None:
        lexer = kwargs.pop("lexer", None)
        color_scheme = kwargs.pop("color_scheme", None)

        if lexer is not None:
            self._set_lexer(lexer)

        if color_scheme is not None:
            self._set_color_scheme(color_scheme)

        super().configure(**kwargs)

    config = configure

    def pack(self, *args, **kwargs) -> None:
        self._frame.pack(*args, **kwargs)

    def grid(self, *args, **kwargs) -> None:
        self._frame.grid(*args, **kwargs)

    def place(self, *args, **kwargs) -> None:
        self._frame.place(*args, **kwargs)

    def pack_forget(self) -> None:
        self._frame.pack_forget()

    def grid_forget(self) -> None:
        self._frame.grid_forget()

    def place_forget(self) -> None:
        self._frame.place_forget()

    def destroy(self) -> None:
        for widget in self._frame.winfo_children():
            BaseWidget.destroy(widget)
        BaseWidget.destroy(self._frame)

    def horizontal_scroll(self, first: str | float, last: str | float) -> None:
        self._hs.set(first, last)

    def vertical_scroll(self, first: str | float, last: str | float) -> None:
        self.highlight()
        self._vs.set(first, last)
        self._line_numbers.redraw()

    def scroll_line_update(self, event: Event | None = None) -> None:
        self.horizontal_scroll(*self.xview())
        self.vertical_scroll(*self.yview())
