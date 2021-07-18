#!/usr/bin/env python

# Jump to "VARS" to do actual configuration

import base64
import getpass
import json
import secrets
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from enum import Enum
from os import environ, makedirs, urandom
from os.path import dirname, exists, join, abspath
from subprocess import PIPE, STDOUT, Popen
from typing import Dict, List, Optional, Union

import jinja2
import yaml
from dotenv import dotenv_values
from jinja2 import FileSystemLoader, Template, StrictUndefined
from passlib.hash import bcrypt
from pydantic import BaseModel, BaseSettings

# For Pydantic parsing
ENV_PREFIX = 'ARGOFLOW_'
DISTRIBUTION = abspath('../distribution/')

### Helpers
jinja_env = jinja2.Environment(
    loader=FileSystemLoader(DISTRIBUTION),
    variable_start_string='<<',
    variable_end_string='>>',
    undefined=StrictUndefined
)

def rand_hex(length: int):
    return base64.urlsafe_b64encode(urandom(length)).decode()

def rand_base64(length: int):
    return secrets.token_hex(length)

def kubectl_yaml(args: List[str]):
    """ Call kubectl subprocess """
    return subprocess.run(
        ['kubectl', 'create', '--dry-run=client', '-o', 'yaml'] + args,
        stdout=subprocess.PIPE
    ).stdout.decode('utf-8')

def templatify(source: str, dest: Optional[str], variables: Dict) -> Optional[str]:
    if dest is not None:
        os.makedirs(os.path.dirname(dest), exist_ok=True)

    try:
        template = jinja_env.get_template(source)
        s = template.render(**variables)
    except Exception as e:
        with open(join(DISTRIBUTION,source)) as f:
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

def write(text: str, dest: Optional[str], overwrite: bool = False) -> None:
    """ A write function that ensures folder exists """
    if dest is None:
        print(text)
        return

    makedirs(dirname(dest), exist_ok=True)

    if exists(dest):
        if overwrite == False:
            print(f"# File {dest} exists, not overwriting", file=sys.stderr)
            return
        else:
            print(f"# Overwriting existing file {dest}", file=sys.stderr)

    with open(dest, 'w') as f:
        f.write(text)

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





### end of helpers


###
### %%%%%%  %%  %%  %%%%%   %%%%%%   %%%%
###   %%     %%%%   %%  %%  %%      %%
###   %%      %%    %%%%%   %%%%     %%%%
###   %%      %%    %%      %%          %%
###   %%      %%    %%      %%%%%%   %%%%
###


class ArgoflowSettings(BaseSettings):
    """
    All our settings can be derived from the
    ARGOFLOW_{var} environment variables.
    """
    class Config:
        case_sensitive = True
        env_prefix = ENV_PREFIX

    @classmethod
    def user_entered(cls):
        """ A method that uses user interaction to get values """
        raise NotImplementedError

    # We named the variables ALL_CAPS,
    # but lets support lower case, too
    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return object.__getattribute__(self, name.upper())


