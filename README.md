<h1 align="center">Chlorophyll</h1>

A module that fills your code with color - syntax highlighted text box widget for Tkinter.

This module is the successor to [`tkcode`](https://github.com/rdbende/tkcode), as it is deprecated - please do not use it anymore.

## Notice

This repository has been moved to Gitlab. The repo is archieved and is read-only now. Please go to [Gitlab](https://gitlab.com/rdbende/chlorophyll) to get updates and participate on issues.

## Installation

`pip install chlorophyll`

## Basic usage
Until there's no documentation

```python
import tkinter

import pygments.lexers
from chlorophyll import CodeView

root = tkinter.Tk()

codeview = CodeView(root, lexer=pygments.lexers.RustLexer, color_scheme="monokai")
codeview.pack(fill="both", expand=True)

root.mainloop()
```
