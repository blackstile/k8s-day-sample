# test_app.py

import unittest
from unittest.mock import patch, MagicMock
import json

# Importe a classe que você quer testar, não a aplicação Flask
from src.agents.moderator_tool import ModeratorTool
from src.agents.hallucination_validator_tool import HallucinationValidatorTool

class TestAgentTools(unittest.TestCase):

    # Use 'patch' para substituir a chamada real à API do Gemini por um objeto falso (mock)
    @patch('google.generativeai.GenerativeModel')
    def test_moderator_tool_detects_inappropriate_content(self, MockGenerativeModel):
        """
        Testa se a ModeratorTool identifica corretamente o conteúdo quando o mock da API retorna 'true'.
        """
        # Configure o nosso mock para se comportar como a API real faria
        mock_response = MagicMock()
        mock_response.text = json.dumps({"inapropriado": True})
        
        # Faça com que a instância do modelo mockado retorne nossa resposta falsa
        mock_model_instance = MockGenerativeModel.return_value
        mock_model_instance.generate_content.return_value = mock_response

        # Agora, chame a ferramenta. Ela usará nosso modelo falso em vez do real.
        result = ModeratorTool.validate("este é um texto ofensivo", "prompt_moderation")

        # Verifique se a ferramenta retornou o resultado esperado
        self.assertTrue(result, "A ferramenta deveria retornar True para conteúdo inapropriado")
        
        # Verifique se o método da API foi chamado
        mock_model_instance.generate_content.assert_called_once()

    @patch('google.generativeai.GenerativeModel')
    def test_moderator_tool_allows_appropriate_content(self, MockGenerativeModel):
        """
        Testa se a ModeratorTool permite conteúdo quando o mock da API retorna 'false'.
        """
        mock_response = MagicMock()
        mock_response.text = json.dumps({"inapropriado": False})
        
        mock_model_instance = MockGenerativeModel.return_value
        mock_model_instance.generate_content.return_value = mock_response

        result = ModeratorTool.validate("este é um texto normal", "prompt_moderation")

        self.assertFalse(result, "A ferramenta deveria retornar False para conteúdo apropriado")
        mock_model_instance.generate_content.assert_called_once()

    @patch('google.generativeai.GenerativeModel')
    def test_hallucination_validator_detects_hallucination(self, MockGenerativeModel):
        """
        Testa se o HallucinationValidatorTool identifica uma alucinação.
        """
        mock_response = MagicMock()
        mock_response.text = json.dumps({"is_hallucination": True})

        mock_model_instance = MockGenerativeModel.return_value
        mock_model_instance.generate_content.return_value = mock_response

        result = HallucinationValidatorTool.validate(
            original_prompt="Qual a capital da França?",
            response_text="A capital da França é Berlim."
        )

        self.assertTrue(result, "A ferramenta deveria retornar True para uma alucinação")
        mock_model_instance.generate_content.assert_called_once()

# Permite executar os testes diretamente com 'python test_app.py'
if __name__ == '__main__':
    unittest.main()

