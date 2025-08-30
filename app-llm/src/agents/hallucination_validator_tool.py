import json
import logging
import time
import google.generativeai as genai
from opentelemetry import trace 

from src.metrics import (
    LLM_API_LATENCY,
    LLM_PROMPT_TOKENS_TOTAL,
    LLM_RESPONSE_TOKENS_TOTAL,
    LLM_API_ERRORS_TOTAL
)


logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__) 

class HallucinationValidatorTool:
    @staticmethod
    @tracer.start_as_current_span("hallucination_validator.validate")
    def validate(original_prompt: str, response_text: str) -> bool:
        """
        Compara a resposta com a pergunta para detectar alucinações. Retorna 'true' se for uma alucinação.
        Args:
            original_prompt: A pergunta feita pelo usuário.
            response_text: A resposta gerada pela IA.
        """
        current_span = trace.get_current_span()
        current_span.set_attribute("app.prompt_length", len(original_prompt))
        current_span.set_attribute("app.response_length", len(response_text))
        
        logger.info("ADK Tool: Executando ferramenta de validação de alucinação.")
        
        model_name = 'gemini-1.5-pro-latest'
        model = genai.GenerativeModel(model_name) 
        generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
        prompt = f"""
        Você é um agente de verificação de fatos. Analise o par abaixo. Uma 'alucinação' ocorre se a resposta for inventada, incoerente ou não responder à pergunta original.
        PERGUNTA ORIGINAL: "{original_prompt}"
        RESPOSTA GERADA: "{response_text}"
        A resposta gerada é uma alucinação? Responda APENAS com um objeto JSON válido contendo uma única chave "is_hallucination" e o valor booleano correspondente.
        """
        start_time = time.monotonic()
        try:
            response = model.generate_content(prompt, generation_config=generation_config)
            if hasattr(response, 'usage_metadata'): # <--- Adicionado
                usage = response.usage_metadata
                LLM_PROMPT_TOKENS_TOTAL.labels(model_name=model_name).inc(usage.prompt_token_count)
                LLM_RESPONSE_TOKENS_TOTAL.labels(model_name=model_name).inc(usage.candidates_token_count)

            is_hallucination = json.loads(response.text).get("is_hallucination", False)
            if is_hallucination:
                logger.info(f"Alucinação gerada: {response_text}")
            current_span.set_attribute("app.is_hallucination", is_hallucination)
            return is_hallucination
        except Exception as e:
            logger.error(f"Erro na ferramenta de validação de alucinação: {e}. Bloqueando por segurança.")
            LLM_API_ERRORS_TOTAL.labels(model_name=model_name).inc()
            return True
        finally:
            latency = time.monotonic() - start_time 
            LLM_API_LATENCY.labels(model_name=model_name).observe(latency)

