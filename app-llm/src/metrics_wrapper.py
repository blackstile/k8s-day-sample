import logging
from functools import wraps

logger = logging.getLogger(__name__)

def wrap_tool_with_metric(tool_function, counter, labels: dict):
    """
    Cria um wrapper em volta de uma função de ferramenta para registrar uma métrica.

    Args:
        tool_function: A função original da ferramenta (ex: ModeratorTool.validate).
        counter: O objeto de contador da Prometheus a ser incrementado.
        labels: Um dicionário de labels para o contador.

    Returns:
        Uma nova função que registra a métrica e depois executa a ferramenta original.
    """
    @wraps(tool_function)
    def metric_wrapper(*args, **kwargs):
        # Passo 1: Incrementar a métrica com as labels corretas
        logger.info(f"Métrica registrada para o contador com labels: {labels}")
        counter.labels(**labels).inc()

        # Passo 2: Executar a função da ferramenta original com seus argumentos
        result = tool_function(*args, **kwargs)

        # Passo 3: Retornar o resultado original
        return result

    return metric_wrapper
