from __future__ import annotations

import contextlib
import tkinter
from pathlib import Path
from tkinter import ttk
from tkinter.font import Font
from typing import Any

import pygments
import pygments.lexers
import toml

from .schemeparser import _parse_scheme

color_schemes_dir = Path(__file__).parent / "colorschemes"


class CodeView(tkinter.Text):
    _w: str
    _builtin_color_schemes = {"ayu-dark", "ayu-light", "dracula", "mariana", "monokai"}

    def __init__(
        self,
        master: tkinter.Misc | None = None,
        lexer: pygments.lexers.Lexer = pygments.lexers.PythonLexer,
        color_scheme: dict[str, dict[str, str | int]] | str | None = None,
        tab_width: int = 4,
        **kwargs,
    ) -> None:
        self._frame = ttk.Frame(master)
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_columnconfigure(0, weight=1)

        kwargs.setdefault("wrap", "none")
        kwargs.setdefault("font", ("monospace", 11))

        super().__init__(self._frame, **kwargs)
        super().grid(row=0, column=0, sticky="nswe")

        self._hs = ttk.Scrollbar(self._frame, orient="horizontal", command=self.xview)
        self._vs = ttk.Scrollbar(self._frame, orient="vertical", command=self.yview)

        self._hs.grid(row=1, column=0, sticky="we")
        self._vs.grid(row=0, column=1, sticky="ns")

        super().configure(
            xscrollcommand=self._hs.set,
            yscrollcommand=self._vs.set,
            tabs=Font(font=kwargs["font"]).measure(" " * tab_width),
        )

        contmand = "Command" if self._windowingsystem == "aqua" else "Control"

        super().bind(f"<{contmand}-c>", self._copy)
        super().bind(f"<{contmand}-v>", self._paste)
        super().bind(f"<{contmand}-a>", self._select_all)

        self._orig = f"{self._w}_widget"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._cmd_proxy)

        self._set_lexer(lexer)
        self._set_color_scheme(color_scheme)

    def _select_all(self, *_) -> str:
        self.tag_add("sel", "1.0", "end")
        self.mark_set("insert", "end")
        return "break"

    def _paste(self, *_):
        insert = self.index(f"@0,0 + {self.cget('height') // 2} lines")

        with contextlib.suppress(tkinter.TclError):
            self.delete("sel.first", "sel.last")
            self.tag_remove("sel", "1.0", "end")
            self.insert("insert", self.clipboard_get())

        self.see(insert)

        return "break"

    def _copy(self, *_):
        text = self.get("sel.first", "sel.last")
        if not text:
            text = self.get("insert linestart", "insert lineend")

        self.clipboard_clear()
        self.clipboard_append(text)

        return "break"

    def _cmd_proxy(self, command: str, *args) -> Any:
        cmd = (self._orig, command) + args
        try:
            result = self.tk.call(cmd)
        except tkinter.TclError as e:
            if 'tagged with "sel"' in str(e):
                return ""
            raise e from None

        if command == "insert":
            length = len(args[1].splitlines())
            if length == 1:
                self._highlight()
            else:
                self.after_idle(lambda: self._highlight_lines(length))
            self.event_generate("<<ContentChanged>>")
        elif command in {"replace", "delete"}:
            self._highlight()
            self.event_generate("<<ContentChanged>>")
        
        return result

    def _setup_tags(self, tags: dict[str, str]) -> None:
        for key, value in tags.items():
            if isinstance(value, str):
                self.tag_configure(f"Token.{key}", foreground=value)

    def _highlight(self) -> None:
        line = int(self.index("insert").split(".")[0])

        for tag in self.tag_names(index=None):
            if tag.startswith("Token"):
                self.tag_remove(tag, f"{line}.0", f"{line}.end")

        line_text = self.get(f"{line}.0", f"{line}.end")
        start_col = 0

        for token, text in pygments.lex(line_text, self._lexer()):
            end_col = start_col + len(text)
            self.tag_add(str(token), f"{line}.{start_col}", f"{line}.{end_col}")
            start_col = end_col

    def _highlight_lines(self, line_count: int = 1) -> None:
        current_index = self.index("insert")
        start_index = self.index(f"insert linestart - {line_count} lines")

        for tag in self.tag_names(index=None):
            if tag.startswith("Token"):
                self.tag_remove(tag, start_index, current_index)

        lines = self.get(start_index, current_index)
        lexer = self._lexer()

        for token, text in pygments.lex(lines, lexer):
            token = str(token)
            end_index = self.index(f"{start_index} + {len(text)} indices")
            if token not in {"Token.Text.Whitespace", "Token.Text"}:
                self.tag_add(token, start_index, end_index)
            start_index = end_index

    def highlight_all(self) -> None:
        start_index = "1.0"

        for tag in self.tag_names(index=None):
            if tag.startswith("Token"):
                self.tag_remove(tag, "1.0", "end")

        lines = self.get("1.0", "end")
        lexer = self._lexer()

        for token, text in pygments.lex(lines, lexer):
            token = str(token)
            end_index = self.index(f"{start_index} + {len(text)} indices")
            if token not in {"Token.Text.Whitespace", "Token.Text"}:
                self.tag_add(token, start_index, end_index)
            start_index = end_index

    def _set_color_scheme(
        self, color_scheme: dict[str, dict[str, str | int]] | str | None
    ) -> None:
        if (
            isinstance(color_scheme, str)
            and color_scheme in self._builtin_color_schemes
        ):
            color_scheme = toml.load(color_schemes_dir / f"{color_scheme}.toml")
        elif color_scheme is None:
            color_scheme = toml.load(color_schemes_dir / "dracula.toml")

        assert isinstance(
            color_scheme, dict
        ), "Must be a dictionary or a built-in color scheme"

        config, tags = _parse_scheme(color_scheme)
        self.configure(**config)
        self._setup_tags(tags)

        self.highlight_all()

    def _set_lexer(self, lexer: pygments.lexers.Lexer) -> None:
        self._lexer = lexer

        self.highlight_all()

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
            tkinter.BaseWidget.destroy(widget)
        tkinter.BaseWidget.destroy(self._frame)