class Secret(BaseModel):
    name: str
    namespace: str
    data: Union[Dict[str,str], str]
    filename: Optional[str]

    def __str__(self):
        """ Create the Kubernetes Secret yaml. """
        # If the data is a dict, then easy-peasy
        if type(self.data) is dict:
            return kubectl_yaml(
                ['secret', 'generic', '-n', self.namespace, self.name] + [
                    f'--from-literal={k}={v}' for (k,v) in self.data.items()
                ]
            )

        # We're creating a secret from a file in this case
        # so we need it to have a name
        if self.filename is None:
            raise ValueError("Data is a string (file contents) but no filename specified.")

        # If the data is a str, then we have to pipe it
        secret_yaml = Popen(
            [
                'kubectl', 'create', '--dry-run=client', '-o', 'yaml',
                'secret', 'generic', '-n', self.namespace, self.name,
                f'--from-file={self.filename}=/dev/stdin'
            ],
            stdout=PIPE, stdin=PIPE, stderr=STDOUT
        )
        output = secret_yaml.communicate(input=self.data.encode('utf-8'))[0]
        return output.decode()

    # Just an alias to str
    def yaml(self, raw=False, ignore_errors=False):
        """ If raw is True, render the secrets as-is, not base64 encoded. """
        output = str(self)
        if raw is True:
            if type(self.data) is str:
                to_replace = [self.data]
            elif type(self.data) is dict:
                to_replace = self.data.values()
            else:
                raise Exception("data should be dict or str")
            # Replace all base64'd variables with the originals
            # This is for things like the vault argocd plugin, where the
            # value in the yamls should be <path-to-secret>,
            # not `base64("<path-to-secret>")`
            for v in to_replace:
                b64 = base64.b64encode(bytes(v, 'utf-8')).decode('utf-8')
                print(f'{v} -> {b64}')
                output = output.replace(b64, v)

        return output

    def kubeseal(self):
        """ Run Kubeseal on the text. (Requires kubeseal) """
        seal = Popen(['kubeseal'], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        seal_out = seal.communicate(input=self.yaml().encode('utf-8'))[0]
        json_data = seal_out.decode()
        return yaml.dump(json.loads(json_data))



###
### oooooo     oooo
###  `888.     .8'
###   `888.   .8'    .oooo.   oooo d8b  .oooo.o
###    `888. .8'    `P  )88b  `888""8P d88(  "8
###     `888.8'      .oP"888   888     `"Y88b.
###      `888'      d8(  888   888     o.  )88b
###       `8'       `Y888""8o d888b    8""888P'
###

class KubeflowProfile(ArgoflowSettings):
    USERNAME: str = 'argoflow'
    PASSWORD: str = rand_hex(24)
    EMAIL: str = 'argoflow@argoflow.org'
    FIRSTNAME: str = 'argo'
    LASTNAME: str = 'flow'

    @classmethod
    def user_entered(cls):
        return cls(
            USERNAME = input("Kubeflow Username: "),
            PASSWORD = getpass.getpass(prompt="Kubeflow Password: "),
            EMAIL = input("Kubeflow Email: "),
            FIRSTNAME = input("Firstname: "),
            LASTNAME = input("Lastname: ")
        )


class Grafana(ArgoflowSettings):
    GRAFANA_USERNAME: str = 'grafana'
    GRAFANA_PASSWORD: str = rand_hex(24)

    @classmethod
    def user_entered(cls):
        return cls(
            GRAFANA_USERNAME = input("Grafana Username: "),
            GRAFANA_PASSWORD = getpass.getpass(prompt="Grafana Password: ")
        )


class OAuth(ArgoflowSettings):
    COOKIE_SECRET: str = rand_base64(16)
    OIDC_CLIENT_ID: str = rand_hex(16)
    OIDC_CLIENT_SECRET: str = rand_hex(32)

    @classmethod
    def user_entered(cls):
        return cls(
            COOKIE_SECRET = rand_base64(16),
            OIDC_CLIENT_ID = getpass.getpass(prompt="OIDC Client ID: "),
            OIDC_CLIENT_SECRET = getpass.getpass(prompt="OIDC Client Secret: ")
        )

# keycloak
class Keycloak(ArgoflowSettings):
    DATABASE_PASS: str = rand_hex(16)
    POSTGRESQL_PASS: str = rand_hex(16)
    KEYCLOAK_ADMIN_PASS: str = rand_hex(16)
    KEYCLOAK_MANAGEMENT_PASS: str = rand_hex(16)

class RealmTemplate(ArgoflowSettings):
    KUBEFLOW_REALM: str

    @classmethod
    def from_oidc(cls, profile: KubeflowProfile, oidc: OAuth):
        path = join(
            'oidc-auth',
            'overlays',
            'keycloak',
            'kubeflow-realm-template.json'
        )

        templated = templatify(source=path, dest=None, variables={
            'profile': profile,
            'oidc': oidc
        })

        return cls(KUBEFLOW_REALM=templated)


# dex
class DexValues(ArgoflowSettings):
    ADMIN_PASS: str
    ADMIN_PASS_DEX: str

    @classmethod
    def from_profile(cls, profile: KubeflowProfile):
        dex_secret = bcrypt.using(rounds=12, ident='2y').hash(profile.PASSWORD)
        return cls(ADMIN_PASS=profile.PASSWORD, ADMIN_PASS_DEX=dex_secret)

class Dex(ArgoflowSettings):
    DEX_CONFIG: str

    @classmethod
    def from_values(cls, profile: KubeflowProfile, oidc: OAuth, dex: DexValues):
        path = join(
            'oidc-auth',
            'overlays',
            'dex',
            'dex-config-template.yaml'
        )

        templated = templatify(source=path, dest=None, variables={
            'profile': profile,
            'dex': dex,
            'oidc': oidc
        })

        return cls(DEX_CONFIG=templated)

# end of dex

class CloudFlare(ArgoflowSettings):
    CLOUDFLARE_API_TOKEN: str

    @classmethod
    def user_entered(cls):
        return cls(
            CLOUDFLARE_API_TOKEN = getpass.getpass(prompt="CloudFlare API Key: ")
        )


class PrivateGitRepo(ArgoflowSettings):
    GIT_HTTPS_USERNAME: str
    GIT_HTTPS_PASSWORD: str

    @classmethod
    def user_entered(cls):
        return cls(
            GIT_HTTPS_USERNAME = input("Git repo Username: "),
            GIT_HTTPS_PASSWORD = getpass.getpass(prompt="Git repo Password: ")
        )


###  ___  ___      _
###  |  \/  |     (_)
###  | .  . | __ _ _ _ __
###  | |\/| |/ _` | | '_ \.
###  | |  | | (_| | | | | |
###  \_|  |_/\__,_|_|_| |_|
###

def parse() -> Namespace:

    parser = ArgumentParser()
    parser.add_argument(
        'secret_type',
        choices=['raw', 'generated', 'vault', 'sealed'],
        help="""Choose which type of secret to generate.

        'raw' just prints the variables themselves, so you can use
        raw, then copy-paste the values into vault, and re-run
        this program with `vault` to reference the values.

        You can also use `raw` and redirect it to an env file, to
        modify and re-use with the `--env-file` flag.
        """
    )

    parser.add_argument(
        '--oauth-type',
        required=True,
        choices=['dex', 'keycloak', 'external'],
        help="Choose to use Dex or Keycloak or External provider"
    )

    parser.add_argument(
        '--cloudflare',
        action='store_true',
        help='Use CloudFlare? (Requires API Key)'
    )

    parser.add_argument(
        '--private-repo',
        action='store_true',
        help='Use Private Repo with ArgoCD?'
    )

    parser.add_argument(
        '--env-file',
        type=str,
        help='A .env file to read from'
    )

    parser.add_argument(
        '--overwrite',
        action='store_true',
        default=False,
        help='Overwrite existing files?'
    )

    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        default=False,
        help='By default, prompt the user'
    )

    args = parser.parse_args()

    return args





