import os
import logging
import json
import time
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template 
from prometheus_flask_exporter import PrometheusMetrics
from google.generativeai.types import generation_types


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

# 2. Define nossas métricas customizadas para LLM
LLM_CALL_LATENCY = metrics.new_histogram(
    'llm_call_latency_seconds',
    'Latência apenas da chamada à API do Gemini'
)
PROMPT_TOKENS = metrics.new_histogram(
    'llm_prompt_tokens_total',
    'Número de tokens no prompt de entrada'
)
RESPONSE_TOKENS = metrics.new_histogram(
    'llm_response_tokens_total',
    'Número de tokens na resposta gerada pelo LLM'
)
CONTENT_MODERATION_BLOCKS = metrics.new_counter(
    'llm_content_moderation_blocks_total',
    'Total de bloqueios pelo agente moderador',
    labels={'block_type': None} # Label para saber se bloqueou o 'prompt' ou a 'response'
)
LLM_API_ERRORS = metrics.new_counter(
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


# --- NOVA ROTA PARA SERVIR O FRONTEND ---
@app.route("/")
def home():
    """
    Esta rota serve a página principal da aplicação (o frontend).
    """
    logger.info("Servindo a página principal index.html")
    # O Flask procura automaticamente na pasta 'templates'
    return render_template("index.html")
# --- FIM DA NOVA ROTA ---


# --- ROTA DA API (sem alterações na lógica) ---
@app.route("/chat", methods=["POST"])
def chat():
    request_id = request.headers.get('X-Request-ID', 'N/A')
    logger.info(f"Requisição recebida no endpoint /chat. Request ID: {request_id}")

    if not request.is_json:
        logger.warning(f"Requisição inválida (não é JSON). Request ID: {request_id}")
        return jsonify({"error": "Request deve ser do tipo JSON"}), 400

    data = request.get_json()
    prompt = data.get("prompt")

    if not prompt:
        logger.warning(f"Requisição sem o campo 'prompt'. Request ID: {request_id}")
        return jsonify({"error": "O campo 'prompt' é obrigatório"}), 400

    logger.info(f"Enviando prompt para a API do Gemini. Request ID: {request_id}")
    try:
        response = model.generate_content(prompt)
        logger.info(f"Resposta recebida da API do Gemini com sucesso. Request ID: {request_id}")
        logger.info(response.text)
        if is_content_inappropriate(response.text):
            raise ValidationMessageError("O gemini retornou conteudo inapropriado")
        return jsonify({"response": response.text}), 200
    except ValidationMessageError as e:
        # TODO: adicioanr counter prometheus para conteudo inapropriado
        return jsonify({"error": "Conteudo inapropriado retornado pelo Gemini"}), 500
    except Exception as e:
        logger.error(f"Ocorreu um erro ao chamar a API do Gemini. Request ID: {request_id}", exc_info=True)
        return jsonify({"error": "Falha ao se comunicar com a API do Gemini"}), 500
# --- FIM DA ROTA DA API ---

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

if __name__ == "__main__":
    logger.info("Iniciando a aplicação Flask em modo monolítico.")
    app.run(host="0.0.0.0", port=5000)

