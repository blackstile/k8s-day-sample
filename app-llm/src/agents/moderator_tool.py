import json
import logging
import time
import google.generativeai as genai
from opentelemetry import trace

from src.metrics import (
    LLM_API_LATENCY,
    LLM_PROMPT_TOKENS_TOTAL,
    LLM_RESPONSE_TOKENS_TOTAL,
    LLM_VALIDATION_BLOCKED_TOTAL,
    LLM_API_ERRORS_TOTAL
)


logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

class ModeratorTool:
    @staticmethod
    @tracer.start_as_current_span("moderator_tool.validate")
    def validate(text_to_validate: str, validation_type: str) -> bool:
        """
        Analisa um texto e retorna 'true' se for inapropriado, 'false' caso contrário.
        Args:
            text_to_validate: O texto que precisa ser validado.
        """
        logger.info(f"ModeratorTools validation_type={validation_type}")
        start_time = time.monotonic()
        logger.info(f"ADK Tool: Executando ferramenta de moderação de conteúdo.")
        current_span = trace.get_current_span()
        current_span.set_attribute("app.validation.type", validation_type)
        current_span.set_attribute("app.validation.text", text_to_validate)
        
        model_name = 'gemini-1.5-pro-latest'
        model = genai.GenerativeModel(model_name) 
        generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
        prompt = f"""
        Você é um sistema de classificação binária. Analise o texto abaixo e determine se ele contém linguagem de baixo calão, ofensas, discurso de ódio, xingamentos ou profanidades. Seja rigoroso em sua avaliação
        Texto: "{text_to_validate}"
        Responda APENAS com um objeto JSON válido contendo uma única chave "inapropriado" e o valor booleano correspondente.
        """
        try:
            response = model.generate_content(prompt, generation_config=generation_config)
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                LLM_PROMPT_TOKENS_TOTAL.labels(model_name=model_name).inc(usage.prompt_token_count)
                LLM_RESPONSE_TOKENS_TOTAL.labels(model_name=model_name).inc(usage.candidates_token_count)

            is_inappropriate = json.loads(response.text).get("inapropriado", False)
            if is_inappropriate: 
                logger.info(f"validation_type={validation_type} - is_inappropriate={is_inappropriate}")
                LLM_VALIDATION_BLOCKED_TOTAL.labels(model_name=model_name, validation_type=validation_type).inc()
            current_span.set_attribute("app.is_inappropriate", is_inappropriate)
            return is_inappropriate
        except Exception as e:
            logger.error(f"Erro na ferramenta de moderação: {e}. Bloqueando por segurança.")
            LLM_API_ERRORS_TOTAL.labels(model_name=model).inc()
            return True
        finally:            
            latency = time.monotonic() - start_time
            LLM_API_LATENCY.labels(model_name=model_name).observe(latency)

