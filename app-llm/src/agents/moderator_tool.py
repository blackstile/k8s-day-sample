import json
import logging
import google.generativeai as genai
from opentelemetry import trace

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
        logger.info(f"ADK Tool: Executando ferramenta de moderação de conteúdo.")
        current_span = trace.get_current_span()
        current_span.set_attribute("app.validation.type", validation_type)
        current_span.set_attribute("app.validation.text", text_to_validate)
        
        model = genai.GenerativeModel('gemini-1.5-pro-latest') 
        generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
        prompt = f"""
        Você é um sistema de classificação binária. Analise o texto abaixo e determine se ele contém linguagem de baixo calão, ofensas, discurso de ódio, xingamentos ou profanidades. Seja rigoroso em sua avaliação
        Texto: "{text_to_validate}"
        Responda APENAS com um objeto JSON válido contendo uma única chave "inapropriado" e o valor booleano correspondente.
        """
        try:
            response = model.generate_content(prompt, generation_config=generation_config)
            is_inappropriate = json.loads(response.text).get("inapropriado", False)
            current_span.set_attribute("app.is_inappropriate", is_inappropriate)
            return is_inappropriate
        except Exception as e:
            logger.error(f"Erro na ferramenta de moderação: {e}. Bloqueando por segurança.")
            return True
