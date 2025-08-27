import os
import logging
import json
import time
import threading
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template 
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Histogram, Counter
from google.generativeai.types import generation_types
from google.generativeai.types import BlockedPromptException
from google.api_core import exceptions as api_core_exceptions

class ValidationMessageError(Exception):
    """Custom exception raised when there are insufficient funds."""
    def __init__(self, message="Sua mensagem tem conteudo inapropriado!!!"):
        self.message = message
        super().__init__(self.message)


# --- Configuração do Logger (sem alterações) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Fim da Configuração do Logger ---


app = Flask(__name__)
metrics = PrometheusMetrics(app)

logging.info(f"**** ROOT CONTEXT: {os.environ.get('APP_ROOT_CONTEXT')}")
root_path = os.environ.get('APP_ROOT_CONTEXT')



# 2. Define nossas métricas customizadas para LLM
LLM_CALL_LATENCY = Histogram(
    'llm_call_latency_seconds',
    'Latência apenas da chamada à API do Gemini'
)
PROMPT_TOKENS = Histogram(
    'llm_prompt_tokens_total',
    'Número de tokens no prompt de entrada'
)
RESPONSE_TOKENS = Histogram(
    'llm_response_tokens_total',
    'Número de tokens na resposta gerada pelo LLM'
)
CONTENT_MODERATION_BLOCKS = Counter(
    'llm_content_moderation_blocks_total',
    'Total de bloqueios pelo agente moderador',
    labelnames=['block_type'] # Label para saber se bloqueou o 'prompt' ou a 'response'
)
LLM_API_ERRORS = Counter(
    'llm_api_errors_total',
    'Total de erros específicos da API do LLM'
)


try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.critical("A variável de ambiente GEMINI_API_KEY não foi definida.")
        raise ValueError("A variável de ambiente GEMINI_API_KEY não foi definida.")
    genai.configure(api_key=api_key)
    logger.info("API Key do Gemini configurada com sucesso.")
except ValueError as e:
    pass

model = genai.GenerativeModel('gemini-1.5-pro-latest')
logger.info("Modelo 'gemini-1.5-pro-latest' inicializado.")


@app.route("/")
def home():
    """
    Esta rota serve a página principal da aplicação (o frontend).
    """
    logger.info("Servindo a página principal index.html")
    # O Flask procura automaticamente na pasta 'templates'
    return render_template("index.html", context_path=root_path)
# --- FIM DA NOVA ROTA ---


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    prompt = data.get("prompt")
    if not prompt:
        return jsonify({"error": "O campo 'prompt' é obrigatório"}), 400

    validation_thread_prompt = threading.Thread(
        target=validate_content_and_log_metric,
        args=(prompt, 'prompt')
    )
    validation_thread_prompt.start()


    try:
        # Mede e registra os tokens de entrada
        prompt_token_count = model.count_tokens(prompt).total_tokens
        logger.info(f"Prompt Token count {prompt_token_count}")
        PROMPT_TOKENS.observe(prompt_token_count)
        
        # Mede a latência da chamada ao LLM
        start_time = time.time()
        response = model.generate_content(prompt)
        latency = time.time() - start_time
        LLM_CALL_LATENCY.observe(latency)
        
        llm_response_text = response.text

        # --- VALIDAÇÃO DA SAÍDA ---
        validation_thread_response = threading.Thread(
            target=validate_content_and_log_metric,
            args=(llm_response_text, 'response')
        )
        validation_thread_response.start()

        # Mede e registra os tokens de saída
        response_token_count = model.count_tokens(llm_response_text).total_tokens
        logger.info(f"Response Token count {response_token_count}")
        RESPONSE_TOKENS.observe(response_token_count)

        logger.info("Resposta gerada e validada com sucesso.")
        return jsonify({"response": llm_response_text})

    except api_core_exceptions.ServiceUnavailable as e:
        LLM_API_ERRORS.inc()
        logger.error(f"Erro de comunicação com a API (ServiceUnavailable): {e}", exc_info=True)
        # Forneça uma mensagem de erro que ajude a depurar
        return jsonify({"error": "Falha ao se comunicar com a API. Verifique a chave de API e a conectividade de rede."}), 503

    # 2. Captura o erro de BLOQUEIO DE CONTEÚDO (corrigido)
    except BlockedPromptException as e:
        LLM_API_ERRORS.inc()
        logger.warning(f"Chamada à API do Gemini bloqueada por política de segurança: {e}")
        return jsonify({"error": "A solicitação foi bloqueada pela política de segurança da API."}), 400
        


    except Exception as e:
        # Outros erros genéricos da API ou da aplicação
        LLM_API_ERRORS.inc()
        logger.error(f"Ocorreu um erro na chamada da API: {e}", exc_info=True)
        return jsonify({"error": "Falha ao se comunicar com a API do Gemini."}), 500

# @app.route("/validator", methods=["POST"])
def validator():
    data = request.get_json()
    prompt = data.get("prompt")
    llmResponse =  data.get("llmOutput")
    return jsonify({"isContent": is_content_inappropriate(llmResponse)})

def is_content_inappropriate(text_to_validate: str) -> bool:
    logger.info(f"Iniciando validação de conteúdo.")
    moderator_prompt = f"""
    Você é um Agente Moderador de Conteúdo treinado. Sua única tarefa é analisar o texto e determinar se ele contém linguagem de baixo calão, ofensas, xingamentos ou profanidades em português do Brasil.
    Seja rigoroso. Analise o seguinte texto:
    ---
    {text_to_validate}
    ---
    Sua resposta DEVE ser um objeto JSON válido com uma única chave "inapropriado" e um valor booleano (`true` ou `false`).
    """
    try:
        generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
        moderator_response = model.generate_content(moderator_prompt, generation_config=generation_config)
        response_data = json.loads(moderator_response.text)
        is_inappropriate = response_data.get("inapropriado", False)
        if is_inappropriate:
            logger.warning("Agente Moderador detectou conteúdo inapropriado.")
        else:
            logger.info("Agente Moderador considerou o conteúdo apropriado.")
        return is_inappropriate
    except Exception as e:
        logger.error(f"Erro no serviço de moderação: {e}. Bloqueando por segurança.", exc_info=True)
        return True

def validate_content_and_log_metric(text: str, block_type: str):
    """
    Função alvo para a thread. Valida o conteúdo e incrementa a métrica
    se for considerado impróprio, sem interferir na requisição principal.
    """
    if is_content_inappropriate(text):
        # A métrica é incrementada aqui, em segundo plano.
        CONTENT_MODERATION_BLOCKS.labels(block_type=block_type).inc()
        logger.warning(f"Conteúdo impróprio detectado em segundo plano para o tipo: {block_type}")



if __name__ == "__main__":
    logger.info("Iniciando a aplicação Flask em modo monolítico.")
    app.run(host="0.0.0.0", port=5000)
