class ContentModerationError(Exception):
    """Lançado quando o conteúdo é detectado como inapropriado."""
    def __init__(self, message, block_type):
        self.message = message
        self.block_type = block_type  # 'prompt' ou 'response'
        super().__init__(self.message)

class HallucinationError(Exception):
    """Lançado quando uma possível alucinação do modelo é detectada."""
    def __init__(self, message, reasoning):
        self.message = message
        self.reasoning = reasoning
        super().__init__(self.message)
