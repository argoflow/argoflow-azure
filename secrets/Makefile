# Config
SETUP_CONF_PATH = ../setup.env
REPLACE := ../.helpers/replace.py -c $(SETUP_CONF_PATH)


# Helpers
KUBE_TEMPLATE := kubectl create --dry-run=client -o yaml
RAND_BASE64 := python3 -c 'import sys,os,base64; print(base64.urlsafe_b64encode(os.urandom(int(sys.argv[1]))).decode())'
RAND_HEX    := python3 -c 'import sys,secrets; print(secrets.token_hex(int(sys.argv[1])))'

GRN := printf '\033[0;32m'
NC  := printf '\033[0m'

# Directories
TEMPLATE := ../template

VARS := vars
GENERATED := generated
SEALED := sealed

# NO ASK (set these to "noask")
CLOUDFLARE_NO_ASK := noask
EXTERNAL_OIDC_NO_ASK := noask

#===========================================

.DEFAULT: all
.PHONY: all clean $(SECRETS)

SECRETS := user kubeflow keycloak oauth external-oidc grafana cloudflare
all: $(SECRETS)

clean:
	rm -rf $(GENERATED) $(VARS) $(SEALED)

# Create secrets from env vars, first
$(VARS):
	mkdir -p $(VARS)
	printenv | grep '^ARGOFLOW_' | while read line; do \
		VAR=$$(echo $$line | awk -F '=' '{print $$1}'); \
		echo '#!/bin/bash\n' > $(VARS)/$$VAR; \
		echo '# This was sourced from an env var\n' > $(VARS)/$$VAR; \
		printf 'export %s\n' $$line >> $(VARS)/$$VAR; \
	done

	@echo "Secrets found in ENV:"
	@echo ========================
	@ls $(VARS)
	@echo ========================
	@echo

##############################
###   _   _
###  | | | |
###  | | | |___  ___ _ __
###  | | | / __|/ _ \ '__|
###  | |_| \__ \  __/ |
###   \___/|___/\___|_|
###
### Create the $(KUBEFLOW_CONFIG) files

KUBEFLOW_CONFIG := $(VARS)/ARGOFLOW_EMAIL
KUBEFLOW_CONFIG += $(VARS)/ARGOFLOW_USERNAME
KUBEFLOW_CONFIG += $(VARS)/ARGOFLOW_FIRSTNAME
KUBEFLOW_CONFIG += $(VARS)/ARGOFLOW_LASTNAME
KUBEFLOW_CONFIG += $(VARS)/ARGOFLOW_ADMIN_PASS

$(KUBEFLOW_CONFIG): $(VARS)
	@if [ ! -f $@ ]; then \
		$(GRN); \
		read -p "(kubeflow setting) $$(basename $@): " VAR; \
		$(NC); \
		printf "export $$(basename $@)='%s'" $$VAR > $@ ; \
	fi

user: $(KUBEFLOW_CONFIG)


##########################################
###    _____  ___        _   _
###   |  _  |/ _ \      | | | |
###   | | | / /_\ \_   _| |_| |__
###   | | | |  _  | | | | __| '_ \.
###   \ \_/ / | | | |_| | |_| | | |
###    \___/\_| |_/\__,_|\__|_| |_|
###
###  Create the $(OAUTH_SECRETS)

$(VARS)/ARGOFLOW_COOKIE_SECRET: $(VARS)
	[ -f $@ ] || printf "export $$(basename $@)='%s'" "$$($(RAND_BASE64) 16)" > $@

$(VARS)/ARGOFLOW_OIDC_CLIENT_ID: $(VARS)
	[ -f $@ ] || printf "export $$(basename $@)='%s'" "$$($(RAND_HEX) 16)" > $@

$(VARS)/ARGOFLOW_OIDC_CLIENT_SECRET: $(VARS)
	[ -f $@ ] || printf "export $$(basename $@)='%s'" "$$($(RAND_HEX) 32)" > $@

# Generate the YAML
OAUTH_SECRETS := $(GENERATED)/oidc-auth/overlays/dex/oauth2-proxy-secret.yaml
OAUTH_SECRETS += $(GENERATED)/oidc-auth/overlays/keycloak/oauth2-proxy-secret.yaml

OAUTH_DEPS := $(VARS)/ARGOFLOW_OIDC_CLIENT_ID
OAUTH_DEPS += $(VARS)/ARGOFLOW_OIDC_CLIENT_SECRET
OAUTH_DEPS += $(VARS)/ARGOFLOW_COOKIE_SECRET

