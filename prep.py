#! /usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright &copy; 2016 Ben Blazak <bblazak@fullerton.edu>
# Released under the [MIT License] (http://opensource.org/licenses/MIT)
# -----------------------------------------------------------------------------

import re
import sys
import textwrap

# open `sys.stdin` with universal newlines
sys.stdin = open( sys.stdin.fileno() )

# -----------------------------------------------------------------------------

class Prep:

    class Error(Exception):
        pass

    def __init__(self, outfile=sys.stdout):
        self.DEBUG = False

        self.outfile = outfile

        # .....................................................................

        def _print(esc, **kwargs):
            self.printinline( eval( esc, globals() ) )

        def _exec(esc, **kwargs):
            exec( textwrap.dedent(esc), globals() )

        def _print_or_exec(esc, **kwargs):
            try:
                _print(esc, **kwargs)
            except:
                _exec(esc, **kwargs)

        def _print_or_exec_block(esc, **kwargs):
            s0 = re.sub( r'\S*$', '', kwargs['e0'].rstrip() )
            s1 = re.sub( r'^\S*', '', kwargs['d1'].lstrip() )

            n0 = s0.count('\n')
            n1 = s1.count('\n')

            if n0 == 0:
                if s0 != '':
                    self.printinline( ' ' )
            elif n0 == 1:
                    self.printinline( '\n' )
            else:
                self.printinline( '\n\n' )

            position = 0
            if self.outfile.seekable():
                position = self.outfile.tell()

            _print_or_exec(esc, **kwargs)

            if self.outfile.seekable() and position != self.outfile.tell():
                if n1 == 0:
                    if s1 != '':
                        self.printinline( ' ' )
                elif n1 == 1:
                    self.printinline( '\n' )
                else:
                    self.printinline( '\n\n' )
            else:
                if n0 == 0:
                    if n1 == 0:
                        if s0 == '' and s1 != '':
                            self.printinline( ' ' )
                    elif n1 == 1:
                        self.printinline( '\n' )
                    else:
                        self.printinline( '\n\n' )
                elif n0 == 1:
                    if n1 > 1:
                        self.printinline( '\n' )

        # .....................................................................

        _delimiter_default = [
            (
                re.compile(r'\(\(\(\n?'), re.compile(r'\n?\)\)\)'),
                { 'nest': True, }
            ),
            (
                re.compile(r'\('), re.compile(r'\)'),
                { 'nest': True, }
            ),
        ]

        # .....................................................................

        self.escape = [

            ( re.compile(r'!'), {
                'delimiter': _delimiter_default,
                'function': _print_or_exec,
            } ),

            ( re.compile(r'!p(rint)?'), {
                'delimiter': _delimiter_default,
                'function': _print,
            } ),

            ( re.compile(r'!e(xec)?'), {
                'delimiter': _delimiter_default,
                'function': _exec,
            } ),

            # .................................................................

            ( re.compile(r'\s*!c(omment)?'), {
                'delimiter': _delimiter_default + [
                    (
                        re.compile(r'\.\.'), re.compile(r'(?=\n)'),
                        { 'nest': False, }
                    ),
                ],
                'function': lambda esc, **kwargs: self.printinline(
                    re.sub( r'[^\n]*$', '', kwargs['e0'] ) ),
            } ),

            ( re.compile(r'!(dnl|deletenewline)'), {
                'delimiter': [
                    ( d[0], re.compile(d[1].pattern + r'\n?'), d[2] )
                    for d in _delimiter_default
                ] + [
                    (
                        re.compile(r'\.\.'), re.compile(r'\n'),
                        { 'nest': False, }
                    ),
                ],
                'function': lambda esc, **kwargs: None,
            } ),

            ( re.compile(r'\s*!i(nline)?'), {
                'delimiter': [
                    ( d[0], re.compile(d[1].pattern + r'\s*'), d[2] )
                    for d in _delimiter_default
                ],
                'function': _print_or_exec,
            } ),

            ( re.compile(r'\s*!b(lock)?'), {
                'delimiter': [
                    ( d[0], re.compile(d[1].pattern + r'\s*'), d[2] )
                    for d in _delimiter_default
                ],
                'function': _print_or_exec_block,
            } ),

            # .................................................................

            ( re.compile(r'!\w*'), {
                'delimiter': _delimiter_default,
                'function': lambda esc, **kwargs: self.error(
                    'Unknown escape: ' + kwargs['e0'] ),
            } ),

            ( re.compile(r'!\w*'), {
                'delimiter': _delimiter_default + [
                    (
                        re.compile(r'\.\.\s*'), re.compile(r'(?:\n)'),
                        { 'nest': False, }
                    ),
                ],
                'function': lambda esc, **kwargs: self.error(
                    'Unknown escape+delimiter: ' + kwargs['e0']+kwargs['d0'] ),
            } ),

        ]

    def print(self, *args, **kwargs):
        print( *args, file=self.outfile, **kwargs )

    def printinline(self, *args, **kwargs):
        print( *args, end='', **kwargs )

    def error(self, msg):
        raise self.Error(msg)

    def input(self, path):
        self.prep(open(path).read())

    def prep(self, _in):
        '''
        `_in` must be a string
        '''

        def match(regex, pattern):
            match = regex.match(pattern)
            if match is not None:
                return match.group()
            else:
                return None

        while len(_in):
            for e in self.escape:

                e0 = match(e[0], _in)
                if e0 is not None:

                    if self.DEBUG:
                        self.printinline( '<escape=' + e0 + '>' )

                    for d in e[1]['delimiter']:

                        d0 = match(d[0], _in[len(e0):])
                        if d0 is not None:

                            if self.DEBUG:
                                self.printinline( '<delimiter=' + d0 + '>' )

                            d[2]['count'] = 1

                            esc = ''  # the escaped string
                            _in = _in[len(e0)+len(d0):]

                            # collect characters, until ending delimiter
                            while True:
                                if not len(_in):
                                    self.error('Escape reached EOF')

                                if d[2]['nest']:
                                    d0 = match(d[0], _in)
                                    if d0 is not None:
                                        d[2]['count'] += 1

                                d1 = match(d[1], _in)
                                if d1 is not None:
                                    d[2]['count'] -= 1

                                if d[2]['count'] > 0:
                                    esc += _in[:1]
                                    _in = _in[1:]
                                else:
                                    break;

                            _in = _in[len(d1):]  # remove end delimiter

                            if self.DEBUG:
                                self.printinline( '<esc=' + esc + '>' )
                                self.printinline( '<delimiter=' + d1 + '>' )
                            else:
                                e[1]['function'](esc, e0=e0, d0=d0, d1=d1)
                                break

                    else:  # if we didn't break out of this loop
                        continue
                    break

            else:
                self.printinline( _in[:1] )
                _in = _in[1:]

# -----------------------------------------------------------------------------

prep = Prep()

if __name__ == '__main__':
    usage = (
        'USAGE:\n'
        + '    ' + sys.argv[0] + ' --help\n'
        + '    cat in_file [in_file ...] | ' + sys.argv[0] + ' > out_file\n'
    )

    if '--help' in sys.argv:
        print(usage)
        if len(sys.argv) != 2:
            exit(1)
        else:
            exit(0)

    if len(sys.argv) != 1:
        print(usage)
        exit(1)

    prep.prep(sys.stdin.read())

