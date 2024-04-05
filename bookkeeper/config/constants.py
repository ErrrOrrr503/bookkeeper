"""
File, containing constants.

It may be ok to hardcore a unique str in view.
(view can contain a lot of strings)
But not ok to rely on equal spelling of repeated values.

The difference from config is that it's not planned that user may alter this.
"""
from bookkeeper.locale.gettext import _

TOP_CATEGORY_NAME = _('-')

# a better way can be enum, but enum has issues with types
# i.e. StrEnum element is str, ok, but, str in StrEnum wold not work.
BUDGET_DAILY = 'Daily'
BUDGET_WEEKLY = 'Weekly'
BUDGET_MONTHLY = 'Monthly'

RGB_RESET_COLOR = (-1, -1, -1)
RGB_BUDGET_WARNING = (150, 150, 0)
RGB_BUDGET_OVERRUN = (150, 0, 0)
RGB_BUDGET_DEFAULT = RGB_RESET_COLOR
