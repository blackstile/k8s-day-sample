#!/bin/bash

# --- Configurações e Variáveis Globais ---
# Saída colorida para melhor legibilidade
# --- Configurações e Variáveis Globais ---
# Saída colorida para melhor legibilidade
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Sem Cor

KIND_BASE_URL="https://kind.sigs.k8s.io/dl/v0.23.0"
KIND_FILE="kind"


install_on_linux() {
    local arch
    arch="$(uname -m)"
    echo "Sistema operacional detectado: Linux"

    case "${arch}" in
        x86_64)
            echo "Arquitetura: AMD64 / x86_64"
            curl -Lo "./${KIND_FILE}" "${KIND_BASE_URL}/kind-linux-amd64"
            ;;
        aarch64)
            echo "Arquitetura: ARM64"
            curl -Lo "./${KIND_FILE}" "${KIND_BASE_URL}/kind-linux-arm64"
            ;;
        *)
            echo "Erro: Arquitetura ${arch} não suportada para Linux."
            exit 1
            ;;
    esac

    echo "Instalando kind em /usr/local/bin/kind..."
    chmod +x "./${KIND_FILE}"
    sudo mv "./${KIND_FILE}" /usr/local/bin/kind

    echo "Install Kubeseal on Linux ...."
    curl -OL "https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.31.0/kubeseal-0.31.0-linux-amd64.tar.gz"
    tar -xvzf kubeseal-0.31.0-linux-amd64.tar.gz kubeseal
    sudo install -m 755 kubeseal /usr/local/bin/kubeseal
}

# Função para instalar o kind no macOS
install_on_macos() {
    local arch
    arch="$(uname -m)"
    echo "Sistema operacional detectado: macOS"

    case "${arch}" in
        x86_64)
            echo "Arquitetura: Intel (x86_64)"
            curl -Lo "./${KIND_FILE}" "${KIND_BASE_URL}/kind-darwin-amd64"
            ;;
        arm64)
            echo "Arquitetura: Apple Silicon (arm64)"
            curl -Lo "./${KIND_FILE}" "${KIND_BASE_URL}/kind-darwin-arm64"
            ;;
        *)
            echo "Erro: Arquitetura ${arch} não suportada para macOS."
            exit 1
            ;;
    esac

    echo "Instalando kind em /usr/local/bin/kind..."
    chmod +x "./${KIND_FILE}"
    # Para macOS, /usr/local/bin é um local comum e geralmente já está no PATH
    # Se o diretório não existir ou não tiver permissão, pode ser necessário criá-lo: sudo mkdir -p /usr/local/bin
    mv "./${KIND_FILE}" /usr/local/bin/kind
}


# --- Execução Principal ---

main() {

    # VERIFICA SE O 'kind' JÁ ESTÁ INSTALADO
    if command -v kind &> /dev/null; then
        echo -e "${GREEN}O 'kind' já está instalado no sistema.${NC}"
        echo -e "Versão atual: ${YELLOW}$(kind --version)${NC}"
        echo "Nenhuma ação é necessária."
        exit 0
    fi

    echo -e "${YELLOW}'kind' não encontrado. Iniciando o processo de instalação...${NC}"
    

    local os
    os="$(uname -s)"

    case "${os}" in
        Linux*)
            install_on_linux
            ;;
        Darwin*)
            install_on_macos
            ;;
        *)
            echo "Erro: Sistema operacional ${os} não suportado."
            exit 1
            ;;
    esac

    echo -e "\n${GREEN}Instalação concluída com sucesso!${NC}"
    echo "Verificando a versão do kind:"
    kind --version
}

# Chama a função principal para iniciar o script
main
