// dashboard.js

document.addEventListener('DOMContentLoaded', () => {
    const studentNameElement = document.getElementById('student-name');
    const enrolledListElement = document.getElementById('enrolled-courses-list');
    const availableListElement = document.getElementById('available-courses-list');
    const statusMessageElement = document.getElementById('status-message');
    const logoutButton = document.getElementById('logout-button');

    // MODIFICATION ICI: Mise à jour de renderCourses
    function renderCourses(courses, targetElement, isAvailableList) {
        targetElement.innerHTML = ''; // Clear previous content

        if (!courses || courses.length === 0) {
            targetElement.innerHTML = `<li>No ${isAvailableList ? 'available' : 'enrolled'} courses found.</li>`;
            return;
        }

        courses.forEach(course => {
            const listItem = document.createElement('li');
            let buttonHtml = '';
            if (isAvailableList) {
                buttonHtml = `<button class="enroll-button" data-course-id="${course.course_id}">Enroll</button>`;
            } else {
                // AJOUT: Bouton Disenroll pour les cours inscrits
                buttonHtml = `<button class="disenroll-button" data-course-id="${course.course_id}">Disenroll</button>`;
            }

            listItem.innerHTML = `
                <h3>${course.name || 'Unnamed Course'}</h3> 
                <p>${course.description || 'No description available.'}</p>
                ${buttonHtml}
            `;
            targetElement.appendChild(listItem);
        });
    }

    async function fetchDashboardData() {
        // ... (contenu existant de fetchDashboardData - pas de changement ici)
        try {
            const response = await fetch('/api/dashboard');
            if (response.ok) {
                const data = await response.json();
                if (data.student && data.student.name) {
                    studentNameElement.textContent = data.student.name;
                } else {
                    studentNameElement.textContent = 'User';
                }
                renderCourses(data.enrolled || [], enrolledListElement, false);
                renderCourses(data.available || [], availableListElement, true);
            } else if (response.status === 401 || response.status === 403) {
                console.log('Unauthorized access, redirecting to login.');
                window.location.href = '/login.html'; // Assumant que login.html est index.html
            }
            else {
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

    async function enrollInCourse(courseId) {
        // ... (contenu existant de enrollInCourse - pas de changement ici)
        statusMessageElement.textContent = 'Enrolling...';
        try {
            const response = await fetch('/api/enroll', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', },
                body: JSON.stringify({ courseId: courseId }),
            });
            if (response.ok) {
                statusMessageElement.textContent = 'Successfully enrolled!';
                await fetchDashboardData();
            } else {
                const errorData = await response.json().catch(() => null);
                const message = errorData?.message || `Enrollment failed (Status: ${response.status})`;
                statusMessageElement.textContent = `Enrollment failed: ${message}`;
                console.error('Enrollment failed:', message);
            }
        } catch (error) {
            console.error('Error during enrollInCourse:', error);
            statusMessageElement.textContent = 'An error occurred during enrollment.';
        }
        setTimeout(() => { if (statusMessageElement.textContent.startsWith('Enrollment') || statusMessageElement.textContent.startsWith('Successfully enrolled!')) { statusMessageElement.textContent = '' } }, 3000);
    }

    // AJOUT: Nouvelle fonction pour se désinscrire
    async function disenrollFromCourse(courseId) {
        statusMessageElement.textContent = 'Disenrolling...';
        try {
            const response = await fetch('/api/disenroll', { // Nouveau point de terminaison backend
                method: 'POST', // Ou DELETE, mais POST est plus simple pour la structure actuelle
                headers: {
                    'Content-Type': 'application/json',
                    // Ajouter l'en-tête d'autorisation si vous utilisez des jetons JWT
                },
                body: JSON.stringify({ courseId: courseId }),
            });

            if (response.ok) {
                statusMessageElement.textContent = 'Successfully disenrolled!';
                // Rafraîchir les données du tableau de bord pour mettre à jour les listes
                await fetchDashboardData();
            } else {
                const errorData = await response.json().catch(() => null); // Essayer de parser l'erreur JSON
                const message = errorData?.message || `Disenrollment failed (Status: ${response.status})`;
                statusMessageElement.textContent = `Disenrollment failed: ${message}`;
                console.error('Disenrollment failed:', message);
            }
        } catch (error) {
            console.error('Error during disenrollFromCourse:', error);
            statusMessageElement.textContent = 'An error occurred during disenrollment.';
        }
        // Optionnel : Effacer le message de statut après quelques secondes
        setTimeout(() => { if (statusMessageElement.textContent.startsWith('Disenroll') || statusMessageElement.textContent.startsWith('Successfully disenrolled!')) { statusMessageElement.textContent = '' } }, 3000);
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
                    statusMessageElement.textContent = 'Error: Could not identify course to enroll.';
                }
            }
        });
    } else {
        console.error('Available courses list element not found!');
    }

    // AJOUT: Gestionnaire d'événements pour les boutons "Disenroll"
    if (enrolledListElement) {
        enrolledListElement.addEventListener('click', (event) => {
            if (event.target.classList.contains('disenroll-button')) {
                const courseId = event.target.dataset.courseId;
                if (courseId) {
                    // Optionnel : Ajouter une confirmation avant de se désinscrire
                    // if (confirm('Are you sure you want to disenroll from this course?')) {
                    //     disenrollFromCourse(courseId);
                    // }
                    disenrollFromCourse(courseId);
                } else {
                    console.error('Disenroll button clicked but course ID not found.');
                    statusMessageElement.textContent = 'Error: Could not identify course to disenroll.';
                }
            }
        });
    } else {
        console.error('Enrolled courses list element not found!');
    }

    if (logoutButton) {
        logoutButton.addEventListener('click', async () => {
            // ... (contenu existant du gestionnaire de déconnexion - pas de changement ici)
            statusMessageElement.textContent = 'Logging out...';
            try {
                await fetch('/api/logout', { method: 'POST' });
            } catch (error) {
                console.warn('Logout request failed:', error);
            } finally {
                window.location.href = '/login.html'; // Assumant que login.html est index.html
            }
        });
    } else {
        console.warn('Logout button not found!');
    }

    fetchDashboardData();
});
