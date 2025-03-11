let currentStep = 1;
let generatedQuestions = [];

document.addEventListener('DOMContentLoaded', function() {
    setupForms();
    loadStudents();
});

function setupForms() {
    document.getElementById('generateForm').addEventListener('submit', handleGenerate);
    document.getElementById('assignForm').addEventListener('submit', handleAssign);
}

async function loadStudents() {
    try {
        const response = await fetch('/api/teacher/students');
        const students = await response.json();
        
        const select = document.querySelector('select[name="students"]');
        select.innerHTML = students.map(student => 
            `<option value="${student.id}">${student.email}</option>`
        ).join('');
    } catch (error) {
        console.error('Error loading students:', error);
    }
}

async function handleGenerate(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    try {
        // Show loading state
        const submitButton = e.target.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.textContent = 'Generating...';

        const response = await fetch('/api/generate-quiz', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (data.error) {
            alert(data.error);
            return;
        }
        
        // Store the generated questions and metadata
        generatedQuestions = data.questions;
        quizTitle = formData.get('title');
        quizTopic = formData.get('topic');
        
        displayQuestions();
        nextStep();
    } catch (error) {
        console.error('Error generating quiz:', error);
        alert('Failed to generate quiz questions');
    } finally {
        // Reset button state
        const submitButton = e.target.querySelector('button[type="submit"]');
        submitButton.disabled = false;
        submitButton.textContent = 'Generate Questions';
    }
}

// Update the displayQuestions function's template literals
function displayQuestions() {
    const container = document.getElementById('questionsContainer');
    container.innerHTML = generatedQuestions.map((q, index) => `
        <div class="question-item p-4 border rounded-lg">
            <div class="flex justify-between items-start mb-2">
                <h3 class="font-medium">Question ${index + 1}</h3>
                <button type="button" onclick="removeQuestion(${index})" class="text-red-600 hover:text-red-800">
                    Remove
                </button>
            </div>
            <div class="mb-4">
                <textarea
                    class="w-full p-2 border rounded mb-2"
                    oninput="updateQuestion(${index}, 'question_text', this.value)"
                >${q.question_text}</textarea>
            </div>
            <div class="space-y-2">
                ${q.options.map((opt, optIndex) => `
                    <div class="flex items-center space-x-2">
                        <input type="radio" 
                            name="correct_${index}" 
                            ${opt === q.correct_answer ? 'checked' : ''}
                            onchange="updateCorrectAnswer(${index}, ${optIndex})"
                        >
                        <input type="text" 
                            class="flex-1 p-2 border rounded"
                            value="${opt}"
                            oninput="updateOption(${index}, ${optIndex}, this.value)"
                        >
                    </div>
                `).join('')}
            </div>
            ${q.Explanation_of_correct_answer ? `
                <div class="mt-4">
                    <label class="block text-sm font-medium text-gray-700">Explanation</label>
                    <textarea
                        class="w-full p-2 border rounded"
                        oninput="updateQuestion(${index}, 'Explanation_of_correct_answer', this.value)"
                    >${q.Explanation_of_correct_answer}</textarea>
                </div>
            ` : ''}
        </div>
    `).join('');
}

// Add these functions after displayQuestions()

function updateQuestion(index, field, value) {
    if (index >= 0 && index < generatedQuestions.length) {
        generatedQuestions[index][field] = value;
        console.log(`Updated question ${index, field}:`, value); // Debug log
    }
}

function updateOption(index, optionIndex, value) {
    if (index >= 0 && index < generatedQuestions.length) {
        generatedQuestions[index].options[optionIndex] = value;
        
        // If this option was the correct answer, update it
        if (generatedQuestions[index].correct_answer === generatedQuestions[index].options[optionIndex]) {
            generatedQuestions[index].correct_answer = value;
        }
        console.log(`Updated option ${optionIndex} for question ${index}:`, value); // Debug log
    }
}

function updateCorrectAnswer(index, optionIndex) {
    if (index >= 0 && index < generatedQuestions.length) {
        generatedQuestions[index].correct_answer = generatedQuestions[index].options[optionIndex];
        console.log(`Updated correct answer for question ${index}:`, generatedQuestions[index].correct_answer); // Debug log
    }
}

function removeQuestion(index) {
    if (confirm('Are you sure you want to remove this question?')) {
        generatedQuestions.splice(index, 1);
        displayQuestions(); // Refresh the display
        console.log('Question removed, remaining questions:', generatedQuestions.length); // Debug log
    }
}

// Replace the existing handleAssign function
async function handleAssign(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    // Validate questions before sending
    if (!generatedQuestions || generatedQuestions.length === 0) {
        alert('No questions available to assign');
        return;
    }

    // Get submit button for loading state
    const submitButton = e.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = 'Assigning...';

    try {
        // Create the request payload
        const payload = {
            title: document.querySelector('input[name="title"]').value,
            topic: document.querySelector('input[name="topic"]').value,
            questions: generatedQuestions,
            students: Array.from(formData.getAll('students')),
            due_date: formData.get('due_date')
        };

        const response = await fetch('/api/teacher/assign-quiz', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        if (result.success) {
            alert('Quiz assigned successfully! Email has been sent');
            // Redirect to teacher dashboard
            window.location.href = '/';  // This will redirect to the root route which handles dashboard routing
        } else {
            throw new Error(result.error || 'Failed to assign quiz');
        }
    } catch (error) {
        console.error('Error assigning quiz:', error);
        alert('Failed to assign quiz: ' + (error.message || 'Unknown error'));
    } finally {
        // Reset button state if there was an error
        submitButton.disabled = false;
        submitButton.textContent = 'Assign Quiz';
    }
}

function nextStep() {
    if (currentStep < 3) {
        document.getElementById(`step${currentStep}`).classList.remove('bg-blue-500');
        document.getElementById(`step${currentStep}`).classList.add('bg-green-500');
        document.getElementById(`line${currentStep}`).classList.remove('bg-gray-200');
        document.getElementById(`line${currentStep}`).classList.add('bg-green-500');
        
        currentStep++;
        
        document.getElementById(`step${currentStep}`).classList.remove('bg-gray-200');
        document.getElementById(`step${currentStep}`).classList.add('bg-blue-500');
        
        updateVisibility();
    }
}

function prevStep() {
    if (currentStep > 1) {
        document.getElementById(`step${currentStep}`).classList.remove('bg-blue-500');
        document.getElementById(`step${currentStep}`).classList.add('bg-gray-200');
        document.getElementById(`line${currentStep-1}`).classList.remove('bg-green-500');
        document.getElementById(`line${currentStep-1}`).classList.add('bg-gray-200');
        
        currentStep--;
        
        document.getElementById(`step${currentStep}`).classList.remove('bg-green-500');
        document.getElementById(`step${currentStep}`).classList.add('bg-blue-500');
        
        updateVisibility();
    }
}

function updateVisibility() {
    ['generateQuestions', 'reviewQuestions', 'assignQuiz'].forEach((id, index) => {
        document.getElementById(id).classList.toggle('hidden', index + 1 !== currentStep);
    });
}