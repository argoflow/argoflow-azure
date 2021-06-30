# Config
SETUP_CONF_PATH = setup.env

SECRETS := secrets-generated
# SECRETS := secrets-sealed
# SECRETS := secrets-external

# Helpers
REPLACE := .helpers/replace.py -c $(SETUP_CONF_PATH)
KUBE_TEMPLATE := kubectl create --dry-run=client -o yaml

# Directories
TEMPLATE := template
DISTRIBUTION := distribution

VARS := secrets/vars
GENERATED := secrets/generated
EXTERNAL := secrets/external
SEALED := secrets/sealed

# CHROMIUM := chromium
CHROMIUM := flatpak run org.chromium.Chromium --incognito

# Kind
KIND_NAME := argoflow

#===========================================

.DEFAULT: all
.PHONY: all clean kind $(SECRETS)


##########################################
###   ____                     _
###  / ___|  ___  ___ _ __ ___| |_ ___
###  \___ \ / _ \/ __| '__/ _ \ __/ __|
###   ___) |  __/ (__| | |  __/ |_\__ \
###  |____/ \___|\___|_|  \___|\__|___/
###
secrets-generated:
	# Add symlink of all generated secrets
	cd $$(dirname $(GENERATED)) && make all
	stow -S $$(basename $(GENERATED)) -d $$(dirname $(GENERATED)) -t $(DISTRIBUTION)

kubeseal:
	kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.16.0/controller.yaml

secrets-sealed:
	#kubeseal
	# Add symlink of all generated secrets
	cd $$(dirname $(SEALED)) && make all
	cd $$(dirname $(SEALED)) && make sealed
	stow -S $$(basename $(SEALED)) -d $$(dirname $(SEALED)) -t $(DISTRIBUTION)

secrets-external:
	# Add symlink of all generated secrets
	stow -S $$(basename $(EXTERNAL)) -d $$(dirname $(EXTERNAL)) -t $(DISTRIBUTION)


##############################################
###
###          d8888   888       888
###         d88888   888       888
###        d88P888   888       888
###       d88P 888   888       888
###      d88P  888   888       888
###     d88P   888   888       888
###    d8888888888   888       888
###   d88P     888   88888888  88888888
###
###

delete:
	cd secrets && make clean
	rm -rf $(DISTRIBUTION)
	kind delete clusters $(KIND_NAME)

build:
	rm -rf $(DISTRIBUTION)
	cp -r $(TEMPLATE) $(DISTRIBUTION)
	# Replace all $$ARGOFLOW_* variables in build
	mkdir -p $(VARS)
	for f in $(VARS); do \
		. $$f ; \
	done; \
	find $(DISTRIBUTION) -type f | xargs -I{} python3 $(REPLACE) -i -c $(SETUP_CONF_PATH) {}


##############################################
###   ___  ___     _        _ _    ______
###   |  \/  |    | |      | | |   | ___ \.
###   | .  . | ___| |_ __ _| | |   | |_/ /
###   | |\/| |/ _ \ __/ _` | | |   | ___ \.
###   | |  | |  __/ |_ (_| | | |____ |_/ /
###   \_|  |_/\___|\__\__,_|_\_____\____/
###
### Create the metallb secret files

define METRICS_SERVER_PATCH
{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "metrics-server",
            "args": [
              "--cert-dir=/tmp",
              "--secure-port=4443",
              "--kubelet-insecure-tls",
              "--kubelet-preferred-address-types=InternalIP"
            ]
          }
        ]
      }
    }
  }
}
endef
METRICS_SERVER_PATCH := $(shell echo '$(METRICS_SERVER_PATCH)' | jq -c)

kind:
	kind create cluster --name $(KIND_NAME) --config kind/kind-cluster.yaml
	kubectl cluster-info --context kind-$(KIND_NAME)
	kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.3.6/components.yaml
	kubectl patch deployment metrics-server -n kube-system -p '$(METRICS_SERVER_PATCH)'


### Local git server,
### For private ArgoCD in kind
gitserver: $(DISTRIBUTION) secrets
	docker build . -t gitserver:latest -f kind/gitserver.Dockerfile
	kind load docker-image gitserver:latest --name $(KIND_NAME)

	kubectl create namespace git || true
	kubectl apply -f kind/gitserver/Deployment.yaml
	kubectl apply -f kind/gitserver/Service.yaml
	kubectl rollout restart deployment -n git gitserver


deploy-argocd: $(DISTRIBUTION)
	kustomize build $(DISTRIBUTION)/argocd/base/ | kubectl apply -f -

	while ! kubectl get secrets \
		-n argocd | grep -q argocd-initial-admin-secret; do \
		echo "Waiting for ArgoCD to start..."; \
		sleep 5; \
	done

	$(MAKE) argo-get-pass

argo-get-pass:
	@echo "ArgoCD Login"
	@echo "=========================="
	@echo "ArgoCD Username is: admin"
	@printf "ArgoCD Password is: %s\n" $$(kubectl -n argocd \
		get secret argocd-initial-admin-secret \
		-o jsonpath="{.data.password}" | base64 -d)
	@echo "=========================="


deploy-kubeflow: $(DISTRIBUTION)
	kubectl apply -f $(DISTRIBUTION)/kubeflow.yaml


METALLB_CONFIGMAP := kind/metallb/configmap.yaml
deploy-metallb:
	# Give ArgoCD a loadbalancer endpoint.
	kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}' || true

	$(KUBE_TEMPLATE) secret generic -n metallb-system memberlist \
		--from-literal=secretkey="$$(openssl rand -base64 128)" > kind/metallb/secret.yaml

	# Fix the IP Range of MetalLB
	CIDR=$$(docker network inspect -f '{{.IPAM.Config}}' kind | sed 's~\[{\([0-9/.]*\) .*~\1~'); \
	SUBCLASS=$$(echo $$CIDR | awk -F '.' '{printf("%d.%d",$$1,$$2)}'); \
	METALLB_RANGE=$$(grep '\([0-9][0-9\.]*\)-\([0-9][0-9\.]*\)' $(METALLB_CONFIGMAP)); \
	METALLB_CLASS=$$(echo $$METALLB_RANGE | sed 's/^ *- *//' | awk -F '.' '{printf("%d.%d", $$1, $$2) }'); \
	kustomize build kind/metallb | sed "s/$$METALLB_CLASS/$$SUBCLASS/g" | kubectl apply -f -

deploy: kind build $(SECRETS) gitserver deploy-argocd deploy-kubeflow deploy-metallb

chromium:
	$(CHROMIUM) --host-rules="MAP *.aaw.cloud.statcan.ca $$(kubectl get svc -n istio-system istio-ingressgateway -o json | jq -r '.status | .. | .ip? // empty')" &
	#kubectl port-forward -n istio-system svc/istio-ingressgateway 8443:80
