document.addEventListener("DOMContentLoaded", () => {
    // Agora a URL da API é apenas um caminho relativo!
    const API_URL = "/chat"; // <-- MUITO MAIS SIMPLES!

    const form = document.getElementById("prompt-form");
    const promptInput = document.getElementById("prompt-input");
    const submitButton = document.getElementById("submit-button");
    const responseArea = document.getElementById("response-area");
    const loadingIndicator = document.getElementById("loading-indicator");

    // O resto do código continua exatamente o mesmo
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const prompt = promptInput.value.trim();
        if (!prompt) {
            alert("Por favor, digite um prompt.");
            return;
        }

        submitButton.disabled = true;
        loadingIndicator.style.display = "block";
        responseArea.textContent = "";

        try {
            const response = await fetch(API_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ prompt: prompt }),
            });

            if (!response.ok) {
                throw new Error(`Erro na API: ${response.statusText}`);
            }

            const data = await response.json();
            markedResponse = marked.parse(data.response);
            console.log(markedResponse)
            responseArea.innerHTML = markedResponse;

        } catch (error) {
            console.error("Falha ao buscar resposta:", error);
            responseArea.textContent = "Desculpe, ocorreu um erro ao se comunicar com a API.";
        } finally {
            submitButton.disabled = false;
            loadingIndicator.style.display = "none";
        }
    });
});
