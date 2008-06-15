"""
General functions that don't fit neatly under any given category.
"""
import os
import textwrap
from src import session_mgr

def wildcard_to_regexp(instring):
    """
    Converts a player-supplied string that may have wildcards in it to regular
    expressions. This is useful for name matching.

    instring: (string) A string that may potentially contain wildcards (* or ?).
    """
    regexp_string = ""

    # If the string starts with an asterisk, we can't impose the beginning of
    # string (^) limiter.
    if instring[0] != "*":
        regexp_string += "^"

    # Replace any occurances of * or ? with the appropriate groups.
    regexp_string += instring.replace("*","(.*)").replace("?", "(.{1})")

    # If there's an asterisk at the end of the string, we can't impose the
    # end of string ($) limiter.
    if instring[-1] != "*":
        regexp_string += "$"

    return regexp_string

def cmd_check_num_args(session, arg_list, min_args, errortext="Missing arguments!"):
    """
    Check a player command's splitted argument list to make sure it contains
    the minimum allowable number of arguments.
    """
    if len(arg_list) < min_args+1:
        session.msg(errortext)
        return False
    return True
    
def time_format(seconds, style=0):
    """
    Function to return a 'prettified' version of a value in seconds.
    
    Style 0: 1d 08:30
    Style 1: 1d
    Style 2: 1 day, 8 hours, 30 minutes, 10 seconds
    """
    if seconds < 0:
        seconds = 0
    else:
        # We'll just use integer math, no need for decimal precision.
        seconds = int(seconds) 
        
    days      = seconds / 86400
    seconds -= days * 86400
    hours     = seconds / 3600
    seconds -= hours * 3600
    minutes  = seconds / 60
    seconds -= minutes * 60
    
    if style is 0:
        """
        Standard colon-style output.
        """
        if days > 0:
            retval = '%id %02i:%02i' % (days, hours, minutes,)
        else:
            retval = '%02i:%02i' % (hours, minutes,)
        
        return retval
    elif style is 1:
        """
        Simple, abbreviated form that only shows the highest time amount.
        """
        if days > 0:
            return '%id' % (days,)
        elif hours > 0:
            return '%ih' % (hours,)
        elif minutes > 0:
            return '%im' % (minutes,)
        else:
            return '%is' % (seconds,)
            
    elif style is 2:
        """
        Full-detailed, long-winded format.
        """
        days_str = hours_str = minutes_str = ''
        if days > 0:
            days_str = '%i days, ' % (days,)
        if days or hours > 0:
            hours_str = '%i hours, ' % (hours,)
        if hours or minutes > 0:
            minutes_str = '%i minutes, ' % (minutes,)
        seconds_str = '%i seconds' % (seconds,)
        
        retval = '%s%s%s%s' % (days_str, hours_str, minutes_str, seconds_str,)
        return retval  

def announce_all(message, with_ann_prefix=True):
    """
    Announces something to all connected players.
    """
    if with_ann_prefix:
        prefix = 'Announcement:'
    else:
        prefix = ''

    for session in session_mgr.get_session_list():
        session.msg('%s %s' % (prefix, message))

def word_wrap(text, width=78):
    """
    Wrap text to a certain number of characters.

    text: (str) The text to wrap.
    width: (int) The number of characters to wrap to.
    """
    return '\r\n'.join(textwrap.wrap(text, width))
    
def host_os_is(osname):
    """
    Check to see if the host OS matches the query.
    """
    if os.name == osname:
        return True
    return False