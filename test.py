from chlorophyll import CodeView
from tkinter import Tk

root = Tk()
cd = CodeView(root)
cd.pack()
cd.insert("end", "\"\"\"\nThis is a test\n\n\n\n\"\"\"")
cd.insert("end", "\n\nprint()")
root.mainloop()