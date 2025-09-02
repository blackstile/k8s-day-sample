GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Sem Cor

#!/bin/bash
create_cluster() {
    echo "### Etapa 1: Criando o cluster Kind ###"
    
    echo "--> Deletando cluster 'k8s-day' existente..."
    kind delete cluster --name k8s-day
    
    echo "--> Criando novo cluster 'k8s-day' com a configuração 'kind.yaml'..."
    kind create cluster --name k8s-day --config kind.yaml
    
    kubectl apply -f metrics-server.yaml
    echo -e "### ${GREEN}Cluster criado com sucesso! ###${NC}"
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
    echo -e "--> ${YELLOW}Aguardando o Ingress Controller ficar pronto...${NC}"
    kubectl wait --namespace ingress-nginx \
      --for=condition=ready pod \
      --selector=app.kubernetes.io/component=controller \
      --timeout=180s
}

deploy_observability(){

    echo "--> Excluindo deploy da stack de observabilidade (Prometheus, Grafana e Jaeger)..."
    kubectl delete -f observability/00-prometheus/  --ignore-not-found=true
    kubectl delete -f observability/01-grafana/  --ignore-not-found=true
    kubectl delete -f observability/02-jaeger/  --ignore-not-found=true
    
    echo "--> Fazendo deploy da stack de observabilidade (Prometheus, Grafana e Jaeger)..."
    kubectl apply -f observability/00-prometheus/
    kubectl apply -f observability/01-grafana/
    kubectl apply -f observability/02-jaeger/

    echo -e "### ${YELLOW} Aguardando os pods do namespace monitoring ficarem prontos.${NC}"
    kubectl wait --namespace monitoring-dev --timeout=180s \
        --for=condition=available \
        deployment/grafana-deployment \
        deployment/prometheus-deployment \
        deployment/jaeger

    echo -e "${GREEN}#######################################################################################################${NC}"
    kubectl get po -n monitoring-dev
    echo -e "${GREEN}#######################################################################################################${NC}"
    echo -e "### ${GREEN}Deploy do observability finalizado com sucesso! ###${NC}"
}

install_ingress_argocd(){
    kubectl apply -f cicd/
}

install_argocd_apps(){
    echo "### Instalando aplicações no ArgoCD \n"
    kubectl apply -f argo-cd-apps/
}


install_sealed(){

    if command -v kubeseal &> /dev/null; then
        echo -e "${GREEN}O 'kubeseal' já está instalado no sistema.${NC}"
        echo -e "Versão atual: ${YELLOW}$(kubeseal --version)${NC}"
        echo "Nenhuma ação é necessária."
        echo -e "${YELLOW}Instalando sealed-secrets controller no cluster${NC}"
        kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.31.0/controller.yaml
        kubectl wait --for=condition=available deploy/sealed-secrets-controller -n kube-system --timeout=180s
        echo -e "${YELLOW} Aguardando o Sealed Secrets Controller ficar pronto ${NC}"
        return 0
    fi


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
    echo -e "${YELLOW} Aguardando o Sealed Secrets Controller ficar pronto ${NC}"
    kubectl wait --for=condition=available deploy/sealed-secrets-controller -n kube-system --timeout=180s
}

install_jaeger(){
    echo "# Instalando Jaeger Operator"
    kubectl create -f https://github.com/jaegertracing/jaeger-operator/releases/download/v1.54.0/jaeger-operator.yaml
}

show_applications_url(){
    ADMIN_PASS=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
    echo "==================================================="
    echo "✅ Instalação concluída!"
    echo -e "${YELLOW}----------------"
    echo -e "${YELLOW}| URL Aplicação|"
    echo -e "${YELLOW}----------------${NC}"
    echo "🌐 Acesse: https://localhost/app"
    echo ""
    echo -e "${YELLOW}-----------------------"
    echo -e "${YELLOW}|Continous Deployment |"
    echo -e "${YELLOW}-----------------------${NC}"
    echo "🌐 Acesse: https://localhost/argocd"
    echo "👤 Usuário: admin"
    echo "🔑 Senha: ${ADMIN_PASS}"
    echo ""
    echo -e "${YELLOW}------------"
    echo -e "${YELLOW}|Monitoring|"
    echo -e "${YELLOW}------------${NC}"
    echo "🌐 Prometheus Acesse: https://localhost/prometheus/graph"
    echo "🌐 Grafana Acesse: https://localhost/grafana/"
    echo "👤Usuário: admin"
    echo "🔑Senha: admin"
    echo ""
    echo -e "${YELLOW}---------------------"
    echo -e "${YELLOW}|Distributed Tracing|"
    echo -e "${YELLOW}---------------------${NC}"
    echo "🌐 Acesse: https://localhost/jaeger/"
    echo ""
    echo "==================================================="
}

API_KEY=$1
echo $API_KEY

if [ -z "$API_KEY" ]; then
    echo -e "${YELLOW}Erro: A chave da API do GEMINI deve ser informada.${NC}"
    echo "======================== USAGE ===================="
    echo "./setup.sh <sua gemini api key>"
    echo ""
    echo "EXEMPLO:"
    echo -e "${GREEN}  ./setup.sh AIzaSyBeX54asChl0xxxxxxxxxxCdlJMMmxxxxx${NC}"
    echo ""
    echo "==================================================="
    exit 1
fi

./kind_install.sh
create_cluster;
install_metrics_server;
install_nginx_controller;
echo -e "Instalando o Argo CD"
./argocd_install.sh -i
deploy_observability;
install_ingress_argocd;
install_sealed;

kubectl create secret generic gemini-api-secret \
--from-literal=GEMINI_API_KEY="$API_KEY" \
--namespace=app-dev \
--dry-run=client -o yaml | kubeseal --format=yaml > app-llm/k8s/01-sealed-secret.yaml

echo "Arquivo '01-sealed-secret.yaml' gerado com sucesso!"

install_argocd_apps;

echo -e "${GREEN}TODA STACK FOI INSTALADA E CONFIGURADA COM SUCESSO${NC}"
show_applications_url


