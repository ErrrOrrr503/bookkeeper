"""
Gettext import and initialization
"""
# following 3 lines will be executed on import and setup gettext.
import gettext
gettext.bindtextdomain('bookkeeper', 'bookkeeper/locale')
gettext.textdomain('bookkeeper')

_ = gettext.gettext