import json
import logging
from google_adk import adk 
import google.generativeai as genai

logger = logging.getLogger(__name__)

class ModeratorTool:
    @staticmethod
    @adk.tool
    def validate(text_to_validate: str) -> bool:
        """
        Analisa um texto e retorna 'true' se for inapropriado, 'false' caso contrário.
        Args:
            text_to_validate: O texto que precisa ser validado.
        """
        logger.info(f"ADK Tool: Executando ferramenta de moderação de conteúdo.")
        
        model = genai.GenerativeModel('gemini-1.5-pro-latest') 
        generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
        prompt = f"""
        Você é um sistema de classificação binária. Analise o texto abaixo e determine se ele contém linguagem de baixo calão, ofensas, discurso de ódio, xingamentos ou profanidades.
        Texto: "{text_to_validate}"
        Responda APENAS com um objeto JSON válido contendo uma única chave "inapropriado" e o valor booleano correspondente.
        """
        try:
            response = model.generate_content(prompt, generation_config=generation_config)
            is_inappropriate = json.loads(response.text).get("inapropriado", False)
            return is_inappropriate
        except Exception as e:
            logger.error(f"Erro na ferramenta de moderação: {e}. Bloqueando por segurança.")
            return True
