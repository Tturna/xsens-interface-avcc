# https://dearpygui.readthedocs.io/en/latest/
import dearpygui.dearpygui as dpg

def log(dpg_item: str, message: str, append: bool = True) -> None:
    if (append):
        message += f'\n{dpg.get_value(dpg_item)}'

    dpg.set_value(dpg_item, f'{message}\n')
    print(message)