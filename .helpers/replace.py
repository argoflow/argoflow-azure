#!/bin/python3

"""
This script lets you replace variable occurrences like `$ARGOFLOW_GIT_URL`
using a conf file. However, this also applies a default behaviour where
ENV vars get precedence over the conf file. I.e.

if      ENV_VAR[X] exists, replace X with ENV_VAR[X] in file F
else if CONF[X] exists,    replace X with CONF[X] in file F
else do nothing.

This is different than the
"""

from os import environ
import re
import sys
import argparse

parser = argparse.ArgumentParser(description='Find and replace vars from a source file, defaulting to ENV vars')
parser.add_argument('inputfile', type=str, help='an integer for the accumulator')
parser.add_argument('-c', '--config', help='Config file to fallback on if ENV var does not exist')
parser.add_argument('-i', '--inplace', action='store_true', help='Modify the file in-place')

args = parser.parse_args()

def parse_conf(conffile):
    """ Arguably should use the configparser library """
    d = {}
    with open(conffile) as f:
        lines = [ line for line in f.readlines() if '=' in line ]
        for line in lines:
            splits = line.split('=')
            d[splits[0]] = '='.join(splits[1:]).strip()
    return d

# Grab vars if they exist
if args.config:
    d = { 
        f'ARGOFLOW_{k}' : v 
        for (k,v) in parse_conf(args.config).items()
    }
else:
    d = {}

# Overlay with all ENV vars ARGOFLOW_*
for k in environ:
    if k.startswith('ARGOFLOW_'):
        d[k] = environ[k]

with open(args.inputfile) as f:
    text = f.read()
    for (k,v) in d.items():
        text = text.replace('$' + k, v)

# Overwrite the file
if not args.inplace:
    print(text)
else:
    with open(args.inputfile, 'w') as f:
        f.write(text) 
