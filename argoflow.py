#!/usr/bin/env python

"""
argoflow.py
===========

This script just sets up the distribution from
environment variables or .env files. It *does not*
touch secrets, as those are delegated to the argoflow_secrets.py
file in the secrets folder.

This script has a cli (argparse), so just use `-h` to see the up-to-date
commands. In terms of modifying this script, you probably need to do two things:

If you're


"""


import jinja2
from jinja2 import Template, FileSystemLoader, StrictUndefined
from pydantic import BaseSettings, ValidationError
import os
from os import environ
from os.path import exists
import sys
from argparse import ArgumentParser, Namespace
from dotenv import dotenv_values
from typing import Dict, Optional
import shutil

import warnings

DISTRIBUTION = 'distribution'
TEMPLATE = 'template/'

jinja_env = jinja2.Environment(
    loader=FileSystemLoader('.'),
    variable_start_string='<<',
    variable_end_string='>>',
    undefined=StrictUndefined

)

# https://stackoverflow.com/a/287944
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# Helper function
def templatify(source: str, dest: Optional[str], variables: Dict) -> Optional[str]:
    if dest is not None:
        os.makedirs(os.path.dirname(dest), exist_ok=True)

    try:
        template = jinja_env.get_template(source)
        s = template.render(**variables)
    except Exception as e:
        with open(source) as f:
            print('# ######################')
            print('# Error processing file:')
            print('# ######################')
            print(f.read())
        raise e

    if dest is None:
        return s

    with open(destination, 'w') as f:
        print(f"# Wrote {destination}", file=sys.stderr)
        f.write(s)

###                                88
###    ,d                          88
###    88                          88
###  MM88MMM  ,adPPYba,    ,adPPYb,88   ,adPPYba,
###    88    a8"     "8a  a8"    `Y88  a8"     "8a
###    88    8b       d8  8b       88  8b       d8
###    88,   "8a,   ,a8"  "8a,   ,d88  "8a,   ,a8"
###    "Y888  `"YbbdP"'    `"8bbdP"Y8   `"YbbdP"'
###


# This is just to avoid defining some stuff
class Dummy():

    # This is for magic stuff
    def __init__(self, prefix: str):
        self.prefix = prefix

    def __getattribute__(self, key):
        this_prefix = object.__getattribute__(self, 'prefix')
        if key == 'prefix':
            return this_prefix

        return Dummy(prefix='.'.join([this_prefix, key]))

    def __str__(self):
        s = '<< %s >>' % self.prefix.rstrip('.')
        print(f"{bcolors.WARNING}WARNING: {s} is a DUMMY!{bcolors.ENDC}")
        if self.prefix == '':
            return '<< DUMMY >>'
        else:
            return s

    def schema():
        return {'properties':{}}

###
###
###  8b       d8  ,adPPYYba,  8b,dPPYba,  ,adPPYba,
###  `8b     d8'  ""     `Y8  88P'   "Y8  I8[    ""
###   `8b   d8'   ,adPPPPP88  88           `"Y8ba,
###    `8b,d8'    88,    ,88  88          aa    ]8I
###      "8"      `"8bbdP"Y8  88          `"YbbdP"'
###


class GitRepo(BaseSettings):
    url: str
    target_revision: str = 'master'

    class Config:
        env_prefix = 'ARGOFLOW_GIT_REPO_'


class Domain(BaseSettings):
    root: str

    dashboard: str = 'kubeflow'
    serving: str = 'serving'
    argocd: str = 'argocd'
    auth: str = 'auth'
    grafana: str = 'grafana'
    kiali: str = 'kiali'
    kubecost: str = 'kubecost'

    class Config:
        env_prefix = 'ARGOFLOW_DOMAIN_'


class CertManager(BaseSettings):
    email_user: str = 'info'
    email_domain: str
    server: str = 'https://acme-staging-v02.api.letsencrypt.org/directory'

    class Config:
        env_prefix = 'ARGOFLOW_CERT_MANAGER_'


