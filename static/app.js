var typed = new Typed("#user-input", {
  strings: [
    "what have i been listening to?",
    "what's my favorite song? what are some recs you can give?",
    "is my taste trash?",
    "what's the best song ever?",
  ],
  typeSpeed: 30,
  loop: true,
});
document.getElementById("user-input").addEventListener("click", function () {
  typed.stop();
  document.getElementById("user-input").value = "";
});
// Assuming you have a reference to your chat messages container
var chatMessages = document.getElementById("chat-messages");

// Function to scroll to the bottom
function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function extractSongName(message) {
  const embedUrlResponse = await fetch("/get_song_embed", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message: message }),
  });
  const embedData = await embedUrlResponse.json();
  if (embedData.song_embed_url) {
    console.log(embedData.song_embed_url);
    return embedData.song_embed_url;
  }
  return null;
}
const sentSongEmbedUrls = new Set();
let messageCount = 0;

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
  scrollToBottom();
  //while waiting for the server to respond, display a loading message
  var loadingMessage = document.createElement("div");
  loadingMessage.className = "message loading-message";
  loadingMessage.innerHTML = "typing...";
  document.getElementById("chat-messages").appendChild(loadingMessage);
  scrollToBottom();
  // Send the user input to the server
  var response = await fetch("/send_message", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message: message }),
  });
  var data = await response.json();
  // Remove the loading message
  document.getElementById("chat-messages").removeChild(loadingMessage);

  // Display the server response
  var serverMessage = document.createElement("div");
  serverMessage.className = "message server-message";
  serverMessage.innerHTML = data.response;
  document.getElementById("chat-messages").appendChild(serverMessage);
  scrollToBottom();
  const songEmbedUrl = await extractSongName(serverMessage.innerHTML);
  if (songEmbedUrl && !sentSongEmbedUrls.has(songEmbedUrl)) {
    // Add the song embed url to the set of sent song embed urls
    sentSongEmbedUrls.add(songEmbedUrl);
    // Create a mini popup embed that plays the song
    const embed = document.createElement("iframe");
    embed.className = "song-embed";
    embed.src = songEmbedUrl + "?autoplay=true";
    embed.width = 300;
    embed.height = 80;
    document.getElementById("chat-messages").appendChild(embed);
  }

  messageCount++;

  // If the message count is even, remove a song from the set
  if (messageCount % 3 === 0) {
    const songToRemove = sentSongEmbedUrls.values().next().value;
    sentSongEmbedUrls.delete(songToRemove);
  }

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

document.getElementById("logout").addEventListener("click", function () {
  window.location.href = "/logout";
});