$(OAUTH_SECRETS): $(OAUTH_DEPS)
	mkdir -p $$(dirname $@)
	# Source all prerequisite secrets
	for f in $^; do \
		. $$f ; \
	done; \
	$(KUBE_TEMPLATE) secret generic -n auth oauth2-proxy \
		--from-literal=client-id=$$ARGOFLOW_OIDC_CLIENT_ID \
		--from-literal=client-secret=$$ARGOFLOW_OIDC_CLIENT_SECRET \
		--from-literal=cookie-secret=$$ARGOFLOW_COOKIE_SECRET > $@

oauth: $(OAUTH_SECRETS)


#######################################################
###    _   __           _____ _             _
###   | | / /          /  __ \ |           | |
###   | |/ /  ___ _   _| /  \/ | ___   __ _| | __
###   |    \ / _ \ | | | |   | |/ _ \ / _` | |/ /
###   | |\  \  __/ |_| | \__/\ | (_) | (_| |   <
###   \_| \_/\___|\__, |\____/_|\___/ \__,_|_|\_\.
###                __/ |
###               |___/
###
###

# These are all just $$($(RAND_HEX) 16)
VARS_KEYCLOAK_DEPS := $(VARS)/ARGOFLOW_DATABASE_PASS
VARS_KEYCLOAK_DEPS += $(VARS)/ARGOFLOW_POSTGRESQL_PASS
VARS_KEYCLOAK_DEPS += $(VARS)/ARGOFLOW_KEYCLOAK_ADMIN_PASS
VARS_KEYCLOAK_DEPS += $(VARS)/ARGOFLOW_KEYCLOAK_MANAGEMENT_PASS

$(VARS_KEYCLOAK_DEPS): $(VARS)
	[ -f $@ ] || printf "export $$(basename $@)='%s'" "$$($(RAND_HEX) 16)" > $@

KEYCLOAK_DEPS := $(VARS)/ARGOFLOW_DATABASE_PASS
KEYCLOAK_DEPS += $(VARS)/ARGOFLOW_POSTGRESQL_PASS
KEYCLOAK_DEPS += $(VARS)/ARGOFLOW_KEYCLOAK_ADMIN_PASS
KEYCLOAK_DEPS += $(VARS)/ARGOFLOW_KEYCLOAK_MANAGEMENT_PASS

KEYCLOAK_SECRET := $(GENERATED)/oidc-auth/overlays/keycloak/keycloak-secret.yaml
$(KEYCLOAK_SECRET): $(KEYCLOAK_DEPS)
	mkdir -p $$(dirname $@)
	for f in $^; do \
		. $$f ; \
	done; \
	$(KUBE_TEMPLATE) secret generic -n auth keycloak-secret \
		--from-literal=admin-password=$$ARGOFLOW_KEYCLOAK_ADMIN_PASS \
		--from-literal=database-password=$$ARGOFLOW_DATABASE_PASS \
		--from-literal=management-password=$$ARGOFLOW_KEYCLOAK_MANAGEMENT_PASS > $@


KEYCLOAK_POSTGRES := $(GENERATED)/oidc-auth/overlays/keycloak/postgresql-secret.yaml
$(KEYCLOAK_POSTGRES): $(KEYCLOAK_DEPS)
	mkdir -p $$(dirname $@)
	for f in $^; do \
		. $$f ; \
	done; \
	$(KUBE_TEMPLATE) secret generic -n auth keycloak-postgresql \
		--from-literal=postgresql-password=$$ARGOFLOW_DATABASE_PASS \
		--from-literal=postgresql-postgres-password=$$ARGOFLOW_POSTGRESQL_PASS > $@

keycloak: $(KEYCLOAK_SECRET) $(KEYCLOAK_POSTGRES)

#####################################################
###    _   __      _           __ _
###   | | / /     | |         / _| |
###   | |/ / _   _| |__   ___| |_| | _____      __
###   |    \| | | | '_ \ / _ \  _| |/ _ \ \ /\ / /
###   | |\  \ |_| | |_) |  __/ | | | (_) \ V  V /
###   \_| \_/\__,_|_.__/ \___|_| |_|\___/ \_/\_/
###

$(VARS)/ARGOFLOW_ADMIN_PASS_DEX: $(VARS) $(VARS)/ARGOFLOW_ADMIN_PASS
	[ -f $@ ] || pip3 freeze | grep -q passlib || pip3 install passlib
	[ -f $@ ] || . $(VARS)/ARGOFLOW_ADMIN_PASS; \
	ADMIN_PASS_DEX=$$(python3 -c "from passlib.hash import bcrypt; print(bcrypt.using(rounds=12, ident='2y').hash(\"$$ARGOFLOW_ADMIN_PASS\"))"); \
	printf "export $$(basename $@)='%s'" "$$ADMIN_PASS_DEX" > $@

DEX_SECRET := $(GENERATED)/oidc-auth/overlays/dex/dex-config-secret.yaml
DEX_DEPS := $(VARS)/ARGOFLOW_ADMIN_PASS_DEX $(OAUTH_DEPS) $(KUBEFLOW_CONFIG)

