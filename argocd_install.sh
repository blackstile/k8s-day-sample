#!/bin/bash
set -euo pipefail

ARGO_NS="argocd"
#MANIFEST_URL="https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml"
MANIFEST_URL="argocd-manifest-install.yaml"
TIMEOUT="180s"

usage() {
  cat <<EOF
Uso:
  $0 -i        # Instala o ArgoCD (usa seu snippet base)
  $0 -p        # Mostra a senha do admin do ArgoCD
  $0 -u        # Desinstala o ArgoCD (remove recursos e o namespace)
  $0 -r        # Desinstala e instala novamente
EOF
}

decode_b64() {
  # Compatível com Linux (base64 -d) e macOS (base64 -D)
  if base64 --help >/dev/null 2>&1; then
    base64 --decode 2>/dev/null || base64 -D
  else
    base64 -D
  fi
}

install_argocd() {
  echo "📦 Criando namespace ${ARGO_NS} (se ainda não existir)..."
  kubectl get ns "${ARGO_NS}" >/dev/null 2>&1 || kubectl create namespace "${ARGO_NS}"

  echo "⬇️ Instalando ArgoCD..."
  kubectl apply -n "${ARGO_NS}" -f "${MANIFEST_URL}"

  echo "⏳ Aguardando deployments ficarem prontos (timeout ${TIMEOUT})..."
  kubectl wait --for=condition=Available deployment --all -n "${ARGO_NS}" --timeout="${TIMEOUT}"

  echo "🔑 Buscando senha inicial do admin..."
  # aguarda o secret existir (caso ainda esteja criando)
  for i in {1..30}; do
    if kubectl -n "${ARGO_NS}" get secret argocd-initial-admin-secret >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done

  ADMIN_PASS=$(kubectl -n "${ARGO_NS}" get secret argocd-initial-admin-secret \
    -o jsonpath="{.data.password}" | decode_b64)

  echo "==================================================="
  echo "✅ Instalação concluída!"
  echo "🌐 Acesse: https://localhost:8080"
  echo "👤 Usuário: admin"
  echo "🔑 Senha: ${ADMIN_PASS}"
  echo "==================================================="
  echo "⚡ Para acessar a UI, rode em outro terminal:"
  echo "kubectl port-forward svc/argocd-server -n ${ARGO_NS} 8080:443"
}

uninstall_argocd() {
  echo "🧹 Removendo recursos do ArgoCD..."
  # Caso já tenha sido removido antes, ignore erros
  kubectl delete -n "${ARGO_NS}" -f "${MANIFEST_URL}" --ignore-not-found=true || true

  echo "🗂  Removendo namespace ${ARGO_NS}..."
  kubectl delete namespace "${ARGO_NS}" --ignore-not-found=true || true

  echo "⏳ Aguardando remoção completa do namespace (se aplicável)..."
  for i in {1..60}; do
    if ! kubectl get ns "${ARGO_NS}" >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done

  echo "✅ Desinstalação concluída."
}

show_admin_pass(){
    ADMIN_PASS=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
    echo "==================================================="
    echo "✅ Instalação concluída!"
    echo "🌐 Acesse: https://localhost/argocd"
    echo "👤 Usuário: admin"
    echo "🔑 Senha: ${ADMIN_PASS}"
    echo "==================================================="
}

case "${1:-}" in
  -i) install_argocd ;;
  -u) uninstall_argocd ;;
  -r) uninstall_argocd; install_argocd ;;
  -p) show_admin_pass ;;
  *)  usage; exit 1 ;;
esac