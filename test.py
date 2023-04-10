from chlorophyll import CodeView
from tkinter import Tk
from pygments.lexers import PythonLexer

root = Tk()
codeview = CodeView(root, lexer=PythonLexer)
codeview.pack()

for i in range(10):
    codeview.insert("1.0", "print()\n")

root.mainloop()