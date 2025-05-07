// signup.js
document.addEventListener('DOMContentLoaded', () => {
    const signupForm = document.getElementById('signup-form');
    const nameInput = document.getElementById('name');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirm-password');
    const messageArea = document.getElementById('message-area');

    if (signupForm) {
        signupForm.addEventListener('submit', async (event) => {
            event.preventDefault(); // Prevent default form submission

            const name = nameInput.value.trim();
            const email = emailInput.value.trim();
            const password = passwordInput.value;
            const confirmPassword = confirmPasswordInput.value;

            // Clear previous messages
            messageArea.textContent = '';
            messageArea.className = 'message-area'; // Reset class

            // Basic client-side validation
            if (!name || !email || !password || !confirmPassword) {
                messageArea.textContent = 'Please fill in all fields.';
                messageArea.classList.add('error-message'); // Style as error
                return;
            }

            if (password !== confirmPassword) {
                messageArea.textContent = 'Passwords do not match.';
                messageArea.classList.add('error-message');
                return;
            }

            if (password.length < 6) {
                messageArea.textContent = 'Password must be at least 6 characters long.';
                messageArea.classList.add('error-message');
                return;
            }

            try {
                const response = await fetch('/api/signup', { // Your new Flask signup endpoint
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        name: name,
                        email: email,
                        password: password
                    }),
                });

                const responseData = await response.json();

                if (response.ok) { // Status 200-299
                    messageArea.textContent = responseData.message || 'Signup successful! Redirecting to login...';
                    messageArea.classList.add('success-message'); // Style as success
                    console.log('Signup successful:', responseData);
                    // Redirect to login page after a short delay
                    setTimeout(() => {
                        window.location.href = '/login.html'; // Assuming login page is login.html
                    }, 2000);
                } else {
                    messageArea.textContent = responseData.message || `Signup failed (Status: ${response.status})`;
                    messageArea.classList.add('error-message');
                    console.error('Signup failed:', responseData);
                }
            } catch (error) {
                console.error('Signup request failed:', error);
                messageArea.textContent = 'An error occurred during signup. Please try again later.';
                messageArea.classList.add('error-message');
            }
        });
    } else {
        console.error('Signup form not found!');
    }
});