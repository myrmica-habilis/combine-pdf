import os

# Paths

# Dialog texts

# TODO: make a nicer Help and About dialog
HELP_TEXT = ('In the "Pages" input field, enter single page numbers'
             ' or ranges of page numbers.\n'
             'Example: 1, 3-5, 8\n'
             'will produce page sequence 1, 3, 4, 5, 8\n\n'
             'Order is observed.\n'
             'Example: 2-4, 1\n'
             'will produce page sequence 2, 3, 4, 1\n\n'
             'Repeating is allowed.\n'
             'Example: 1-3, 2, 1-2\n'
             'will produce page sequence 1, 2, 3, 2, 1, 2')

ABOUT_TEXT = ('CombinePDF\n\n'
              'version 0.8.7\n\n'
              '10 November 2019')
