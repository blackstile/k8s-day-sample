document.addEventListener("DOMContentLoaded", () => {
    
    const API_URL = (contextPath || "") + "/chat"; 

    const form = document.getElementById("prompt-form");
    const promptInput = document.getElementById("prompt-input");
    const submitButton = document.getElementById("submit-button");
    const responseArea = document.getElementById("response-area");
    const loadingIndicator = document.getElementById("loading-indicator");

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

            const data = await response.json();
            if (!response.ok) {
                console.log(`response: `, response)
                if (data.error){
                    responseArea.textContent =  data.error
                    return;
                }
                throw new Error(`Erro na API: ${response.statusText}`);
            }

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
