// Assuming you have a reference to your chat messages container
var chatMessages = document.getElementById("chat-messages");

// Function to scroll to the bottom
function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Function to handle user input and display messages
async function sendMessage() {
  var userInput = document.getElementById("user-input");
  var message = userInput.value;
  userInput.value = "";
  // append user message
  var userMessage = document.createElement("div");
  userMessage.className = "message user-message";
  userMessage.innerHTML = message;
  document.getElementById("chat-messages").appendChild(userMessage);
  // Send the user input to the server
  var response = await fetch("/send_message", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message: message }),
  });
  var data = await response.json();

  // Display the server response
  var serverMessage = document.createElement("div");
  serverMessage.className = "message server-message";
  serverMessage.innerHTML = data.response;
  document.getElementById("chat-messages").appendChild(serverMessage);
  scrollToBottom();
}

// Event listener for send button click
document.getElementById("send-button").addEventListener("click", sendMessage);

// Event listener for enter key press
document
  .getElementById("user-input")
  .addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      sendMessage();
    }
  });
