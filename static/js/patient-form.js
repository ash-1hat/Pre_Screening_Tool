/**
 * Patient Form Handler for Medical Pre-Screening Tool
 * Manages patient registration, validation, and doctor selection
 */

class PatientFormHandler {
    constructor() {
        this.form = document.getElementById('patient-form');
        this.departmentSelect = document.getElementById('department');
        this.doctorSelect = document.getElementById('doctor');
        this.doctorFields = document.getElementById('doctor-fields');
        this.registrationSummary = document.getElementById('registration-summary');
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadDepartments();
        this.setupDoctorSelectionToggle();
        this.checkForRecognizedPatient();
    }

    setupEventListeners() {
        // Form submission
        this.form.addEventListener('submit', (e) => this.handleFormSubmit(e));

        // Real-time validation
        document.getElementById('name').addEventListener('blur', () => this.validateField('name'));
        document.getElementById('mobile').addEventListener('blur', () => this.validateField('mobile'));
        document.getElementById('age').addEventListener('blur', () => this.validateField('age'));
        document.getElementById('gender').addEventListener('change', () => this.validateField('gender'));

        // Mobile number formatting
        document.getElementById('mobile').addEventListener('input', (e) => this.formatMobile(e));

        // Department selection
        this.departmentSelect.addEventListener('change', () => this.handleDepartmentChange());

        // Form buttons
        document.getElementById('proceed-btn')?.addEventListener('click', () => this.proceedToInterview());
        document.getElementById('edit-btn')?.addEventListener('click', () => this.editInformation());
    }

    setupDoctorSelectionToggle() {
        const radioButtons = document.querySelectorAll('input[name="doctor-selection"]');
        radioButtons.forEach(radio => {
            radio.addEventListener('change', () => this.toggleDoctorFields());
        });
    }

    toggleDoctorFields() {
        const selectedValue = document.querySelector('input[name="doctor-selection"]:checked').value;
        
        if (selectedValue === 'select') {
            this.doctorFields.classList.remove('hidden');
            this.loadDepartments(); // Ensure departments are loaded
        } else {
            this.doctorFields.classList.add('hidden');
            this.departmentSelect.value = '';
            this.doctorSelect.value = '';
        }
    }

    async loadDepartments() {
        if (!this.departmentSelect) return;

        try {
            this.departmentSelect.innerHTML = '<option value="">Loading departments...</option>';
            
            const response = await api.getDepartments();
            
            this.departmentSelect.innerHTML = '<option value="">Select Department</option>';
            
            if (response.departments && response.departments.length > 0) {
                response.departments.forEach(dept => {
                    const option = document.createElement('option');
                    option.value = dept;
                    option.textContent = dept;
                    this.departmentSelect.appendChild(option);
                });
            } else {
                this.departmentSelect.innerHTML = '<option value="">No departments available</option>';
            }
        } catch (error) {
            console.error('Error loading departments:', error);
            this.departmentSelect.innerHTML = '<option value="">Error loading departments</option>';
        }
    }

    async handleDepartmentChange() {
        const selectedDepartment = this.departmentSelect.value;
        
        if (!selectedDepartment) {
            this.doctorSelect.innerHTML = '<option value="">Select department first</option>';
            this.doctorSelect.disabled = true;
            return;
        }

        try {
            this.doctorSelect.innerHTML = '<option value="">Loading doctors...</option>';
            this.doctorSelect.disabled = false;
            
            const response = await api.getDoctorsByDepartment(selectedDepartment);
            
            this.doctorSelect.innerHTML = '<option value="">Select Doctor</option>';
            
            if (response.doctors && response.doctors.length > 0) {
                response.doctors.forEach(doctor => {
                    const option = document.createElement('option');
                    option.value = doctor;
                    option.textContent = `Dr. ${doctor}`;
                    this.doctorSelect.appendChild(option);
                });
            } else {
                this.doctorSelect.innerHTML = '<option value="">No doctors available</option>';
            }
        } catch (error) {
            console.error('Error loading doctors:', error);
            this.doctorSelect.innerHTML = '<option value="">Error loading doctors</option>';
        }
    }

    formatMobile(event) {
        let value = event.target.value.replace(/\D/g, '');
        if (value.length > 10) {
            value = value.substring(0, 10);
        }
        event.target.value = value;
    }

    validateField(fieldName) {
        const field = document.getElementById(fieldName);
        const value = field.value.trim();
        let validation;

        // Clear previous errors
        utils.hideError(`${fieldName}-error`);

        switch (fieldName) {
            case 'name':
                validation = utils.validateName(value);
                break;
            case 'mobile':
                validation = utils.validateMobile(value);
                break;
            case 'age':
                validation = utils.validateAge(value);
                break;
            case 'gender':
                validation = utils.validateGender(value);
                break;
            default:
                return true;
        }

        if (!validation.valid) {
            utils.showError(`${fieldName}-error`, validation.message);
            return false;
        }

        return true;
    }

    validateForm() {
        const fields = ['name', 'mobile', 'age', 'gender'];
        let isValid = true;

        fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        // Validate doctor selection if required
        const doctorSelectionValue = document.querySelector('input[name="doctor-selection"]:checked').value;
        if (doctorSelectionValue === 'select') {
            const department = this.departmentSelect.value;
            const doctor = this.doctorSelect.value;
            
            if (!department) {
                utils.showError('department-error', 'Please select a department');
                isValid = false;
            }
            
            if (!doctor) {
                utils.showError('doctor-error', 'Please select a doctor');
                isValid = false;
            }
        }

        return isValid;
    }

