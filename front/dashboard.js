// dashboard.js

document.addEventListener('DOMContentLoaded', () => {
    const studentNameElement = document.getElementById('student-name');
    const enrolledListElement = document.getElementById('enrolled-courses-list');
    const availableListElement = document.getElementById('available-courses-list');
    const finishedListElement = document.getElementById('finished-courses-list');
    const statusMessageElement = document.getElementById('status-message');
    const logoutButton = document.getElementById('logout-button');

    function setStatusMessage(message, type) {
        statusMessageElement.textContent = message;
        // Assumant que #status-message a la classe .message-area en HTML ou que vous l'ajoutez ici
        // statusMessageElement.className = 'message-area'; // Si pas déjà en HTML
        if (type === 'success') {
            statusMessageElement.classList.remove('error-message'); // S'assurer qu'elle n'y est pas
            statusMessageElement.classList.add('success-message');
        } else if (type === 'error') {
            statusMessageElement.classList.remove('success-message');
            statusMessageElement.classList.add('error-message');
        } else { // type 'info' ou neutre
            statusMessageElement.classList.remove('success-message', 'error-message');
        }
    }

    function clearStatusMessageAfterDelay(delay = 3000) {
        // Vérifier si le message est un message d'action avant de l'effacer
        const currentText = statusMessageElement.textContent || "";
        if (currentText.startsWith('Marking') ||
            currentText.includes('finished!') ||
            currentText.startsWith('Disenroll') ||
            currentText.startsWith('Successfully disenrolled!') ||
            currentText.startsWith('Enrollment') ||
            currentText.startsWith('Successfully enrolled!')) {
            setTimeout(() => {
                statusMessageElement.textContent = '';
                statusMessageElement.classList.remove('success-message', 'error-message');
            }, delay);
        }
    }


    function renderCourses(courses, targetElement, courseStatusType) {
        targetElement.innerHTML = '';

        if (!courses || courses.length === 0) {
            let message = 'No courses found.';
            if (courseStatusType === 'enrolled') message = 'No courses currently enrolled.';
            else if (courseStatusType === 'available') message = 'No courses available for enrollment.';
            else if (courseStatusType === 'finished') message = 'No courses finished yet.';
            targetElement.innerHTML = `<li>${message}</li>`;
            return;
        }

        courses.forEach(course => {
            const listItem = document.createElement('li');
            let buttonsHtml = '';
            if (courseStatusType === 'available') {
                buttonsHtml = `<button class="enroll-button" data-course-id="${course.course_id}">Enroll</button>`;
            } else if (courseStatusType === 'enrolled') {
                // Les classes sont définies dans style.css et seront stylées individuellement
                buttonsHtml = `
                    <button class="mark-finished-button" data-course-id="${course.course_id}">Mark as Finished</button>
                    <button class="disenroll-button" data-course-id="${course.course_id}">Disenroll</button>
                `;
            } else if (courseStatusType === 'finished') {
                buttonsHtml = `<span class="status-badge">Completed</span>`;
            }

            listItem.innerHTML = `
                <h3>${course.name || 'Unnamed Course'}</h3> 
                <p>${course.description || 'No description available.'}</p>
                <div class="course-actions">
                    ${buttonsHtml}
                </div>
            `;
            targetElement.appendChild(listItem);
        });
    }

    async function fetchDashboardData() {
        try {
            const response = await fetch('/api/dashboard');
            if (response.ok) {
                const data = await response.json();
                if (data.student && data.student.name) {
                    studentNameElement.textContent = data.student.name;
                } else {
                    studentNameElement.textContent = 'User'; // Fallback
                }
                // Correction: les booléens pour le type de cours étaient mal passés dans la version précédente
                renderCourses(data.enrolled || [], enrolledListElement, 'enrolled');
                renderCourses(data.available || [], availableListElement, 'available');
                renderCourses(data.finished || [], finishedListElement, 'finished');
            } else if (response.status === 401 || response.status === 403) {
                console.log('Unauthorized access, redirecting to login.');
                setStatusMessage('Session expired or unauthorized. Redirecting to login...', 'error');
                setTimeout(() => { window.location.href = '/login.html'; }, 2000); // Assumant que login.html est login.html
            }
            else {
                const errorText = await response.text(); // Obtenir plus de détails si ce n'est pas du JSON
                console.error('Failed to fetch dashboard data:', response.status, errorText);
                setStatusMessage(`Error loading dashboard: ${response.statusText || 'Unknown error'}`, 'error');
                enrolledListElement.innerHTML = '<li>Could not load enrolled courses.</li>';
                availableListElement.innerHTML = '<li>Could not load available courses.</li>';
                finishedListElement.innerHTML = '<li>Could not load finished courses.</li>';
            }
        } catch (error) {
            console.error('Error during fetchDashboardData:', error);
            setStatusMessage('Could not connect to server to load dashboard.', 'error');
            enrolledListElement.innerHTML = '<li>Error loading enrolled courses.</li>';
            availableListElement.innerHTML = '<li>Error loading available courses.</li>';
            finishedListElement.innerHTML = '<li>Error loading finished courses.</li>';
        }
    }

    async function enrollInCourse(courseId) {
        setStatusMessage('Enrolling...', 'info');
        try {
            const response = await fetch('/api/enroll', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', },
                body: JSON.stringify({ courseId: courseId }),
            });
            const responseData = await response.json().catch(() => null); // Gérer le cas où la réponse n'est pas JSON

            if (response.ok) {
                setStatusMessage(responseData.message || 'Successfully enrolled!', 'success');
                await fetchDashboardData();
            } else {
                setStatusMessage(responseData?.message || `Enrollment failed (Status: ${response.status})`, 'error');
                console.error('Enrollment failed:', responseData || response.status);
            }
        } catch (error) {
            console.error('Error during enrollInCourse:', error);
            setStatusMessage('An error occurred during enrollment.', 'error');
        }
        clearStatusMessageAfterDelay();
    }

    async function disenrollFromCourse(courseId) {
        setStatusMessage('Disenrolling...', 'info');
        try {
            const response = await fetch('/api/disenroll', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', },
                body: JSON.stringify({ courseId: courseId }),
            });
            const responseData = await response.json().catch(() => null);

            if (response.ok) {
                setStatusMessage(responseData.message || 'Successfully disenrolled!', 'success');
                await fetchDashboardData();
            } else {
                setStatusMessage(responseData?.message || `Disenrollment failed (Status: ${response.status})`, 'error');
                console.error('Disenrollment failed:', responseData || response.status);
            }
        } catch (error) {
            console.error('Error during disenrollFromCourse:', error);
            setStatusMessage('An error occurred during disenrollment.', 'error');
        }
        clearStatusMessageAfterDelay();
    }

    async function markCourseAsFinished(courseId) {
        setStatusMessage('Marking as finished...', 'info');
        try {
            const response = await fetch('/api/course/finish', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', },
                body: JSON.stringify({ courseId: courseId }),
            });
            const responseData = await response.json().catch(() => null);

            if (response.ok) {
                setStatusMessage(responseData.message || 'Course marked as finished!', 'success');
                await fetchDashboardData();
            } else {
                setStatusMessage(responseData?.message || `Failed to mark as finished (Status: ${response.status})`, 'error');
                console.error('Mark as finished failed:', responseData || response.status);
            }
        } catch (error) {
            console.error('Error during markCourseAsFinished:', error);
            setStatusMessage('An error occurred while marking the course as finished.', 'error');
        }
        clearStatusMessageAfterDelay();
    }


    // --- Event Listeners ---
    if (availableListElement) {
        availableListElement.addEventListener('click', (event) => {
            if (event.target.classList.contains('enroll-button')) {
                const courseId = event.target.dataset.courseId;
                if (courseId) {
                    enrollInCourse(courseId);
                } else {
                    console.error('Enroll button clicked but course ID not found.');
                    setStatusMessage('Error: Could not identify course to enroll.', 'error');
                }
            }
        });
    } else {
        console.error('Available courses list element not found!');
    }

    if (enrolledListElement) {
        enrolledListElement.addEventListener('click', (event) => {
            const target = event.target;
            const courseId = target.dataset.courseId;

            if (!courseId) return;

            if (target.classList.contains('disenroll-button')) {
                // Optionnel: if (confirm('Are you sure?')) disenrollFromCourse(courseId);
                disenrollFromCourse(courseId);
            } else if (target.classList.contains('mark-finished-button')) {
                markCourseAsFinished(courseId);
            }
        });
    } else {
        console.error('Enrolled courses list element not found!');
    }

    if (logoutButton) {
        logoutButton.addEventListener('click', async () => {
            setStatusMessage('Logging out...', 'info');
            try {
                await fetch('/api/logout', { method: 'POST' });
            } catch (error) {
                console.warn('Logout request failed:', error);
            } finally {
                // Rediriger vers login.html (page de connexion)
                window.location.href = '/login.html';
            }
        });
    } else {
        console.warn('Logout button not found!');
    }

    fetchDashboardData();
});