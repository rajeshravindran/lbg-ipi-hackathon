document.addEventListener('DOMContentLoaded', function() {
    const triggerBtn = document.querySelector('.floating-chatbot');
    const chatbotWindow = document.getElementById('avivaChatbotWindow');
    const closeBtn = document.getElementById('avivaChatbotClose');
    const minimizeBtn = document.getElementById('avivaChatbotMinimize');

    if (triggerBtn && chatbotWindow) {
        // Show chatbot on trigger click
        triggerBtn.addEventListener('click', function(e) {
            e.preventDefault();
            chatbotWindow.classList.add('is-open');
            triggerBtn.setAttribute('aria-expanded', 'true');
        });

        // Hide chatbot on close
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                chatbotWindow.classList.remove('is-open');
                triggerBtn.setAttribute('aria-expanded', 'false');
            });
        }

        // Minimize functionality (same as close per requirements or just hide)
        if (minimizeBtn) {
            minimizeBtn.addEventListener('click', function() {
                chatbotWindow.classList.remove('is-open');
                triggerBtn.setAttribute('aria-expanded', 'false');
            });
        }
    }
});
