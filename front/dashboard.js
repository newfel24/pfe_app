// dashboard.js

document.addEventListener('DOMContentLoaded', () => {
    const studentNameElement = document.getElementById('student-name');
    const enrolledListElement = document.getElementById('enrolled-courses-list');
    const availableListElement = document.getElementById('available-courses-list');
    const statusMessageElement = document.getElementById('status-message');
    const logoutButton = document.getElementById('logout-button');

    // Function to render a list of courses
    function renderCourses(courses, targetElement, isAvailableList) {
        targetElement.innerHTML = ''; // Clear previous content (like "Loading...")

        if (!courses || courses.length === 0) {
            targetElement.innerHTML = `<li>No ${isAvailableList ? 'available' : 'enrolled'} courses found.</li>`;
            return;
        }

        courses.forEach(course => {
            const listItem = document.createElement('li');
            listItem.innerHTML = `
                <h3>${course.name || 'Unnamed Course'}</h3>
                <p>${course.description || 'No description available.'}</p>
                ${isAvailableList ?
                    `<button class="enroll-button" data-course-id="${course.course_id}">Enroll</button>` :
                    '' // Don't show enroll button for already enrolled courses
                }
            `;
            targetElement.appendChild(listItem);
        });
    }

    // Function to fetch dashboard data from the backend
    async function fetchDashboardData() {
        try {
            // Assume cookies handle auth, otherwise add Authorization header if using JWT
            const response = await fetch('/api/dashboard'); // Your Flask dashboard endpoint

            if (response.ok) {
                const data = await response.json();

                // Update student name (assuming backend sends student info)
                if (data.student && data.student.name) {
                    studentNameElement.textContent = data.student.name;
                } else {
                    studentNameElement.textContent = 'User'; // Fallback
                }

                // Render enrolled and available courses
                renderCourses(data.enrolled || [], enrolledListElement, false);
                renderCourses(data.available || [], availableListElement, true);

            } else if (response.status === 401 || response.status === 403) {
                // Unauthorized or Forbidden - redirect to login
                console.log('Unauthorized access, redirecting to login.');
                window.location.href = '/login.html';
            }
            else {
                // Other errors fetching data
                console.error('Failed to fetch dashboard data:', response.status);
                statusMessageElement.textContent = `Error loading dashboard: ${response.statusText}`;
                enrolledListElement.innerHTML = '<li>Could not load enrolled courses.</li>';
                availableListElement.innerHTML = '<li>Could not load available courses.</li>';
            }
        } catch (error) {
            console.error('Error during fetchDashboardData:', error);
            statusMessageElement.textContent = 'Could not connect to server to load dashboard.';
            enrolledListElement.innerHTML = '<li>Error loading enrolled courses.</li>';
            availableListElement.innerHTML = '<li>Error loading available courses.</li>';
        }
    }

    // Function to handle course enrollment
    async function enrollInCourse(courseId) {
        statusMessageElement.textContent = 'Enrolling...'; // Provide feedback
        try {
            const response = await fetch('/api/enroll', { // Your Flask enroll endpoint
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    // Add Authorization header here if using JWT tokens
                },
                body: JSON.stringify({ courseId: courseId }),
            });

            if (response.ok) {
                statusMessageElement.textContent = 'Successfully enrolled!';
                // Refresh the dashboard data to show updated lists
                await fetchDashboardData();
            } else {
                // Handle enrollment errors (e.g., already enrolled, prerequisites not met)
                const errorData = await response.json().catch(() => null);
                const message = errorData?.message || `Enrollment failed (Status: ${response.status})`;
                statusMessageElement.textContent = `Enrollment failed: ${message}`;
                console.error('Enrollment failed:', message);
            }
        } catch (error) {
            console.error('Error during enrollInCourse:', error);
            statusMessageElement.textContent = 'An error occurred during enrollment.';
        }
        // Optional: Clear status message after a few seconds
        setTimeout(() => { if (statusMessageElement.textContent.startsWith('Enrollment') || statusMessageElement.textContent.startsWith('Successfully')) { statusMessageElement.textContent = '' } }, 5000);
    }

    // --- Event Listeners ---

    // Event listener for enroll buttons (using event delegation)
    if (availableListElement) {
        availableListElement.addEventListener('click', (event) => {
            if (event.target.classList.contains('enroll-button')) {
                const courseId = event.target.dataset.courseId;
                if (courseId) {
                    enrollInCourse(courseId);
                } else {
                    console.error('Enroll button clicked but course ID not found.');
                    statusMessageElement.textContent = 'Error: Could not identify course to enroll.';
                }
            }
        });
    } else {
        console.error('Available courses list element not found!');
    }

    // Event listener for logout button
    if (logoutButton) {
        logoutButton.addEventListener('click', async () => {
            statusMessageElement.textContent = 'Logging out...';
            try {
                // Optional: Call backend logout endpoint if needed for session invalidation
                await fetch('/api/logout', { method: 'POST' });
            } catch (error) {
                console.warn('Logout request failed (may not matter if client-side redirect works):', error);
            } finally {
                // Always redirect to login page
                window.location.href = '/login.html';
            }
        });
    } else {
        console.warn('Logout button not found!'); // Use warn as it might be optional
    }

    // --- Initial Load ---
    // Fetch data when the page loads
    fetchDashboardData();

}); // End DOMContentLoaded
