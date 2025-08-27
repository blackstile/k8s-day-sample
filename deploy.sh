#!/bin/bash

# Define um 'modo estrito' para o script. Se um comando falhar, o script para.
# 'nounset' trata variáveis não definidas como erro.
set -eo pipefail
set -o nounset

# --- Funções para cada etapa ---

# Função para construir a imagem Docker, fazer o push e executá-la
build_image() {
    echo "### Etapa 1: Construindo a imagem Docker ###"
    cd app-llm || { echo "Diretório 'app-llm' não encontrado!"; exit 1; }
    
    echo "--> Construindo a imagem blackstile/app-llm:1.0.0"
    docker build --no-cache  . -t blackstile/app-llm:1.0.0

    echo "--> Enviando imagem para o registro"
    docker push blackstile/app-llm:1.0.0
    
    # echo "--> Executando o container localmente"
    # Remove um container com o mesmo nome, se existir, para evitar conflitos
    # docker rm -f app-llm || true
    # docker run -d --name app-llm -p 8000:5000 blackstile/app-llm:1.0.0
    
    cd ..
    echo "### Imagem construída com sucesso! ###"
}

# Função para criar o cluster Kind
create_cluster() {
    echo "### Etapa 2: Criando o cluster Kind ###"
    
    echo "--> Deletando cluster 'k8s-day' existente..."
    kind delete cluster --name k8s-day
    
    echo "--> Criando novo cluster 'k8s-day' com a configuração 'kind.yaml'..."
    kind create cluster --name k8s-day --config kind.yaml
    
    kubectl apply -f components.yaml
    echo "### Cluster criado com sucesso! ###"
}

# Função para fazer o deploy dos recursos no Kubernetes
deploy_application() {
    echo "### Etapa 3: Fazendo deploy da aplicação no Kubernetes ###"
    
    echo "--> Aplicando o Ingress NGINX Controller..."
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

    # Adicionando uma espera para o Ingress Controller ficar pronto
    echo "--> Aguardando o Ingress Controller ficar pronto..."
    kubectl wait --namespace ingress-nginx \
      --for=condition=ready pod \
      --selector=app.kubernetes.io/component=controller \
      --timeout=180s


    echo "--> Fazendo deploy da aplicação (app-llm)..."
    kubectl apply -f app-llm/k8s
    
    echo "--> Fazendo deploy da stack de observabilidade (Prometheus e Grafana)..."
    kubectl apply -f observability/00-prometheus/
    kubectl apply -f observability/01-grafana/
    
    echo "--> Configurando o contexto para o namespace 'app-dev'..."
    kubectl config set-context --current --namespace=app-dev

      
    echo "### Deploy finalizado com sucesso! ###"
}

redeploy_app(){

    echo "--> Configurando o contexto para o namespace 'app-dev'..."
    kubectl config set-context --current --namespace=app-dev

    echo "### Excluindo a versão antiga da aplicação"
    kubectl delete -f app-llm/k8s  --ignore-not-found=true
    echo "### Realizando o deploy da aplicação"
    kubectl apply -f app-llm/k8s

    echo "### Deploy da Aplicação LLM finalizada com sucesso! ###"
}

redeploy_observability(){

    kubectl config set-context --current --namespace=monitoring-dev
    echo "--> Excluindo deploy da stack de observabilidade (Prometheus e Grafana)..."
    kubectl delete -f observability/00-prometheus/  --ignore-not-found=true
    kubectl delete -f observability/01-grafana/  --ignore-not-found=true
    
    echo "--> Fazendo deploy da stack de observabilidade (Prometheus e Grafana)..."
    kubectl apply -f observability/00-prometheus/
    kubectl apply -f observability/01-grafana/

    kubectl wait --namespace monitoring-dev \
      --for=condition=ready pod \
      --selector=app.kubernetes.io/component=controller \
      --timeout=30s
    
    echo "### Deploy do observability finalizado com sucesso! ###"
    kubectl config set-context --current --namespace=app-dev
}

# Função para exibir a ajuda
usage() {
    echo "Uso: $0 [flags]"
    echo
    echo "Flags disponíveis:"
    echo "  -a    Executa todas as etapas (build, cluster, deploy)."
    echo "  -b    Executa a etapa de build da imagem Docker."
    echo "  -c    Executa a etapa de criação do cluster Kind."
    echo "  -d    Executa a etapa de deploy da aplicação."
    echo "  -r    Executa o re-deploy da aplicação LLM no kubernetes"
    echo "  -o    Executa o re-deploy do grafana e prometheus no kubernetes"
    echo "  -i    Import Dashboard para o grafana"
    echo "  -h    Mostra este menu de ajuda."
    exit 1
}

# --- Lógica de controle ---

# Se nenhum argumento for passado, exibe a ajuda
if [ $# -eq 0 ]; then
    set -- -a
fi

# Processa as flags passadas na linha de comando
while getopts "abcdro" opt; do
  case ${opt} in
    a )
      build_image
      create_cluster
      deploy_application
      ;;
    b )
      build_image
      ;;
    c )
      create_cluster
      ;;
    d )
      deploy_application
      ;;
    r )
      redeploy_app
      ;;
    o )
      redeploy_observability
      ;;
    h|? )
      usage
      ;;
  esac
done
