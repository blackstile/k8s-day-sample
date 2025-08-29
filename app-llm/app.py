import os
import logging
from flask import Flask, request, jsonify, render_template
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter
import google.generativeai as genai
from google.adk.tools import FunctionTool
from google.adk.agents import LlmAgent 
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.agents.moderator_tool import ModeratorTool
from src.agents.hallucination_validator_tool import HallucinationValidatorTool
from src.metrics_wrapper import wrap_tool_with_metric

# --- Configuração do Logger, Flask, etc. ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
app = Flask(__name__)
metrics = PrometheusMetrics(app, group_by='endpoint')

# --- Métricas Prometheus ---
REQUESTS_TOTAL = Counter(
    'app_requests_total',
    'Total de requisições recebidas no endpoint /chat'
)
VALIDATION_EVENTS_TOTAL = Counter(
    'app_validation_events_total',
    'Total de eventos de validação executados pelos agentes',
    ['validation_type']
)

logging.info(f"**** ROOT CONTEXT: {os.environ.get('APP_ROOT_CONTEXT')}")
root_path = os.environ.get('APP_ROOT_CONTEXT') or ""

# --- Configuração da API do Gemini ---
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("A variável de ambiente GEMINI_API_KEY não foi definida.")
    genai.configure(api_key=api_key)
    logger.info("API Key do Gemini configurada com sucesso.")
except Exception as e:
    logger.critical(f"Falha ao inicializar o Gemini: {e}")

# --- Envolvendo as Ferramentas com as Métricas ---
prompt_moderator_tool = wrap_tool_with_metric(
    tool_function=ModeratorTool.validate,
    counter=VALIDATION_EVENTS_TOTAL,
    labels={'validation_type': 'prompt_moderation'}
)
prompt_moderator_tool.__name__ = "prompt_content_moderator"
prompt_moderator_tool.__doc__ = "Use esta ferramenta para verificar se a PERGUNTA ORIGINAL DO USUÁRIO é apropriada. Retorna 'true' se for inapropriada."

response_moderator_tool = wrap_tool_with_metric(
    tool_function=ModeratorTool.validate,
    counter=VALIDATION_EVENTS_TOTAL,
    labels={'validation_type': 'response_moderation'}
)
response_moderator_tool.__name__ = "response_content_moderator"
response_moderator_tool.__doc__ = "Use esta ferramenta para verificar se a RESPOSTA QUE VOCÊ GEROU é apropriada. Retorna 'true' se for inapropriada."

hallucination_tool_with_metric = wrap_tool_with_metric(
    tool_function=HallucinationValidatorTool.validate,
    counter=VALIDATION_EVENTS_TOTAL,
    labels={'validation_type': 'hallucination_check'}
)
hallucination_tool_with_metric.__name__ = "hallucination_validator"
hallucination_tool_with_metric.__doc__ = "Use esta ferramenta para verificar se uma resposta é uma alucinação. Retorna 'true' se for uma alucinação."

# --- Prompt do Agente ADK ---
AGENT_PROMPT = """
Você é um assistente de IA seguro e prestativo. Seu trabalho é responder às perguntas do usuário, mas apenas se elas passarem por um rigoroso processo de validação.

Ferramentas disponíveis que você DEVE usar:
- `prompt_content_moderator`: Verifica se a pergunta do usuário é ofensiva.
- `response_content_moderator`: Verifica se a resposta que você está prestes a dar é ofensiva.
- `hallucination_validator`: Verifica se a sua resposta é uma alucinação ou inconsistente com a pergunta.

Siga este fluxo de trabalho para CADA pergunta:
1.  Primeiro, use a ferramenta `prompt_content_moderator` para analisar a pergunta do usuário. Se a ferramenta retornar `true`, PARE imediatamente e responda exatamente com a string: "ERRO: CONTEÚDO IMPRÓPRIO NA ENTRADA".
2.  Se a pergunta for apropriada, gere uma resposta inicial para o usuário. Não a mostre ainda.
3.  Em seguida, use a ferramenta `response_content_moderator` para analisar a sua própria resposta gerada. Se a ferramenta retornar `true`, descarte a resposta e responda exatamente com: "ERRO: RESPOSTA IMPRÓPRIA GERADA".
4.  Se a sua resposta for apropriada, use a ferramenta `hallucination_validator`, passando a pergunta original e a sua resposta. Se a ferramenta retornar `true`, descarte a resposta e responda exatamente com: "ERRO: RESPOSTA INVÁLIDA GERADA".
5.  Se a sua resposta passar por TODAS as verificações, e somente neste caso, entregue a resposta final ao usuário.
"""

APP_NAME = "k8s_day_app"
USER_ID = "1980"
SESSION_ID = "session1980"

# --- Criação do Agente Principal ---
try:
    main_agent = LlmAgent(
        name="main_agent",
        instruction=AGENT_PROMPT,
        tools=[
            FunctionTool(prompt_moderator_tool),
            FunctionTool(response_moderator_tool),
            FunctionTool(hallucination_tool_with_metric)
        ],
        model='gemini-1.5-pro-latest'
    )
    logger.info("Agente ADK inicializado com ferramentas com métricas.")
    session_service = InMemorySessionService()
    session = session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    runner = Runner(agent=main_agent, app_name=APP_NAME, session_service=session_service)

except Exception as e:
    logger.critical(f"Falha ao criar o Agente ADK: {e}")
    print(f"Falha ao criar o Agente ADK: {e}")
    main_agent = None



def call_agent(query):
    """
    Helper function to call the agent with a query.
    """
    content = types.Content(role="user", parts=[types.Part(text=query)])
    events = runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)
    final_response = None
    for event in events:
        if event.is_final_response():
            final_response = event.content.parts[0].text
            print("Agent Response: ", final_response) 
    return final_response;


@app.route("/")
def home():
    """Serve a página principal do chat."""
    return render_template("index.html", context_path=root_path)

@app.route("/chat", methods=["POST"])
def chat():
    """Recebe o prompt do usuário e retorna a resposta do agente."""
    REQUESTS_TOTAL.inc()

    if not main_agent:
        return jsonify({"error": "O serviço de IA não está configurado corretamente."}), 503

    prompt = request.get_json().get("prompt")
    if not prompt:
        return jsonify({"error": "O campo 'prompt' é obrigatório"}), 400

    try:

        response_text = call_agent(prompt)
        
        if response_text.startswith("ERRO:"):
            logger.warning(f"Agente ADK bloqueou a solicitação: {response_text}")
            return jsonify({"error": response_text}), 400

        return jsonify({"response": response_text})
        
    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado na chamada do agente ADK: {e}", exc_info=True)
        return jsonify({"error": "Ocorreu um erro inesperado no processamento do agente."}), 500

if __name__ == "__main__":
    logger.info("Iniciando a aplicação Flask com arquitetura de agentes ADK.")
    app.run(host="0.0.0.0", port=5000)

