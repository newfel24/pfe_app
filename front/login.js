// login.js

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const errorMessage = document.getElementById('error-message');

    if (loginForm) {
        loginForm.addEventListener('submit', async (event) => {
            event.preventDefault(); // Prevent default form submission

            const email = emailInput.value;
            const password = passwordInput.value;

            // Clear previous error messages
            errorMessage.textContent = '';

            // Basic validation
            if (!email || !password) {
                errorMessage.textContent = 'Please enter both email and password.';
                return;
            }

            try {
                const response = await fetch('/api/login', { // Your Flask login endpoint
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ email: email, password: password }),
                });

                if (response.ok) {
                    // Login successful
                    console.log('Login successful');
                    // Redirect to the dashboard page
                    window.location.href = '/home.html'; // Assumes home.html is at the root
                } else {
                    // Login failed - Handle errors from backend
                    const errorData = await response.json().catch(() => null); // Try to parse error JSON
                    const message = errorData?.message || `Login failed (Status: ${response.status})`;
                    errorMessage.textContent = message;
                    console.error('Login failed:', message);
                }
            } catch (error) {
                // Network error or other issue
                console.error('Login request failed:', error);
                errorMessage.textContent = 'An error occurred during login. Please try again later.';
            }
        });
    } else {
        console.error('Login form not found!');
    }
});
