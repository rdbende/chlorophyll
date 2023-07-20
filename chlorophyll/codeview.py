from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from tkinter import BaseWidget, Event, Misc, TclError, Text, ttk
from tkinter.font import Font
from typing import Any

import pygments.lexers

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
        # Set up the frame
        self._frame = ttk.Frame(master)
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_columnconfigure(1, weight=1)

        # Set kwargs
        kwargs.setdefault("wrap", "none")
        kwargs.setdefault("font", ("monospace", 11))

        # Finish setting up the text widget
        super().__init__(self._frame, **kwargs)
        super().grid(row=0, column=1, sticky="nswe")

        # Set up the line numbers and scrollbars
        self._line_numbers = TkLineNumbers(self._frame, self, justify=kwargs.get("justify", "left"))
        self._vs = ttk.Scrollbar(self._frame, orient="vertical", command=self.yview)
        self._hs = ttk.Scrollbar(self._frame, orient="horizontal", command=self.xview)

        # Grid the line numbers and scrollbars
        self._line_numbers.grid(row=0, column=0, sticky="ns")
        self._vs.grid(row=0, column=2, sticky="ns")
        self._hs.grid(row=1, column=1, sticky="we")

        # Configure the text widget
        super().configure(
            yscrollcommand=self.vertical_scroll,
            xscrollcommand=self.horizontal_scroll,
            tabs=Font(font=kwargs["font"]).measure(" " * tab_width),
        )

        # Set up the key bindings
        contmand = "Command" if self._windowingsystem == "aqua" else "Control"

        super().bind(f"<{contmand}-c>", self._copy, add=True)
        super().bind(f"<{contmand}-v>", self._paste, add=True)
        super().bind(f"<{contmand}-a>", self._select_all, add=True)
        super().bind(f"<{contmand}-Shift-Z>", self.redo, add=True)
        super().bind("<<ContentChanged>>", self.scroll_line_update, add=True)

        # Set up the proxy
        self._orig = f"{self._w}_widget"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._cmd_proxy)

        # Create any necessary variables
        self._current_text: str = self.get("1.0", "end-1c")
        self._current_visible_area: tuple[str, str] = self.index("@0,0"), self.index(f"@0,{self.winfo_height()}")

        # Set up the lexer and color scheme along with the MLCDS tag
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
        """Highlights all the visible text in the text widget"""

        # Get visible area and text
        visible_area: tuple[str] = self.index("@0,0"), self.index(f"@0,{self.winfo_height()}")
        visible_text: str = self.get(*visible_area)

        # Check if anything has changed
        if visible_area == self._current_visible_area and visible_text == self._current_text:
            return

        self._current_text = visible_text

        # Get line offset
        line_offset: int = int(self.index("@0,0").split(".")[0]) - 1
        # Not used yet (remove F841 when used)

        # Remove all tags
        for tag in self.tag_names():
            if tag.startswith("Token."):
                self.tag_remove(tag, "1.0", "end")

        # Highlight the text
        start_index = str(self.tk.call(self._orig, "index", f"1.0 + {line_offset} lines"))
        for token, text in pygments.lex(visible_text, self._lexer):
            token = str(token)
            end_index = self.index(f"{start_index} + {len(text)} chars")
            if token not in {"Token.Text.Whitespace", "Token.Text"}:
                self.tag_add(token, start_index, end_index)
            start_index = end_index

        self._current_visible_area = visible_area

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
        self._current_visible_area = self.index("@0,0"), self.index(f"@0,{self.winfo_height()}")
        self.highlight()
        self._vs.set(first, last)
        self._line_numbers.redraw()

    def scroll_line_update(self, _: Event | None = None) -> None:
        self.horizontal_scroll(*self.xview())
        self.vertical_scroll(*self.yview())