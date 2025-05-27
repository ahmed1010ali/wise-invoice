const dropArea = document.getElementById('drop-area');
const fileInput = document.getElementById('file-input');
const fileList = document.getElementById('file-list');
const predictButton = document.getElementById('predict-button');
const uploadResult = document.getElementById('upload-result');
const backendUrl = '/predict';
let selectedFile = null;

// File input change
fileInput.addEventListener('change', () => {
  selectedFile = fileInput.files[0];
  updateFileList(fileInput.files);
  predictButton.classList.remove('hidden');
});

// Predict button click
predictButton.addEventListener('click', async () => {
  if (!selectedFile) return;

  const formData = new FormData();
  formData.append("file", selectedFile);

  try {
    const response = await fetch(backendUrl, {
      method: "POST",
      body: formData
    });

    const resultText = await response.text();
    uploadResult.innerText = resultText;
  } catch (err) {
    console.error("Prediction failed:", err);
    uploadResult.innerText = "Prediction failed.";
  }
});

// Drag & drop handlers
dropArea.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropArea.classList.add('bg-gray-100', 'border-blue-500');
});

dropArea.addEventListener('dragleave', () => {
  dropArea.classList.remove('bg-gray-100', 'border-blue-500');
});

dropArea.addEventListener('drop', (e) => {
  e.preventDefault();
  dropArea.classList.remove('bg-gray-100', 'border-blue-500');
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    selectedFile = files[0];
    updateFileList(files);
    predictButton.classList.remove('hidden');
  }
});

// Show file name
function updateFileList(files) {
  fileList.innerHTML = '';
  if (files.length > 0) {
    const ul = document.createElement('ul');
    for (let i = 0; i < files.length; i++) {
      const li = document.createElement('li');
      li.textContent = files[i].name;
      li.className = "text-gray-700";
      ul.appendChild(li);
    }
    fileList.appendChild(ul);
  }
}

// Click drop area to open file dialog
dropArea.addEventListener('click', () => {
  fileInput.click();
});

// Chatbot logic
const chatSend = document.getElementById('chat-send');
const chatInput = document.getElementById('chat-input');
const chatMessages = document.getElementById('chat-messages');
const chatbotButton = document.getElementById('chatbot-button');
const chatbotContainer = document.getElementById('chatbot-container');

// Show chatbot UI when button is clicked
chatbotButton.addEventListener('click', () => {
  chatbotContainer.classList.toggle('hidden');
  chatInput.focus();
});

// Send message to chatbot
chatSend.addEventListener('click', async () => {
  const message = chatInput.value.trim();
  if (!message) return;

  // Append user's message
  const userMsg = document.createElement('div');
  userMsg.className = "bg-blue-100 text-blue-800 rounded-md py-2 px-3 self-end mb-1 text-left";
  userMsg.textContent = message;
  chatMessages.appendChild(userMsg);

  chatInput.value = '';
  chatInput.disabled = true;
  chatSend.disabled = true;

  try {
    const response = await fetch('/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_message: message,        // ✅ match your backend model
        use_report_agent: false       // ✅ send default value
      })
    });

    const result = await response.json();
    const replyMsg = document.createElement('div');
    replyMsg.className = "bg-gray-100 text-gray-800 rounded-md py-2 px-3 self-start mb-1 text-left";
    replyMsg.textContent = result.response;
    chatMessages.appendChild(replyMsg);

  } catch (err) {
    console.error("Chat failed:", err);
    const errorMsg = document.createElement('div');
    errorMsg.className = "bg-red-100 text-red-800 rounded-md py-2 px-3 self-start mb-1 text-left";
    errorMsg.textContent = "❌ حدث خطأ أثناء الاتصال بالخادم.";
    chatMessages.appendChild(errorMsg);
  }

  chatInput.disabled = false;
  chatSend.disabled = false;
  chatInput.focus();
});

// Optional: support Enter key to send
chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    chatSend.click();
  }
});
chatMessages.scrollTop = chatMessages.scrollHeight;