class CloudFlare(BaseSettings):
    email: str

    class Config:
        env_prefix = 'ARGOFLOW_CLOUDFLARE_'








if __name__ == '__main__':

    parser = ArgumentParser(
        description='Generate the Argoflow distribution from the template.'
    )
    parser.add_argument(
        '--env-file',
        type=str,
        help='A .env file to read from'
    )
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Overwrite the existing distribution folder if it exists'
    )
    parser.add_argument(
        '-v', '--print_vars',
        action='store_true',
        help='Overwrite the existing distribution folder if it exists'
    )
    args = parser.parse_args()

    # Overwrite folder?
    if exists(DISTRIBUTION):
        if args.force:
            print("# removing existing distribution folder", file=sys.stderr)
            shutil.rmtree(DISTRIBUTION)
        else:
            print("distribution folder already exists and --force not set. Exiting.", file=sys.stderr)
            sys.exit(1)

    # Load the env file
    if args.env_file is not None:
        config = dotenv_values(args.env_file)
        for (k,v) in config.items():
            if k in environ:
                print(f"# {k} is in {args.env_file}, ", file=sys.stderr)
                print("# but we won't override env vars", file=sys.stderr)
                continue

            print(f"# Setting {k} is from {args.env_file}", file=sys.stderr)
            environ[k] = v


    # Every variable is either a Dummy
    # or a real pydantic type that
    # we'll neeed to fill
    variables = {
        # Set these!
        'git_repo': GitRepo,
        'domain': Domain,
        'cert_manager': CertManager,
        'cloudflare': CloudFlare,
        # These are TODO
        'rds': Dummy,
        's3': Dummy,
        # These are actually secrets
        'profile': Dummy,
        'dex': Dummy,
        'keycloak': Dummy,
        'oidc': Dummy,
    }

    for (k, v) in variables.items():
        if v is Dummy:
            # { key: Dummy } => { key: Dummy(key) }
            variables[k] = v(k)

    # Get all the "ARGOFLOW_BLAH=<< blah >>" strings
    help_message = ""
    for (k,v) in variables.items():
        if isinstance(v, Dummy):
            continue

        for (kk,vv) in v.schema()['properties'].items():
            key = '.'.join([k,kk])
            env_var = list(vv['env_names'])[0].upper()
            help_message += f'{env_var}=<< {key} >>\n'
    help_message += bcolors.ENDC

    # User just wants to see the variables.
    if args.print_vars:
        print(f'{bcolors.OKGREEN}{help_message}{bcolors.ENDC}')
        sys.exit(0)

    # Instantiate everything
    try:
        # We define the un-instantiated variables above so that its
        # easier to print nice debugging messages. Here we instantiate
        # everything and see if anything went wrong.
        for var in variables:
            if isinstance(variables[var], type):
                variables[var] = variables[var]()
            elif isinstance(variables[var], Dummy):
                pass
            else:
                print(variables[var])
                raise Exception("This shouldn't happen.")

    except ValidationError as e:
        print(f'{bcolors.FAIL}\n', file=sys.stderr)
        print('# Failed to get the Argoflow parameters.', file=sys.stderr)
        print('# Did you set the necessary ENV vars or use --env-file [file.env]?', file=sys.stderr)
        print(f'# You need these:\n', file=sys.stderr)
        print(help_message, file=sys.stderr)
        print(file=sys.stderr)
        print(f'{bcolors.ENDC}\n', file=sys.stderr)
        raise e


    # Copy and template everything!
    for (dirpath, dirnames, filenames) in os.walk(TEMPLATE):
        for filename in filenames:
            relpath = os.path.relpath(dirpath, TEMPLATE)
            source = os.sep.join([dirpath, filename])
            destination = os.sep.join([DISTRIBUTION, relpath, filename])
            templatify(source, destination, variables)
