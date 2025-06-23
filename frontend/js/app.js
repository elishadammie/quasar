// frontend/js/script.js (Updated to handle sources)

document.addEventListener("DOMContentLoaded", () => {
    const userInput = document.getElementById("user-input");
    const sendButton = document.getElementById("send-button");
    const chatBox = document.getElementById("chat-box");
    const citationBox = document.getElementById("citation-box"); // Get the citation panel
    // const apiUrl = "http://localhost:8000/api/v1/chat";
    const apiUrl = "/api/v1/chat";

    function addMessage(html, sender) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", `${sender}-message`);
        messageDiv.innerHTML = html; // Use innerHTML to render links
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function updateContextPanel(sources) {
        citationBox.innerHTML = ''; // Clear previous citations
        if (sources && sources.length > 0) {
            const list = document.createElement('ul');
            list.style.paddingLeft = '20px';
            sources.forEach((source, index) => {
                const item = document.createElement('li');
                // Display filename and page number
                item.innerText = `${index + 1}. ${source.source} (Page: ${source.page || 'N/A'})`;
                list.appendChild(item);
            });
            citationBox.appendChild(list);
        } else {
            citationBox.innerText = 'No sources were used for this answer.';
        }
    }

    async function sendMessage() {
        const question = userInput.value.trim();
        if (question === "") return;

        addMessage(question, "user");
        userInput.value = "";
        
        // Clear the context panel and show a thinking message
        updateContextPanel([]); 
        const thinkingMessageDiv = document.createElement("div");
        thinkingMessageDiv.classList.add("message", "assistant-message");
        thinkingMessageDiv.innerText = "Quasar is thinking...";
        chatBox.appendChild(thinkingMessageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;

        try {
            const response = await fetch(apiUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: question }),
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const data = await response.json();
            
            // Update the message with the real answer
            thinkingMessageDiv.innerHTML = data.answer; // Use innerHTML for citations
            
            // Update the context panel with the sources
            updateContextPanel(data.sources);

        } catch (error) {
            console.error("Error fetching from API:", error);
            thinkingMessageDiv.innerText = "Sorry, I encountered an error.";
        }
    }

    sendButton.addEventListener("click", sendMessage);
    userInput.addEventListener("keypress", (event) => {
        if (event.key === "Enter") sendMessage();
    });

    addMessage("Hello! I am Quasar. How can I help you with your documents today?", "assistant");
});