    async handleFormSubmit(event) {
        event.preventDefault();

        if (!this.validateForm()) {
            return;
        }

        const formData = new FormData(this.form);
        const doctorSelectionValue = document.querySelector('input[name="doctor-selection"]:checked').value;
        
        const patientData = {
            name: formData.get('name').trim(),
            mobile: formData.get('mobile').trim(),
            age: parseInt(formData.get('age')),
            gender: formData.get('gender'),
            skip_doctor_selection: doctorSelectionValue === 'skip',
            chosen_department: doctorSelectionValue === 'select' ? formData.get('department') : null,
            chosen_doctor: doctorSelectionValue === 'select' ? formData.get('doctor') : null
        };

        try {
            utils.showLoading('Registering patient...');

            const response = await api.registerPatient(patientData);

            if (response.success) {
                utils.savePatientData(response.patient);
                this.showRegistrationSummary(response.patient);
            } else {
                throw new Error(response.message || 'Registration failed');
            }

        } catch (error) {
            console.error('Registration error:', error);
            alert(`Registration failed: ${error.message}`);
        } finally {
            utils.hideLoading();
        }
    }

    showRegistrationSummary(patientData) {
        const summaryContent = document.getElementById('summary-content');
        
        const summaryHTML = `
            <div class="summary-grid">
                <div class="summary-item">
                    <strong>Name</strong>
                    <span>${patientData.name}</span>
                </div>
                <div class="summary-item">
                    <strong>Age</strong>
                    <span>${patientData.age} years</span>
                </div>
                <div class="summary-item">
                    <strong>Mobile</strong>
                    <span>${patientData.mobile}</span>
                </div>
                <div class="summary-item">
                    <strong>Gender</strong>
                    <span>${patientData.gender}</span>
                </div>
                ${patientData.chosen_doctor ? `
                    <div class="summary-item">
                        <strong>Preferred Doctor</strong>
                        <span>Dr. ${patientData.chosen_doctor} (${patientData.chosen_department})</span>
                    </div>
                ` : `
                    <div class="summary-item">
                        <strong>Doctor Selection</strong>
                        <span>AI will recommend based on assessment</span>
                    </div>
                `}
            </div>
        `;
        
        summaryContent.innerHTML = summaryHTML;
        
        // Hide form and show summary
        this.form.classList.add('hidden');
        this.registrationSummary.classList.remove('hidden');
        
        // Add success animation
        this.registrationSummary.classList.add('slide-up');
    }

    editInformation() {
        this.form.classList.remove('hidden');
        this.registrationSummary.classList.add('hidden');
        this.registrationSummary.classList.remove('slide-up');
    }

    proceedToInterview() {
        // Get session_id from sessionStorage (set during patient data storage)
        const sessionId = sessionStorage.getItem('currentSessionId');
        if (sessionId) {
            // Navigate to interview page with session_id
            window.location.href = `/static/interview.html?session_id=${sessionId}`;
        } else {
            alert('Session not found. Please try again.');
            this.editInformation();
        }
    }

    checkForRecognizedPatient() {
        // Check if patient was recognized via face recognition
        const recognizedPatient = sessionStorage.getItem('recognizedPatient');
        const urlParams = new URLSearchParams(window.location.search);
        
        if (recognizedPatient && urlParams.get('recognized') === 'true') {
            const patientData = JSON.parse(recognizedPatient);
            this.populateFormWithRecognizedData(patientData);
            
            // Clear the session storage
            sessionStorage.removeItem('recognizedPatient');
            
            // Show success message
            this.showRecognitionSuccessMessage(patientData.name);
        }
    }

    populateFormWithRecognizedData(patientData) {
        // Populate form fields with recognized patient data
        document.getElementById('name').value = patientData.name;
        document.getElementById('mobile').value = patientData.mobile;
        document.getElementById('age').value = patientData.age;
        document.getElementById('gender').value = patientData.gender;
        
        // Mark fields as valid
        this.validateField('name');
        this.validateField('mobile');
        this.validateField('age');
        this.validateField('gender');
        
        // Scroll to form
        document.querySelector('.patient-form').scrollIntoView({ behavior: 'smooth' });
    }

    showRecognitionSuccessMessage(patientName) {
        // Create and show success message
        const messageDiv = document.createElement('div');
        messageDiv.className = 'recognition-success-message';
        messageDiv.style.cssText = `
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
            animation: slideDown 0.5s ease-out;
        `;
        messageDiv.innerHTML = `
            <h4><i class="fas fa-check-circle"></i> Welcome back, ${patientName}!</h4>
            <p>Your details have been automatically filled. Please review and proceed.</p>
        `;
        
        // Insert after form header
        const formHeader = document.querySelector('.form-header');
        formHeader.insertAdjacentElement('afterend', messageDiv);
        
        // Remove message after 5 seconds
        setTimeout(() => {
            messageDiv.remove();
        }, 5000);
    }
}

// Initialize form handler when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PatientFormHandler();
});
