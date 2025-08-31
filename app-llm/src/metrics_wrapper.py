import logging
from functools import wraps
import inspect

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
    sig = inspect.signature(tool_function)
    tool_params = sig.parameters

    @wraps(tool_function)
    def metric_wrapper(*args, **kwargs):
        logger.info(f"Métrica registrada para o contador com labels: {labels}")
        counter.labels(**labels).inc()
        
        if 'validation_type' in tool_params:
            kwargs['validation_type'] = labels.get('validation_type', 'unknown')

        result = tool_function(*args, **kwargs)

    
        return result

    return metric_wrapper
