<h1 align="center">Chlorophyll</h1>

> **Note**
> This module is the successor to [`tkcode`](https://github.com/rdbende/tkcode), as it is deprecated - please do not use it any more.

## Description
Chlorophyll provides the `CodeView` widget for tkinter, which is a `Text` widget with syntax highlighting, line numbers, and works as a simple code editor. It is written in Python and uses the [`pygments`](https://pygments.org/) library for syntax highlighting and the [`TkLineNums`](https://www.github.com/Moosems/TkLineNums) module for line numbers.


## Installation

`pip install chlorophyll`

# Documentation

### `CodeView` Widget
|Options      |Description                     |Input                                         |
|-------------|--------------------------------|----------------------------------------------|
|master       |The parent widget               |Tkinter widget                                |
|lexer        |The Language lexer              |Pygments lexer                                |
|color_scheme |A color scheme for the code     |Dict, string, or toml file                    |
|tab_width    |The width of a tab (`\t`)       |Int                                           |
|**kwargs      |Keyword arguments for the widget|Any keyword arguments given to a `Text` widget|

#### Basic Usage:
```python
from tkinter import Tk

import pygments.lexers
from chlorophyll import CodeView

root = Tk()

codeview = CodeView(root, lexer=pygments.lexers.RustLexer, color_scheme="monokai")
codeview.pack(fill="both", expand=True)

root.mainloop()
```