def setup_oauth(
        oauth_type:str,
        profile: KubeflowProfile,
        vars: Dict,
        files: Dict
    ) -> None:

    assert oauth_type in ['keycloak','dex','external']






if __name__ == '__main__':

    args = parse()

    if not exists(DISTRIBUTION):
        fail = lambda s: bcolors.FAIL + s + bcolors.ENDC
        print(fail(f'Distribtion folder "{DISTRIBUTION}" does not exist'), file=sys.stderr)
        print(fail(f'Run argoflow.py first. Exiting.'), file=sys.stderr)
        sys.exit(1)

    if args.env_file is not None:
        config = dotenv_values(args.env_file)
        for (k,v) in config.items():
            if k in environ:
                print(f"# {k} is in {args.env_file}, ", file=sys.stderr)
                print("# but we won't override env vars", file=sys.stderr)
                continue

            print(f"# Setting {k} is from {args.env_file}", file=sys.stderr)
            environ[k] = v


    # We'll define the secrets first and
    # write the secrets at the end.
    files = {}
    vars = {}

    # User, Email, etc
    # Neeed for some OIDC stuff.
    if args.interactive:
        vars['profile'] = KubeflowProfile.user_entered()
    else:
        vars['profile'] = KubeflowProfile()


    ##################
    ### OAUTH Setup
    ### (was really long, so moved into a function)
    ##################
    # Choose which type of oidc to use
    # (a poor man's switch statement)
    if args.oauth_type == 'external' and \
        f'{ENV_PREFIX}OIDC_CLIENT_ID' not in environ:
        # External oidc requires real values, not
        # generated ones.
        vars['oidc'] = OAuth.user_entered()
    else:
        vars['oidc'] = OAuth() # Fetch from ENV vars


    oidc_dest = {
        'keycloak': 'oidc-auth/overlays/keycloak',
        'dex': 'oidc-auth/overlays/dex',
        'external': 'oidc-auth/base'
    }[args.oauth_type]

    files[f'{oidc_dest}/oauth2-proxy-secret.yaml'] = Secret(
        name='oauth2-proxy',
        namespace='auth',
        data={
            'client-id': vars['oidc'].OIDC_CLIENT_ID,
            'client-secret': vars['oidc'].OIDC_CLIENT_SECRET,
            'cookie-secret': vars['oidc'].COOKIE_SECRET
        }
    )

    if args.oauth_type == 'dex':
        ###########
        ### DEX
        ###########
        try:
            vars['dex'] = Dex()
        except:
            try:
                dex_values = DexValues()
            except:
                dex_values = DexValues.from_profile(profile=vars['profile'])

            vars['dex'] = Dex.from_values(
                profile=vars['profile'],
                oidc=vars['oidc'],
                dex=dex_values
            )

        files[f'{oidc_dest}/dex-config-secret.yaml'] = Secret(
            name='dex-config',
            namespace='auth',
            data=vars['dex'].DEX_CONFIG,
            filename='config.yaml'
        )

    elif args.oauth_type == 'keycloak':
        ###########
        ### Keycloak
        ###########

        try:
            # Try reading from env-var
            vars['kubeflow-realm'] = RealmTemplate()
        except:
            vars['kubeflow-realm'] = RealmTemplate.from_oidc(
                profile=vars['profile'],
                oidc=vars['oidc']
            )

        files[f'{oidc_dest}/kubeflow-realm-secret.yaml'] = Secret(
            name='kubeflow-realm',
            namespace='auth',
            data=vars['kubeflow-realm'].KUBEFLOW_REALM,
            filename='kubeflow-realm.json'
        )

        vars['keycloak'] = Keycloak()

        # Keycloak also requires some extra secrets
        files[f'{oidc_dest}/keycloak-secret.yaml'] = Secret(
            name='keycloak-secret',
            namespace='auth',
            data={
                'admin-password': vars['keycloak'].KEYCLOAK_ADMIN_PASS,
                'database-password': vars['keycloak'].DATABASE_PASS,
                'management-password': vars['keycloak'].KEYCLOAK_MANAGEMENT_PASS
            }
        )

        files[f'{oidc_dest}/postgresql-secret.yaml'] = Secret(
            name='keycloak-postgresql',
            namespace='auth',
            data={
                'postgresql-password': vars['keycloak'].DATABASE_PASS,
                'postgresql-postgres-password': vars['keycloak'].POSTGRESQL_PASS
            }
        )


    ##################
    ### Private Repo
    ##################
    if args.private_repo:
        try:
            vars['repo'] = PrivateGitRepo()
        except:
            vars['repo'] = PrivateGitRepo.user_entered()

        files['argocd/overlays/private-repo/secret.yaml'] = Secret(
            name='git-repo-secret',
            namespace='argocd',
            data={
                'HTTPS_USERNAME': vars['repo'].GIT_HTTPS_USERNAME,
                'HTTPS_PASSWORD': vars['repo'].GIT_HTTPS_PASSWORD
            }
        )


    ##################
    ### Grafana
    ##################
    if args.interactive:
        vars['grafana'] = Grafana.user_entered()
    else:
        vars['grafana'] = Grafana()

    files['monitoring-resources/grafana-admin-secret.yaml'] = Secret(
        name='grafana-admin-secret',
        namespace='monitoring',
        data={
            'admin-user': vars['grafana'].GRAFANA_USERNAME,
            'admin-password': vars['grafana'].GRAFANA_PASSWORD
        }
    )


    ##################
    ### Cloudflare
    ##################
    if args.cloudflare:
        try:
            vars['cloudflare'] = CloudFlare()
        except:
            # No env var found
            vars['cloudflare'] = CloudFlare.user_entered()


        files['cloudflare-secrets/cloudflare-api-token-secret-cert-manager.yaml'] = Secret(
            name='cloudflare-api-token-secret',
            namespace='cert-manager',
            data={
                'api-token': vars['cloudflare'].CLOUDFLARE_API_TOKEN
            }
        )

        files['cloudflare-secrets/cloudflare-api-token-secret-external-dns.yaml'] = Secret(
            name='cloudflare-api-token-secret',
            namespace='kube-system',
            data={
                'api-token': vars['cloudflare'].CLOUDFLARE_API_TOKEN
            }
        )


    ##########################
    ### All done! Let's save
    ##########################

    if args.secret_type == 'raw':
        print('\n### Argoflow Values')
        # Just print the variables and be done!
        for v in vars.values():
            # pydantic magic
            schema = {
                k: sorted(list(val['env_names']))[0]
                for (k,val) in type(v).schema()['properties'].items()
            }

            d = dict(v)
            for k in schema:
                env_var = schema[k]
                val = d[k].replace('\n','\\n')
                print(f'{env_var}="{val}"')

        # done!
        sys.exit(0)

    # Save everything!
    if args.secret_type == 'vault':

        for v in vars.values():
            for (k,val) in v.dict().items():
                if not val.startswith('<') or not val.endswith('>'):
                    print(f"# {k} looks like a real secret, not a reference", file=sys.stderr)
                    print(f'{k} -> {v}', file=sys.stderr)
                    raise ValueError(f'Vault secret {k} should look like <path>')

    for (file, secret) in files.items():
        if args.secret_type == 'generated':
            data = secret.yaml()
        elif args.secret_type == 'sealed':
            data = secret.kubeseal()
        elif args.secret_type == 'vault':
            # Don't accidentally commit secrets...
            data = secret.yaml(raw=True)
        else:
            raise Exception('This should be impossible.')

        write(data, dest=f'{args.secret_type}/{file}', overwrite=args.overwrite)