$(DEX_SECRET): $(DEX_DEPS)
	mkdir -p $$(dirname $@)
	for f in $^; do \
		. $$f ; \
	done; \
	python3 $(REPLACE) $(TEMPLATE)/oidc-auth/overlays/dex/dex-config-template.yaml | \
		$(KUBE_TEMPLATE) secret generic -n auth dex-config --from-file=config.yaml=/dev/stdin > $@


OIDC_KUBEFLOW := $(GENERATED)/oidc-auth/overlays/keycloak/kubeflow-realm-secret.yaml

$(OIDC_KUBEFLOW): $(DEX_DEPS)
	mkdir -p $$(dirname $@)
	for f in $^; do \
		. $$f ; \
	done; \
	python3 $(REPLACE) $(TEMPLATE)/oidc-auth/overlays/keycloak/kubeflow-realm-template.json | \
		$(KUBE_TEMPLATE) secret generic -n auth kubeflow-realm --from-file=kubeflow-realm.json=/dev/stdin > $@


kubeflow: $(OIDC_KUBEFLOW) $(DEX_SECRET)

##############################################
###    _____            __
###   |  __ \          / _|
###   | |  \/_ __ __ _| |_ __ _ _ __   __ _
###   | | __| '__/ _` |  _/ _` | '_ \ / _` |
###   | |_\ \ | | (_| | || (_| | | | | (_| |
###    \____/_|  \__,_|_| \__,_|_| |_|\__,_|
###
###

GRAFANA_CONFIG := $(VARS)/ARGOFLOW_GRAFANA_ADMIN_USERNAME
GRAFANA_CONFIG += $(VARS)/ARGOFLOW_GRAFANA_ADMIN_PASS

$(GRAFANA_CONFIG): $(VARS)
	@if [ ! -f $@ ]; then \
		$(GRN); \
		read -p "(grafana) $$(basename $@): " VAR; \
		$(NC); \
		printf "export $$(basename $@)='%s'" $$VAR > $@ ; \
	fi

GRAFANA_SECRET := $(GENERATED)/monitoring-resources/grafana-admin-secret.yaml

$(GRAFANA_SECRET): $(GRAFANA_CONFIG)
	mkdir -p $$(dirname $@)
	for f in $^; do \
		. $$f ; \
	done; \
	$(KUBE_TEMPLATE) secret generic -n monitoring grafana-admin-secret \
		--from-literal=admin-user=$$ARGOFLOW_GRAFANA_ADMIN_USERNAME \
		--from-literal=admin-password=$$ARGOFLOW_GRAFANA_ADMIN_PASS > $@

grafana: $(GRAFANA_SECRET)


###########################################################################
###    _____     _                        _     _____ ___________ _____
###   |  ___|   | |                      | |   |  _  |_   _|  _  \  __ \.
###   | |____  __ |_ ___ _ __ _ __   __ _| |   | | | | | | | | | | /  \/
###   |  __\ \/ / __/ _ \ '__| '_ \ / _` | |   | | | | | | | | | | |
###   | |___>  <| |_  __/ |  | | | | (_| | |   \ \_/ /_| |_| |/ /| \__/\.
###   \____/_/\_\\__\___|_|  |_| |_|\__,_|_|    \___/ \___/|___/  \____/
###
###

ifeq ($(EXTERNAL_OIDC_NO_ASK),noask)
external-oidc:
	@echo "Skipping External OIDC setup..."
else

EXTERNAL_OIDC_SECRET := $(GENERATED)/oidc-auth/base/oauth2-proxy-secret.yaml

$(VARS)/ARGOFLOW_OIDC_CLIENT_ID_INPUT $(VARS)/ARGOFLOW_OIDC_CLIENT_SECRET_INPUT: $(VARS)
	@if [ ! -f $(EXTERNAL_OIDC_SECRET) ] && [ ! -f $@ ]; then \
		$(GRN); \
		read -p "(external oidc) $$(basename $@): " VAR; \
		$(NC); \
		printf "export $$(basename $@)='%s'" $$VAR > $@ ; \
	fi


EXTERNAL_OIDC_DEPS := $(VARS)/ARGOFLOW_OIDC_CLIENT_ID_INPUT
EXTERNAL_OIDC_DEPS += $(VARS)/ARGOFLOW_OIDC_CLIENT_ID_INPUT
# This was defined in the OAuth section
EXTERNAL_OIDC_DEPS += $(VARS)/ARGOFLOW_COOKIE_SECRET

