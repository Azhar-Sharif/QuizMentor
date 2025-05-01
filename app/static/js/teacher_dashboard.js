document.addEventListener('DOMContentLoaded', function() {
    loadTeacherInfo();
    loadDashboardStats();
    loadRecentAssignments();
    loadStudentPerformance();
    setupEventListeners();
    fetchWeakTopics();

    // Desktop dropdown toggle
    const profileDropdown = document.getElementById('profileDropdown');
    const dropdownMenu = document.getElementById('dropdownMenu');

    if (profileDropdown && dropdownMenu) {
        profileDropdown.addEventListener('click', function(event) {
            dropdownMenu.classList.toggle('hidden');
            event.stopPropagation();
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function(event) {
            if (!profileDropdown.contains(event.target)) {
                dropdownMenu.classList.add('hidden');
            }
        });
    }

    // Mobile menu toggle
    const mobileMenuButton = document.getElementById('mobileMenuButton');
    const mobileMenu = document.getElementById('mobileMenu');

    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
    }
});

async function loadTeacherInfo() {
    try {
        const response = await fetch('/api/teacher/info');
        const data = await response.json();
        
        // Update both instances of teacher name
        document.getElementById('teacherName').textContent = data.name;
        document.getElementById('teacherNameDropdown').textContent = data.name;
        document.getElementById('teacherEmail').textContent = data.email;
    } catch (error) {
        console.error('Error loading teacher info:', error);
    }
}

async function loadDashboardStats() {
    try {
        const response = await fetch('/api/teacher/stats');
        const data = await response.json();
        
        document.getElementById('totalStudents').textContent = data.totalStudents;
        document.getElementById('totalQuizzes').textContent = data.totalQuizzes;
        document.getElementById('activeAssignments').textContent = data.activeAssignments;
        document.getElementById('avgClassScore').textContent = `${data.averageScore}%`;
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

async function loadRecentAssignments(filter = 'all') {
    try {
        const response = await fetch(`/api/teacher/assignments?filter=${filter}`);
        const assignments = await response.json();
        const tableBody = document.getElementById('recentAssignmentsBody');
        
        tableBody.innerHTML = assignments.map(assignment => `
            <tr>
                <td class="px-6 py-4 whitespace-nowrap">${assignment.quiz_title}</td>
                <td class="px-6 py-4 whitespace-nowrap">${assignment.student_email}</td>
                <td class="px-6 py-4 whitespace-nowrap">${new Date(assignment.due_date).toLocaleDateString()}</td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 py-1 rounded-full text-xs ${getStatusClass(assignment.status)}">
                        ${assignment.status}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <button onclick="viewAssignment(${assignment.id})" 
                            class="text-blue-600 hover:text-blue-900">
                        View Details
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading assignments:', error);
    }
}

async function loadStudentPerformance() {
    try {
        const response = await fetch('/api/teacher/student-performance');
        const data = await response.json();
        
        updateTopicFilter(data.topics);
        renderPerformanceChart(data.performance);
        renderPerformanceTable(data.performance);
    } catch (error) {
        console.error('Error loading student performance:', error);
    }
}

function setupEventListeners() {
    document.getElementById('topicFilter').addEventListener('change', filterPerformance);
    document.getElementById('sortOrder').addEventListener('change', filterPerformance);
}

function getStatusClass(status) {
    const classes = {
        'pending': 'bg-yellow-100 text-yellow-800',
        'completed': 'bg-green-100 text-green-800',
        'overdue': 'bg-red-100 text-red-800'
    };
    return classes[status] || '';
}

function updateTopicFilter(topics) {
    const select = document.getElementById('topicFilter');
    select.innerHTML = `
        <option value="">All Topics</option>
        ${topics.map(topic => `<option value="${topic}">${topic}</option>`).join('')}
    `;
}

function renderPerformanceChart(data) {
    const ctx = document.getElementById('performanceChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.student_email),
            datasets: [{
                label: 'Average Score',
                data: data.map(item => item.average_score),
                backgroundColor: 'rgba(59, 130, 246, 0.5)',
                borderColor: 'rgb(59, 130, 246)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
}

function renderPerformanceTable(data) {
    const tableBody = document.getElementById('studentPerformanceBody');
    tableBody.innerHTML = data.map(item => `
        <tr>
            <td class="px-6 py-4 whitespace-nowrap">${item.student_email}</td>
            <td class="px-6 py-4 whitespace-nowrap">${item.topic}</td>
            <td class="px-6 py-4 whitespace-nowrap">${item.average_score}%</td>
        </tr>
    `).join('');
}

async function filterPerformance() {
    const topic = document.getElementById('topicFilter').value;
    const order = document.getElementById('sortOrder').value;
    
    try {
        const response = await fetch(`/api/teacher/student-performance?topic=${topic}&order=${order}`);
        const data = await response.json();
        renderPerformanceChart(data.performance);
        renderPerformanceTable(data.performance);
    } catch (error) {
        console.error('Error filtering performance:', error);
    }
}

function viewAssignment(id) {
    window.location.href = `/teacher/assignment/${id}`;
}

function fetchWeakTopics() {
    const weakTopicsList = document.getElementById('weakTopicsList');
    weakTopicsList.innerHTML = '<li>Loading...</li>'; // Show loading state

    fetch('/api/predict-weak-topics')
        .then(response => response.json())
        .then(data => {
            weakTopicsList.innerHTML = ''; // Clear the list
            if (data.weak_topics && data.weak_topics.length > 0) {
                data.weak_topics.forEach(topic => {
                    const li = document.createElement('li');
                    li.textContent = topic;
                    weakTopicsList.appendChild(li);
                });
            } else {
                weakTopicsList.innerHTML = '<li>No weak topics found.</li>';
            }
        })
        .catch(error => {
            console.error('Error fetching weak topics:', error);
            weakTopicsList.innerHTML = '<li>Error fetching weak topics. Please try again later.</li>';
        });
}

// Automatically fetch weak topics when the page loads
document.addEventListener('DOMContentLoaded', fetchWeakTopics);
