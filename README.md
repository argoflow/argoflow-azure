# Deploying Kubeflow with ArgoCD

This repository contains Kustomize manifests that point to the upstream
manifest of each Kubeflow component and provides an easy way for people
to change their deployment according to their need. ArgoCD application
manifests for each component will be used to deploy Kubeflow.

The intended usage is for people to fork this repository, make their desired
kustomizations, run a script to change the ArgoCD application specs to point
to their fork of this repository, and finally apply a master ArgoCD application
that will deploy all other applications.

## Prerequisites

- docker (if using kind)
- docker-tuntap-osx (if using macosx)
- findutils (if using macosx)
- kubectl `1.21.1`
- kustomize `4.0.5`
- yq `4.9.3`

## Workflow

The rough workflow is as follows:

- Fork this repository
- Modify the kustomizations
- Run `./setup_repo.sh examples/setup.conf`
- Commit and push your changes
- Install ArgoCD
- Install Kubeflow

## Folder setup

- [argocd](./distribution/argocd): Kustomize files for ArgoCD
- [argocd-applications](./distribution/argocd-applications): ArgoCD application for each Kubeflow component
- [cert-manager](./distribution/cert-manager): Kustomize files for installing cert-manager v1.2
- [kubeflow](./distribution/kubeflow): Kustomize files for installing Kubeflow components
  - [central-dashboard](./distribution/kubeflow/notebooks/central-dashboard): Kustomize files for installing the Central Dashboard
  - [jupyter-web-app](./distribution/kubeflow/notebooks/jupyter-web-app): Kustomize files for installing the Jupyter Web App
    - [notebook-controller](./distribution/kubeflow/notebooks/notebook-controller): Kustomize files for installing the Notebook Controller
  - [katib](./distribution/kubeflow/katib): Kustomize files for installing Katib
  - [kfserving](./distribution/kubeflow/kfserving): Kustomize files for installing KFServing
  - [namespaces](./distribution/kubeflow/namespace): Kustomize manifest to create the profile and namespace for the default Kubeflow user
  - [operators](./distribution/kubeflow/operators): Kustomize files for installing the various operators
  - [pipelines](./distribution/kubeflow/pipelines): Kustomize files for installing Kubeflow Pipelines
  - [pod-defaults](./distribution/kubeflow/notebooks/pod-defaults): Kustomize files for installing Pod Defaults (a.k.a. admission webhook)
  - [profile-controller_access-management](./distribution/kubeflow/notebooks/profile-controller_access-management): Kustomize files for installing the Profile Controller and Access Management
  - [roles](./distribution/kubeflow/roles): Kustomize files for Kubeflow namespace and ClusterRoles
  - [tensorboards-web-app](./distribution/kubeflow/notebooks/tensorboards-web-app): Kustomize files for installing the Tensorboards Web App
    - [tensorboard-controller](./distribution/kubeflow/notebooks/tensorboard-controller): Kustomize files for installing the Tensorboard Controller
  - [volumes-web-app](./distribution/kubeflow/notebooks/volumes-web-app): Kustomize files for installing the Volumes Web App
- [knative](./distribution/knative): Kustomize files for installing KNative
- [metallb](./distribution/metallb): Kustomize files for installing MetalLB
- [oidc-auth](./distribution/oidc-auth): Kustomize files for OIDC authservice

### Root files

- [kustomization.yaml](./distribution/kustomization.yaml): Kustomization file that references the ArgoCD application files in [argocd-applications](./distribution/argocd-applications)
- [kubeflow.yaml](./distribution/kubeflow.yaml): ArgoCD application that deploys the ArgoCD applications referenced in [kustomization.yaml](./distribution/kustomization.yaml)

## Kind

### Installation

On linux:

```bash
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.10.0/kind-linux-amd64
chmod +x ./kind
mv ./kind /<some-dir-in-your-PATH>/kind
```

On Mac:

```bash
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.10.0/kind-darwin-amd64
chmod +x ./kind
mv ./kind /<some-dir-in-your-PATH>/kind
```

On Windows:

```cmd
curl.exe -Lo kind-windows-amd64.exe https://kind.sigs.k8s.io/dl/v0.10.0/kind-windows-amd64
Move-Item .\kind-windows-amd64.exe c:\some-dir-in-your-PATH\kind.exe
```

### Deploying kind cluster

`kind create cluster --config kind/kind-cluster.yaml`

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.3.6/components.yaml
kubectl patch deployment metrics-server -n kube-system -p '{"spec":{"template":{"spec":{"containers":[{"name":"metrics-server","args":["--cert-dir=/tmp", "--secure-port=4443", "--kubelet-insecure-tls","--kubelet-preferred-address-types=InternalIP"]}]}}}}'
```

### Deploy Sealed Secrets

Install the sealed secrets controller:

```sh
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.16.0/controller.yaml
```

### Deploy MetalLB

Edit the IP range in [configmap.yaml](./metallb/configmap.yaml) so that it is within
the range of your docker network.

To get your docker network range, run the following command:

```sh
docker network inspect -f '{{.IPAM.Config}}' kind
```

After updating the metallb configmap, deploy it by running:

```sh
kustomize build distribution/metallb/ | kubectl apply -f -
```

### Deploy Argo CD

Deploy Argo CD with the following command and expose with a Load Balancer:

```sh
kustomize build distribution/argocd/base/ | kubectl apply -f -
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'
```

Get the Load Balancer IP of the Argo CD endpoint:

```sh
kubectl get svc argocd-server -n argocd
```

Login with the username `admin` and the password:

```sh
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
argocd login <lb-ip>
argocd account update-password
```

### Deploy Kubeflow

To deploy Kubeflow, execute the following command:

```sh
kubectl apply -f distribution/kubeflow.yaml
```

> Note: This deploys all components of Kubeflow 1.3 and this might take a while.

Get the IP of the Kubeflow gateway with the following command:

```sh
kubectl get svc istio-ingressgateway -n istio-system
```

### Hosts

Add the following entries to you `/etc/hosts` file:

```sh
<lb-ip> kubeflow.aaw.cloud.statcan.ca
<lb-ip> serving.aaw.cloud.statcan.ca
<lb-ip> auth.aaw.cloud.statcan.ca
```

### Remove kind cluster

Delete the Kind Cluster:

```sh
kind delete cluster
```

## References

The following are some useful references which might provide some additional assistance.

* [Kind and MetalLB on MacOSX](https://www.thehumblelab.com/kind-and-metallb-on-mac/)
