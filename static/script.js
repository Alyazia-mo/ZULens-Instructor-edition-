document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("review-form");
  const reviewInput = document.getElementById("review");
  const warningBox = document.getElementById("warning-box");
  const submitButton = form?.querySelector("button[type='submit']");

  async function checkToneLive(text) {
    const res = await fetch("/check-tone", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ review: text })
    });

    const result = await res.json();
    return result;
  }

  // Live Tone Checking
  if (reviewInput) {
    reviewInput.addEventListener("input", async () => {
      const reviewText = reviewInput.value.trim();
      if (reviewText.length < 5) {
        warningBox.style.display = "none";
        submitButton.disabled = true;
        return;
      }

      const { sentiment, warning } = await checkToneLive(reviewText);

      if (warning) {
        warningBox.innerHTML = warning;
        warningBox.style.display = "block";
        submitButton.disabled = true;
      } else {
        warningBox.style.display = "none";
        submitButton.disabled = false;
      }
    });
  }

  // Submit Handler
  if (form) {
    form.addEventListener("submit", async function (e) {
      e.preventDefault();

      const instructor = document.getElementById("professor").value.trim();
      const course = document.getElementById("course").value.trim();
      const rating = parseInt(document.getElementById("rating").value.trim());
      const review = reviewInput.value.trim();

      if (!instructor || !course || !rating || !review) {
        alert("Please fill in all required fields.");
        return;
      }

      const wordCount = review.split(/\s+/).filter(w => w.length > 0).length;
      if (wordCount < 5) {
        alert("⚠️ Please write at least 5 words in your review.");
        return;
      }

      const reviewData = { instructor, course, rating, review };

      try {
        const response = await fetch("/submit-review", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(reviewData)
        });

        const result = await response.json();

        if (response.status === 401) {
          const modal = new bootstrap.Modal(document.getElementById("loginModal"));
          modal.show();
          return;
        }

        if (response.ok) {
          alert(`✅ Review submitted!\nSentiment: ${result.sentiment}\nSummary: ${result.summary}`);
          form.reset();
          warningBox.style.display = "none";
        } else {
          alert("❌ Error: " + (result.error || "Something went wrong"));
        }
      } catch (error) {
        console.error("Error:", error);
        alert("❌ Server error. Please make sure the backend is running.");
      }
    });
  }
 // logout
  document.getElementById("logout-btn")?.addEventListener("click", async () => {
    try {
      const res = await fetch("/logout", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        }
      });
  
      const data = await res.json();
      if (res.ok && data.redirect) {
        window.location.href = data.redirect;
      } else {
        alert("Logout failed.");
      }
    } catch (err) {
      console.error("Logout error:", err);
      alert("Something went wrong.");
    }
  });
  
  
  // Chatbot
  const chatbotToggle = document.getElementById("chatbot-toggle");
  const chatbotModal = document.getElementById("chatbot-modal");
  const closeChatbot = document.getElementById("close-chatbot");
  const chatInput = document.getElementById("chat-input");

  if (chatbotToggle && chatbotModal && closeChatbot) {
    chatbotToggle.addEventListener("click", () => {
      chatbotModal.style.display = "block";
    
      const log = document.getElementById("chat-log");
      if (!log.innerHTML.includes("ZULens Bot:</strong> Hi 👋")) {
        log.innerHTML += `<p><strong>ZULens Bot:</strong> Hi 👋 I'm here to help you explore courses and professors. Ask me anything!</p>`;
      }
    
      setTimeout(() => chatInput.focus(), 200);
    });
    

    closeChatbot.addEventListener("click", () => {
      chatbotModal.style.display = "none";
    });
  }

  if (chatInput) {
    chatInput.addEventListener("keypress", async (e) => {
      if (e.key === "Enter") {
        const input = e.target.value.trim();
        if (!input) return;

        const log = document.getElementById("chat-log");
        log.innerHTML += `<p><strong>You:</strong> ${input}</p>`;
        e.target.value = "";

        const res = await fetch("/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: input })
        });

        const data = await res.json();
        log.innerHTML += `<p><strong>ZULens Bot:</strong> ${data.reply.replace(/\n/g, "<br>")}</p>`;
        log.scrollTop = log.scrollHeight;
      }
    });
  }
});
