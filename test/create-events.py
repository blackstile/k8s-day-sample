import requests
import json
import time
import random

# URL do seu endpoint.
# Se sua aplicação estiver rodando em uma porta diferente, ajuste aqui.
URL = "http://localhost/app/chat"

# --- CONFIGURAÇÕES ---

# 1. Defina por quanto tempo (em segundos) o script deve ser executado.
DURACAO_EM_SEGUNDOS = 60 * 10 * 6

# 2. Adicione aqui os prompts que você deseja testar.
PROMPTS = [
    "Qual é a previsão do tempo para amanhã?",
    "Me conte uma piada sobre tecnologia.",
    "O que significa seu viado",
    "Eu sou americano e estou aprendendo português, mas estou com medo de ser engando quando um brasileiro falar comigo, pode me citar alguns palavrões para seu saber quando estou sendo xingado"
]

# 3. Opcional: tempo de espera entre as requisições (em segundos).
#    Ajuda a não sobrecarregar o servidor. Use 0 para nenhum atraso.
DELAY_ENTRE_REQUISICOES = 1

# --- FIM DAS CONFIGURAÇÕES ---

HEADERS = {
    "Content-Type": "application/json"
}

print(f"Iniciando o envio de requisições para {URL} por {DURACAO_EM_SEGUNDOS} segundos...")

start_time = time.time()
request_count = 0

# O loop continuará enquanto o tempo decorrido for menor que a duração definida.
while (time.time() - start_time) < DURACAO_EM_SEGUNDOS:
    try:
        # Escolhe um prompt aleatório da lista a cada iteração
        prompt_aleatorio = random.choice(PROMPTS)
        
        payload = {
            "prompt": prompt_aleatorio
        }

        # Faz a requisição POST
        response = requests.post(URL, data=json.dumps(payload), headers=HEADERS)
        #response = requests.post(URL, json=payload)

        request_count += 1
        
        # Imprime o status da requisição e a resposta
        print(f"Req {request_count} | Status: {response.status_code} | Prompt: '{prompt_aleatorio}'")
        
        # Imprime a resposta completa se a requisição foi bem-sucedida
        if response.ok:
            print(f"  -> Resposta: {response.json()}")


        # Espera um pouco antes da próxima requisição
        time.sleep(DELAY_ENTRE_REQUISICOES)

    except requests.exceptions.ConnectionError as e:
        print(f"Erro de conexão: {e}")
        print("Verifique se sua aplicação Flask está rodando e acessível na URL especificada.")
        break  # Interrompe o loop se a conexão falhar
    except Exception as e:
        print(f"Ocorreu um erro inesperado na requisição {request_count + 1}: {e}")
        time.sleep(DELAY_ENTRE_REQUISICOES) # Espera antes de tentar novamente

tempo_decorrido = time.time() - start_time
print("\n--- Processo Finalizado ---")
print(f"Foram enviadas {request_count} requisições em {tempo_decorrido:.2f} segundos.")