$(EXTERNAL_OIDC_SECRET): $(EXTERNAL_OIDC_DEPS)
	# This is a cheat. If answer "No", create a blank secret yaml
	while true; do \
		$(GRN); \
	    read -p "Setup External OIDC client instead of on-cluster provider [y/n]? " yn; \
		$(NC); \
	    case $$yn in \
	        [Yy]*) exit 0 ;; \
	        [Nn]*) mkdir -p $$(dirname $(EXTERNAL_OIDC_SECRET)); \
					touch $(EXTERNAL_OIDC_SECRET) ; \
					exit 0 ;; \
	        * ) echo "Please answer yes or no.";; \
	    esac; \
	done

	# The (blank) secret may have been created in the above command.
	[ -f $(EXTERNAL_OIDC_SECRET) ] || \
	for f in $^; do \
		. $$f ; \
	done; \
	$(KUBE_TEMPLATE) secret generic -n auth oauth2-proxy \
		--from-literal=client-id=$$ARGOFLOW_OIDC_CLIENT_ID_INPUT \
		--from-literal=client-secret=$$ARGOFLOW_OIDC_CLIENT_SECRET_INPUT \
		--from-literal=cookie-secret=$$ARGOFLOW_COOKIE_SECRET > $@

external-oidc: $(EXTERNAL_OIDC_SECRET)
endif


########################################################
###    _____ _                 _  __ _
###   /  __ \ |               | |/ _| |
###   | /  \/ | ___  _   _  __| | |_| | __ _ _ __ ___
###   | |   | |/ _ \| | | |/ _` |  _| |/ _` | '__/ _ \.
###   | \__/\ | (_) | |_| | (_| | | | | (_| | | |  __/
###    \____/_|\___/ \__,_|\__,_|_| |_|\__,_|_|  \___|
###
###

ifeq ($(CLOUDFLARE_NO_ASK),noask)
cloudflare:
	@echo "Skipping Cloudflare setup..."
else

CLOUDFLARE_CERT_MANAGER := $(GENERATED)/cloudflare-secrets/cloudflare-api-token-secret-cert-manager.yaml
CLOUDFLARE_DNS := $(GENERATED)/cloudflare-secrets/cloudflare-api-token-secret-external-dns.yaml

$(VARS)/ARGOFLOW_CLOUDFLARE_API_TOKEN:
	# This is a cheat. If answer "No", create a blank secret yaml
	while true; do \
		$(GRN); \
	    read -p "Setup Cloudflare with cert-manager and external DNS [y/n]? " yn; \
		$(NC); \
	    case $$yn in \
	        [Yy]*) \
					$(GRN); \
					read -p "(cloudflare) $$(basename $@): " VAR; \
					$(NC); \
					printf "export $$(basename $@)='%s'" $$VAR > $@ ; \
					break \
					;; \
	        [Nn]*) \
					mkdir -p $$(dirname $(CLOUDFLARE_CERT_MANAGER)); \
					mkdir -p $$(dirname $(CLOUDFLARE_DNS)); \
					touch $(CLOUDFLARE_CERT_MANAGER) ; \
					touch $(CLOUDFLARE_DNS) ; \
					exit 0 ;; \
	        * ) echo "Please answer yes or no.";; \
	    esac; \
	done


$(CLOUDFLARE_CERT_MANAGER): $(VARS)/ARGOFLOW_CLOUDFLARE_API_TOKEN
	[ -f $@ ] || \
	for f in $^; do \
		. $$f ; \
	done; \
	$(KUBE_TEMPLATE) secret generic -n cert-manager cloudflare-api-token-secret \
	  	--from-literal=api-token=$$ARGOFLOW_CLOUDFLARE_API_TOKEN > $@

$(CLOUDFLARE_DNS): $(VARS)/ARGOFLOW_CLOUDFLARE_API_TOKEN
	[ -f $@ ] || \
	for f in $^; do \
		. $$f ; \
	done; \
	$(KUBE_TEMPLATE) secret generic -n kube-system cloudflare-api-token-secret \
	  	--from-literal=api-token=$$ARGOFLOW_CLOUDFLARE_API_TOKEN > $@

CLOUDFLARE_SECRETS := $(CLOUDFLARE_CERT_MANAGER) $(CLOUDFLARE_DNS)
cloudflare: $(CLOUDFLARE_SECRETS)

endif



#################################
###     ____             _
###    / ___|  ___  __ _| |
###    \___ \ / _ \/ _` | |
###     ___) |  __/ (_| | |
###    |____/ \___|\__,_|_|
###
###  This needs to be already prepped on your cluster
sealed:
	mkdir -p $@
	{ cd $(GENERATED); find * -name '*.yaml'; } | while read line; do \
		mkdir -p $@/$$(dirname $$line); \
		kubeseal -f $(GENERATED)/$$line | $(KUBE_TEMPLATE) -f - > $@/$$line; \
	done
