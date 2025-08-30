from prometheus_client import Counter, Histogram

# --- Métricas Prometheus Originais ---
REQUESTS_TOTAL = Counter(
    'app_requests_total',
    'Total de requisições recebidas no endpoint /chat'
)
VALIDATION_EVENTS_TOTAL = Counter(
    'app_validation_events_total',
    'Total de eventos de validação executados pelos agentes',
    ['validation_type']
)

# --- Novas Métricas Prometheus para LLM ---
LLM_API_LATENCY = Histogram(
    'llm_api_latency_seconds',
    'Latência das chamadas à API do LLM',
    ['model_name']
)
LLM_PROMPT_TOKENS_TOTAL = Counter(
    'llm_prompt_tokens_total',
    'Total de tokens enviados nos prompts para o LLM',
    ['model_name']
)
LLM_RESPONSE_TOKENS_TOTAL = Counter(
    'llm_response_tokens_total',
    'Total de tokens recebidos nas respostas do LLM',
    ['model_name']
)
LLM_API_ERRORS_TOTAL = Counter(
    'llm_api_errors_total',
    'Total de erros durante chamadas à API do LLM',
    ['model_name']
)