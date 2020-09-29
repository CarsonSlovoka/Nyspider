__all__ = ('highlight_print', 'cached_property', 'green_text')

import sys
import platform

is_py3 = sys.version_info[0] == 3
is_64bits = sys.maxsize > 2 ** 32

is_win = sys.platform.startswith('win')
is_win_10 = is_win and (platform.win32_ver()[0] == '10')
is_cygwin = sys.platform == 'cygwin'
is_darwin = sys.platform == 'darwin'  # Mac OS X

# Unix platforms
is_linux = sys.platform.startswith('linux')
is_solar = sys.platform.startswith('sun')  # Solaris
is_aix = sys.platform.startswith('aix')
is_freebsd = sys.platform.startswith('freebsd')
is_hpux = sys.platform.startswith('hp-ux')

is_unix = is_linux or is_solar or is_aix or is_freebsd or is_hpux

"""
NEW_LINE_SIGN = ['\r\n' if is_win else
                 '\n' if is_unix else '\r']  # windows: \r\n, unix: \n, max: \r
"""
NEW_LINE_SIGN = chr(10)

try:
    import colorama
    from colorama import Fore, Back

    colorama.init(autoreset=True)
except ImportError as _e:
    colorama = _e

    class AnsiFore:
        __slots__ = ()

        def __getattr__(self, item):
            return ""


    class AnsiBack:
        __slots__ = ()

        def __getattr__(self, item):
            return ""

    Fore = AnsiFore()
    Back = AnsiBack()


def highlight_print(msg: str, fore: Fore = Fore.RED, back: Back = Back.LIGHTYELLOW_EX, print_flag: bool = True) -> str:
    if not isinstance(colorama, ImportError):
        msg = back + fore + msg
    if print_flag:
        print(msg)
    return msg + Fore.RESET


def green_text(text):
    return highlight_print(text, fore=Fore.GREEN, back="", print_flag=False)


if sys.version_info[0] >= 3 and sys.version_info[1] >= 8:  # py.version >= 3.8
    from Lib.functools import cached_property
else:
    cached_property = property

