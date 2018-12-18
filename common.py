#!/usr/bin/env python3

import types
from typing import Union
from abc import ABC, abstractmethod

import tkinter as tk
from tkinter import ttk


def float_or_zero(value):
    try:
        return float(value)
    except ValueError:
        return float(0)


def center_toplevel(toplevel: tk.Toplevel):
    toplevel.nametowidget('.').eval('tk::PlaceWindow %s center' % toplevel.winfo_toplevel())


class FloatValidator:
    '''
    Used to validate tkinter entry widgets accepting only input that still results in a float.
    Inherit this to add the validate_float_entry method to your class.

    '''
    def validate_float_entry(self, action: str, value: str,
        widget_obj_name: str, min_value_or_attrname: str, max_value_or_attrname: str) -> bool:
        '''
        More on entry validation:
            http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/entry-validation.html
        Example:
            import tkinter as tk

            class MyClass(FloatValidator):
                def some_method(self):
                    field = tk.Entry()
                    validator = field.register(self.validate_float_entry)
                    field.configure(validate='all')
                    field.configure(validatecommand=(validator, '%d', '%P', 'field', 0, 100))
        Note:
            All parameters are coerced to string by tkinter. Therefore widget_obj_name must be
            a string, so it's 'field' in the above example.
            min_value_or_attrname can max_value_or_attrname can be numbers (will be coerced),
            a string that can be converted to a float or a name of an instance attribute.
            If the attribute is a method, it will be called without any parameters and the return
            value will be used as the min or max value respectively. Lambdas obviously work, too.
        '''

        entry_widget = getattr(self, widget_obj_name)

        # Try to convert to float to see if it's a value, if can't, treat it as an attribute name
        # and get it with getattr from self.
        try:
            min_value =  float(min_value_or_attrname)
        except ValueError:
            min_value = getattr(self, min_value_or_attrname)
        try:
            max_value = float(max_value_or_attrname)
        except:
            max_value = getattr(self, max_value_or_attrname)
        
        # If the values are in fact callables, call them.
        if callable(min_value):
            min_value = min_value()
        if callable(max_value):
            max_value = max_value()
        
        # Raise error if min or max is still not a number, like if calling didn't return a number
        if not isinstance(min_value, (float, int)):
            raise TypeError('min_value_or_attrname can\'t be resolved to a number')
        if not isinstance(max_value, (float, int)):
            raise TypeError('max_value_or_attrname can\'t be resolved to a number')

        # Update field to min_value if unfocused when blank or value is smaller than min_value.
        # This essentially prevents entering values smaller than min_value while enabling
        # proper deletion of the input and entering numbers initially smaller than min_value.
        if action == '-1': # focus change action
            if not value or float_or_zero(value) < float(min_value):
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, float(min_value))

        # Return validation result
        # Will only let changes to the entry field that still result in a float.
        # The number also has to be within min/max bounds.
        if value:
            try:
                float(value)
                if float(value) > float(max_value):
                    # Only prevent values over max_value.
                    # Validating against min_value will happen above.
                    return False
                else:
                    return True
            except (TypeError, ValueError):
                return False
        else:
            # Allow empty string, so we can delete the contents completely
            return True


class CreateToolTip:
    # Source: https://stackoverflow.com/questions/3221956/how-do-i-display-tooltips-in-tkinter
    ''' Create a tooltip for a given widget. '''
    def __init__(self, widget: tk.Widget, text='widget info'):
        self.waittime = 500 #ms
        self.wraplength = 180 #pixels
        self.widget = widget
        self.text = text
        self.widget.bind('<Enter>', self.enter)
        self.widget.bind('<Leave>', self.leave)
        self.widget.bind('<ButtonPress>', self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox('insert') # pylint: disable=W0612
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.hidetip() # added this as a comment suggested
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry('+%d+%d' % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background='#ffffff', relief='solid', borderwidth=1,
                       wraplength = self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()


class BaseDialog(ABC):
    ''' Abstract Base Class for dialogs. '''
    def __init__(self, parent: tk.Widget, callback: types.FunctionType, window_title: str,
            text: str, destroy_on_close: bool=True, **kwargs):
        self.parent = parent

        self.toplevel = tk.Toplevel(self.parent)
        self.toplevel.title(window_title)
        self.toplevel.resizable(False, False)
        self.toplevel.protocol('WM_DELETE_WINDOW', lambda: self.close(False, **kwargs))
        self.toplevel.focus()

        self.callback = callback
        self.destroy_on_close = destroy_on_close

        self.frame = ttk.Frame(self.toplevel)
        self.frame.grid(padx=20, pady=5)

        self.label = ttk.Label(self.frame, text=text)
        self.label.grid(row=0, column=0, columnspan=2, pady=10)

        self.ok_button = ttk.Button(self.frame, text='OK',
            command=lambda: self.close(True, **kwargs))
        self.ok_button.grid(row=10, column=0, pady=16, sticky=tk.W+tk.E)
        self.ok_button.bind('<Return>', lambda event: self.close(True, **kwargs))

        self.configure_widgets(**kwargs)

        center_toplevel(self.toplevel)
    
    def configure_widgets(self, **kwargs):
        ''' Override this to add and reconfigure widgets in the dialog. Use self.frame as parent.
        Use the grid geometry manager. Row 0 is the main label, row 10 is the buttons' row.
        Column 0 in row 10 is the self.ok_button. '''
        pass
    
    @abstractmethod
    def close(self, ok_clicked: bool=False, **kwargs):
        ''' Override this to call self.callback somehow.
        Then super().close(ok_clicked, **kwargs) to close the dialog. '''

        if self.destroy_on_close:
            self.toplevel.destroy()
        else:
            self.toplevel.withdraw()


class OkDialog(BaseDialog):
    def close(self, ok_clicked: bool, **kwargs):
        self.callback(ok_clicked, **kwargs)

        super().close()


class YesNoDialog(BaseDialog):
    def configure_widgets(self, **kwargs):
        self.ok_button.configure(text='Yes', width=15)
        self.no_button = ttk.Button(self.frame, text='No', width=15,
            command=lambda: self.close(False, **kwargs))
        self.no_button.grid(row=10, column=1, sticky=tk.E)
        self.ok_button.grid(row=10, column=0, sticky=tk.W)

    def close(self, ok_clicked: bool, **kwargs):
        self.callback(ok_clicked, **kwargs)

        super().close()


class FloatEntryDialog(BaseDialog, FloatValidator):
    def configure_widgets(self, **kwargs):
        self.entry_value = tk.StringVar()
        self.entry_value.set(kwargs['default_value'])

        self.entry = ttk.Entry(self.frame, textvariable=self.entry_value)
        self._entry_validator = self.entry.register(self.validate_float_entry)
        self.entry.configure(validate='all',
            validatecommand=(self._entry_validator, '%d', '%P', 'entry',
                kwargs['min_value'], kwargs['max_value']))
        self.entry.grid(row=1, columnspan=2, pady=10)
        self.entry.focus()

        self.ok_button.configure(text='OK')
        
        self.no_button = ttk.Button(self.frame, text='Cancel', width=10,
            command=lambda: self.close(False))
        self.no_button.grid(row=10, column=1, sticky=tk.W+tk.E)
    
    def close(self, ok_clicked: bool, **kwargs):
        if ok_clicked:
            self.callback(float(self.entry.get()))
        
        super().close()