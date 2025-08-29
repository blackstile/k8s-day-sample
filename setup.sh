#!/bin/bash
create_cluster() {
    echo "### Etapa 1: Criando o cluster Kind ###"
    
    echo "--> Deletando cluster 'k8s-day' existente..."
    kind delete cluster --name k8s-day
    
    echo "--> Criando novo cluster 'k8s-day' com a configuração 'kind.yaml'..."
    kind create cluster --name k8s-day --config kind.yaml
    
    kubectl apply -f metrics-server.yaml
    echo "### Cluster criado com sucesso! ###"
}

install_metrics_server(){
    echo "### Etapa 2: Instalando o Metric Server"
    kubectl apply -f metrics-server.yaml
}

install_nginx_controller(){
    echo "### Etapa 3:  Aplicando o Ingress NGINX Controller..."
    # kubectl apply -f nginx-ingress-controller.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

    # Adicionando uma espera para o Ingress Controller ficar pronto
    echo "--> Aguardando o Ingress Controller ficar pronto..."
    kubectl wait --namespace ingress-nginx \
      --for=condition=ready pod \
      --selector=app.kubernetes.io/component=controller \
      --timeout=180s
}

deploy_observability(){

    echo "--> Excluindo deploy da stack de observabilidade (Prometheus e Grafana)..."
    kubectl delete -f observability/00-prometheus/  --ignore-not-found=true
    kubectl delete -f observability/01-grafana/  --ignore-not-found=true
    
    echo "--> Fazendo deploy da stack de observabilidade (Prometheus e Grafana)..."
    kubectl apply -f observability/00-prometheus/
    kubectl apply -f observability/01-grafana/

    kubectl wait --namespace monitoring-dev \
      --for=condition=ready pod \
      --selector=app.kubernetes.io/component=controller \
      --timeout=60s
    
    kubectl get po -n monitoring-dev
    echo "### Deploy do observability finalizado com sucesso! ###"
}

install_ingress_argocd(){
    kubectl apply -f cicd/
}

install_argocd_apps(){
    echo "### Instalando aplicações no ArgoCD \n"
    kubectl apply -f argo-cd-apps/
}


install_sealed(){
    local os
    os="$(uname -s)"

    case "${os}" in
        Linux*)
            curl -OL "https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.31.0/kubeseal-0.31.0-linux-amd64.tar.gz"
            tar -xvzf kubeseal-0.31.0-linux-amd64.tar.gz kubeseal
            sudo install -m 755 kubeseal /usr/local/bin/kubeseal
            ;;
        Darwin*)
            brew install kubeseal
            ;;
        *)
            echo "Erro: Sistema operacional ${os} não suportado."
            exit 1
            ;;
    esac
    kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.31.0/controller.yaml
}

install_jaeger(){
    echo "# Instalando Jaeger Operator"
    kubectl create -f https://github.com/jaegertracing/jaeger-operator/releases/download/v1.54.0/jaeger-operator.yaml

}


./kind_install.sh
create_cluster;
install_metrics_server;
install_nginx_controller;
echo -e "Instalando o Argo CD"
./argocd_install.sh -i
deploy_observability;
install_ingress_argocd;
install_argocd_apps;
install_sealed;


