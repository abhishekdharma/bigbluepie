#!/usr/bin/env python

#for Python 2
import Tkinter as tk
import ttk
#for Python 3
#import tkinter as tk
#from tkinter import ttk
from myplayer3 import BluePlayer
import platform
tkTop = 0
tkButtonQuit = 0
tkDecButton = 0 
tkPrevButton = 0
tkNxtButton = 0
tkPausButton = 0
tkPlayButton = 0
bp_object = 0
songInfo = 0
callInfotxt = 0

def quit():
    global tkTop
    tkTop.destroy()

def refreshApp():
    global tkTop
    tkTop.update()
    return True

def gui_init(bp_object1): 
    global tkTop
    global bp_object
    global songInfo
    global callInfotxt
    bp_object = bp_object1
    tkTop = tk.Tk()
    print("GUI Init")
    tkTop.geometry('480x320')
    maxCols = 50; 
    notebook = ttk.Notebook(tkTop)
    fr_phone = ttk.Frame(notebook)
    fr_music = ttk.Frame(notebook)
    notebook.add(fr_phone, text='Phone')
    notebook.add(fr_music, text='Music')
    notebook.grid(columnspan=maxCols)
 
    tkButtonQuit = tk.Button(
        tkTop,
        text="Quit",
        command=quit)
    tkButtonQuit.grid(row=4)
  
    tkAnsButton = tk.Button(
        fr_phone,
        text="Ans", command=bp_object.answer)
    tkAnsButton.grid(row=0, column=0)
#tkAnsButton.pack(side = tk.LEFT)
   
    tkDecButton = tk.Button(
        fr_phone,
        text="Dec", command=bp_object.end_call)
    tkDecButton.grid(row=0, column=9)
#tkDecButton.pack(side = tk.RIGHT)

    callInfotxt = tk.Text(fr_phone, height=4, width=30);
    callInfotxt.grid(row=2, column=0, columnspan=maxCols)
    #infotxt.pack(side = tk.BOTTOM);
    callInfotxt.insert(tk.END, "Just a text Widget\nin two lines\n")
 
    tkPrevButton = tk.Button(
        fr_music,
        text="<<", command=bp_object.previous)
    #tkPrevButton.pack(side = tk.LEFT)
    tkPrevButton.grid(row=0, column=1)

    tkNxtButton = tk.Button(
        fr_music,
        text=">>", command=bp_object.next)
    tkNxtButton.grid(row=0, column=3)
    #tkNxtButton.pack(side = tk.LEFT)

    tkPlayButton = tk.Button(
        fr_music,
        text=">", command=bp_object.play)
    tkPlayButton.grid(row=0, column=5)
    #tkPlayButton.pack(side = tk.LEFT)

    tkPausButton = tk.Button(
        fr_music,
        text="||", command=bp_object.pause)
    tkPausButton.grid(row=0, column=7)
    #tkPausButton.pack(side = tk.LEFT)

    songInfo = tk.Text(fr_music, height=4, width=30);
    #songInfo.pack(side = tk.BOTTOM, fill=tk.X);
    songInfo.grid(row=4, column=0, columnspan=maxCols)
    songInfo.insert(tk.END, "Just a text Widget\nin two lines\n")
#    tk.mainloop()

def update_music_display(lines):
    global songInfo
    display = ""
    songInfo.delete(1.0, tk.END)
    for i, line in enumerate(lines):
        if i >= 3: break 
        display = lines[i] + "\n"
    songInfo.insert(tk.END, display) 

def update_phone_display(state, text):
    global callInfotxt
    display = state + text
    callInfotxt.delete(1.0, tk.END)
    callInfotxt.insert(tk.END, display) 
