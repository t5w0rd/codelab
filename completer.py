#!/usr/bin/env python3

import readline
import logging
import os


class Completer:
    def __init__(self, keys_generator):
        self.matches = []
        self.keys = keys_generator

    def complete(self, text, state):
        response = None
        if state == 0:
            if text:
                matches = [key for key in self.keys() if key and key.startswith(text)]
            else:
                matches = list(self.keys())

            matches.append(None)
            self.matches = matches

        return self.matches[state]


def input_line(prompt=''):
    try:
        line = input(prompt)
    except KeyboardInterrupt:
        return False
    except Exception:
        return False

    return line


if __name__ == '__main__':
    HISTORY_FILENAME = '{}/.completer.history'.format(os.environ['HOME'])

    keys =  ["one", "two", "three", "exit"]
    def keys_generator():
        for key in keys:
            yield key

    # Register our completer function
    readline.set_completer(Completer(keys_generator).complete)

    # Use the tab key for completion
    readline.parse_and_bind('tab: complete')

    # Prompt the user for text
    if os.path.exists(HISTORY_FILENAME):
        readline.read_history_file(HISTORY_FILENAME)

    while True:
        line = input_line('>> ')
        if line is False:
            break

        if line == 'exit':
            break

        if line:
            print('input: ', line)

    readline.write_history_file(HISTORY_FILENAME)

