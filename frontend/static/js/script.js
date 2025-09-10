// script.js

// Store plans globally
let availablePlans = [];

document.getElementById('registerBtn').onclick = function() {
    const authModal = new bootstrap.Modal(document.getElementById('authModal'));
    document.getElementById('authModalLabel').innerText = 'Register';
    document.getElementById('fullNameField').style.display = 'block';
    document.getElementById('fullName').setAttribute('required', 'required');
    document.getElementById('planField').style.display = 'block';
    document.getElementById('planSelect').setAttribute('required', 'required');
    authForm.reset(); // Clear form fields
    populatePlanSelect();
    authModal.show();
}

// Add login button functionality
document.getElementById('loginBtn').onclick = function() {
    const authModal = new bootstrap.Modal(document.getElementById('authModal'));
    document.getElementById('authModalLabel').innerText = 'Login';
    document.getElementById('fullNameField').style.display = 'none';
    document.getElementById('fullName').removeAttribute('required');
    document.getElementById('planField').style.display = 'none';
    document.getElementById('planSelect').removeAttribute('required');
    document.getElementById('toggleText').innerText = "Don't have an account?";
    document.getElementById('toggleAuth').innerText = 'Register';
    authForm.reset(); // Clear form fields
    authModal.show();
}

const authForm = document.getElementById('authForm');
authForm.onsubmit = async function(e) {
    e.preventDefault();

    const isRegister = document.getElementById('authModalLabel').innerText === 'Register';
    const url = isRegister ? '/auth/register' : '/auth/login';
    
    // Prepare data based on whether it's register or login
    let data;
    if (isRegister) {
        const planId = document.getElementById('planSelect').value;
        console.log('Selected plan ID:', planId);
        console.log('Plan select element:', document.getElementById('planSelect'));
        console.log('Available plans:', availablePlans);
        data = {
            email: document.getElementById('email').value,
            password: document.getElementById('password').value,
            full_name: document.getElementById('fullName').value
        };
        // Only add plan_id if it's not empty
        if (planId && planId !== '') {
            data.plan_id = planId;
        }
        console.log('Registration data being sent:', data);
    } else {
        // For login, we need to use OAuth2 form data format
        const formData = new URLSearchParams();
        formData.append('username', document.getElementById('email').value);
        formData.append('password', document.getElementById('password').value);
        data = formData;
    }

    try {
        let response;
        if (isRegister) {
            response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        } else {
            response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: data
            });
        }

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'An error occurred');
        }

        const result = await response.json();
        
        if (isRegister) {
            // Check if payment is required (redirect to Stripe)
            if (result.requires_payment && result.checkout_url) {
                // Store a flag that registration is pending payment
                localStorage.setItem('registration_pending', 'true');
                localStorage.setItem('registered_email', result.user.email);
                
                // Close modal
                bootstrap.Modal.getInstance(document.getElementById('authModal')).hide();
                
                // Show notification about redirect
                const successToast = new bootstrap.Toast(document.getElementById('successToast'));
                document.querySelector('#successToast .toast-body').innerText = 'Registration successful! Redirecting to payment...';
                successToast.show();
                
                // Redirect to Stripe checkout
                setTimeout(() => {
                    window.location.href = result.checkout_url;
                }, 1500);
            } else {
                // No payment required (Freemium or Starter plan)
                // Close modal and show success notification
                bootstrap.Modal.getInstance(document.getElementById('authModal')).hide();
                const successToast = new bootstrap.Toast(document.getElementById('successToast'));
                document.querySelector('#successToast .toast-body').innerText = 'Registration successful! Please login.';
                successToast.show();
                
                // Switch to login mode after a delay
                setTimeout(() => {
                    document.getElementById('loginBtn').click();
                }, 2000);
            }
        } else {
            // Store token and redirect to dashboard
            localStorage.setItem('access_token', result.access_token);
            bootstrap.Modal.getInstance(document.getElementById('authModal')).hide();
            
            const successToast = new bootstrap.Toast(document.getElementById('successToast'));
            document.querySelector('#successToast .toast-body').innerText = 'Login successful! Redirecting...';
            successToast.show();
            
            setTimeout(() => {
                window.location.href = '/dashboard.html';
            }, 1500);
        }
    } catch (error) {
        console.error('Error:', error);
        const errorToast = new bootstrap.Toast(document.getElementById('errorToast'));
        document.getElementById('errorToastBody').innerText = error.message;
        errorToast.show();
    }
}

async function loadPlans() {
    const res = await fetch("/clients/plans");
    const plans = await res.json();
    availablePlans = plans; // Store for later use
    const pricingContainer = document.getElementById("pricing-plans");
    
    // Get user's location info
    const locationInfo = await getUserLocation();
    const isIndian = locationInfo.country === 'IN';

    plans.forEach((plan, index) => {
        // Get formatted price using utility function
        const formattedPrice = formatPrice(plan.price, isIndian);
        
        // Fill pricing
        const card = document.createElement("div");
        card.className = "col-lg-3 col-md-6";
        const popularBadge = plan.name === 'Standard' ? '<span class="badge bg-warning text-dark position-absolute top-0 end-0 m-3">Popular</span>' : '';
        // Build feature list based on plan type
        let featuresList = '';
        
        // Website/Sites feature
        if (plan.max_sites === -1) {
            featuresList += '<li class="mb-2"><i class="fas fa-check text-success me-2"></i><strong>Unlimited</strong> websites</li>';
        } else if (plan.max_sites === 1) {
            featuresList += '<li class="mb-2"><i class="fas fa-check text-success me-2"></i><strong>1</strong> website</li>';
        } else {
            featuresList += `<li class="mb-2"><i class="fas fa-check text-success me-2"></i><strong>${plan.max_sites}</strong> websites</li>`;
        }
        
        // Document feature
        if (plan.max_documents === -1) {
            featuresList += '<li class="mb-2"><i class="fas fa-check text-success me-2"></i><strong>Unlimited</strong> documents</li>';
        } else if (plan.max_documents > 0) {
            featuresList += `<li class="mb-2"><i class="fas fa-check text-success me-2"></i>Up to <strong>${plan.max_documents}</strong> documents</li>`;
        } else if (plan.can_upload_docs) {
            featuresList += '<li class="mb-2"><i class="fas fa-check text-success me-2"></i>Document uploads</li>';
        } else {
            featuresList += '<li class="mb-2 text-muted"><i class="fas fa-times text-danger me-2"></i>No document uploads</li>';
        }
        
        // Voice feature
        if (plan.can_use_voice) {
            featuresList += '<li class="mb-2"><i class="fas fa-check text-success me-2"></i><strong>Voice input</strong> (Speech-to-text)</li>';
        } else {
            featuresList += '<li class="mb-2 text-muted"><i class="fas fa-times text-danger me-2"></i>Voice input</li>';
        }
        
        // Messages feature (only show if not -1)
        if (plan.max_messages !== -1) {
            featuresList += `<li class="mb-2"><i class="fas fa-check text-success me-2"></i><strong>${plan.max_messages}</strong> messages/month</li>`;
        } else {
            featuresList += '<li class="mb-2"><i class="fas fa-check text-success me-2"></i><strong>Unlimited</strong> messages</li>';
        }
        
        // Chat history
        if (plan.chat_history_days) {
            featuresList += `<li class="mb-2"><i class="fas fa-check text-success me-2"></i><strong>${plan.chat_history_days}-day</strong> chat history</li>`;
        }
        
        // Branding
        if (plan.branding_removed) {
            featuresList += '<li class="mb-2"><i class="fas fa-check text-success me-2"></i>White-label (no branding)</li>';
        } else {
            featuresList += '<li class="mb-2 text-muted"><i class="fas fa-times text-danger me-2"></i>White-label option</li>';
        }
        
        // API access
        if (plan.api_access) {
            featuresList += '<li class="mb-2"><i class="fas fa-check text-success me-2"></i>API access</li>';
        }
        
        card.innerHTML = `
      <div class="plan h-100 position-relative" data-plan-id="${plan.id}">
        ${popularBadge}
        <div class="text-center mb-4">
          <h3 class="mb-2">${plan.name}</h3>
          <h4 class="display-5 mb-0">${formattedPrice}</h4>
          ${plan.price > 0 ? '<small class="text-muted">per month</small>' : ''}
        </div>
        <p class="text-center mb-4">${plan.description || ''}</p>
        <ul class="list-unstyled">
          ${featuresList}
        </ul>
        <button class="btn btn-primary w-100 mt-3" onclick="selectPlan('${plan.id}')">
          ${plan.price === 0 ? 'Start Free' : 'Choose Plan'}
        </button>
      </div>
    `;
        pricingContainer.appendChild(card);
    });
}

// Populate plan select dropdown
async function populatePlanSelect() {
    const planSelect = document.getElementById('planSelect');
    planSelect.innerHTML = '<option value="">Choose a plan...</option>';
    
    console.log('Populating plans, available plans:', availablePlans);
    
    // Get user's location info
    const locationInfo = await getUserLocation();
    const isIndian = locationInfo.country === 'IN';
    
    availablePlans.forEach(plan => {
        const option = document.createElement('option');
        option.value = plan.id;
        const formattedPrice = formatPrice(plan.price, isIndian);
        option.textContent = `${plan.name} - ${plan.price === 0 ? 'Free' : formattedPrice + '/mo'}`;
        planSelect.appendChild(option);
    });
}

// Select plan function
function selectPlan(planId) {
    // Open registration modal with selected plan
    document.getElementById('registerBtn').click();
    // Pre-select the plan
    setTimeout(() => {
        document.getElementById('planSelect').value = planId;
    }, 100);
}

loadPlans();

// Check for payment success parameter and authentication messages
window.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const paymentStatus = urlParams.get('payment');
    const isRegistration = urlParams.get('registration') === 'complete';
    const authStatus = urlParams.get('auth');
    
    if (paymentStatus === 'success') {
        let message = '';
        if (isRegistration && localStorage.getItem('registration_pending') === 'true') {
            // This is a successful registration payment
            message = `
                <strong>Welcome aboard!</strong> Your payment was successful and your account is now active. 
                Please log in with your email (${localStorage.getItem('registered_email') || 'your registered email'}) to access your dashboard.
            `;
            // Clear the registration flags
            localStorage.removeItem('registration_pending');
            localStorage.removeItem('registered_email');
        } else {
            // Regular payment success
            message = `
                <strong>Payment Successful!</strong> Your subscription has been activated. Please log in to access your dashboard.
            `;
        }
        
        // Show success notification
        const successMessage = document.createElement('div');
        successMessage.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
        successMessage.style.zIndex = '9999';
        successMessage.style.maxWidth = '600px';
        successMessage.innerHTML = message + `
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.body.appendChild(successMessage);
        
        // Auto-open login modal after 2 seconds
        setTimeout(() => {
            document.getElementById('loginBtn').click();
        }, 2000);
        
        // Remove the payment parameter from URL
        window.history.replaceState({}, document.title, window.location.pathname);
    } else if (paymentStatus === 'cancelled') {
        // Show cancellation notification
        const cancelMessage = document.createElement('div');
        cancelMessage.className = 'alert alert-warning alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
        cancelMessage.style.zIndex = '9999';
        cancelMessage.innerHTML = `
            <strong>Payment Cancelled</strong> You can complete your registration by selecting a plan and trying again.
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.body.appendChild(cancelMessage);
        
        // Clear any registration flags
        localStorage.removeItem('registration_pending');
        localStorage.removeItem('registered_email');
        
        // Remove the payment parameter from URL
        window.history.replaceState({}, document.title, window.location.pathname);
    }
    
    // Handle authentication messages
    if (authStatus === 'required') {
        // Show message that authentication is required
        const authMessage = document.createElement('div');
        authMessage.className = 'alert alert-warning alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
        authMessage.style.zIndex = '9999';
        authMessage.style.maxWidth = '600px';
        authMessage.innerHTML = `
            <strong>Authentication Required</strong> Please log in to access the dashboard.
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.body.appendChild(authMessage);
        
        // Auto-open login modal
        setTimeout(() => {
            document.getElementById('loginBtn').click();
        }, 1000);
        
        // Remove the auth parameter from URL
        window.history.replaceState({}, document.title, window.location.pathname);
    } else if (authStatus === 'expired') {
        // Show message that session expired
        const expiredMessage = document.createElement('div');
        expiredMessage.className = 'alert alert-info alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
        expiredMessage.style.zIndex = '9999';
        expiredMessage.style.maxWidth = '600px';
        expiredMessage.innerHTML = `
            <strong>Session Expired</strong> Your session has expired. Please log in again.
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.body.appendChild(expiredMessage);
        
        // Auto-open login modal
        setTimeout(() => {
            document.getElementById('loginBtn').click();
        }, 1000);
        
        // Remove the auth parameter from URL
        window.history.replaceState({}, document.title, window.location.pathname);
    }
});

// Add toggle functionality
document.getElementById('toggleAuth').onclick = function(e) {
    e.preventDefault();
    const modalTitle = document.getElementById('authModalLabel');
    const toggleText = document.getElementById('toggleText');
    const toggleLink = document.getElementById('toggleAuth');
    const fullNameField = document.getElementById('fullNameField');
    
    if (modalTitle.innerText === 'Register') {
        modalTitle.innerText = 'Login';
        toggleText.innerText = "Don't have an account?";
        toggleLink.innerText = 'Register';
        fullNameField.style.display = 'none';
        document.getElementById('fullName').removeAttribute('required');
        document.getElementById('planField').style.display = 'none';
        document.getElementById('planSelect').removeAttribute('required');
    } else {
        modalTitle.innerText = 'Register';
        toggleText.innerText = 'Already have an account?';
        toggleLink.innerText = 'Login';
        fullNameField.style.display = 'block';
        document.getElementById('fullName').setAttribute('required', 'required');
        document.getElementById('planField').style.display = 'block';
        document.getElementById('planSelect').setAttribute('required', 'required');
        populatePlanSelect();
    }
}

// Scroll Animation
function handleScrollAnimation() {
    const elements = document.querySelectorAll('.animate-on-scroll');
    
    elements.forEach(element => {
        const elementTop = element.getBoundingClientRect().top;
        const elementBottom = element.getBoundingClientRect().bottom;
        const windowHeight = window.innerHeight;
        
        if (elementTop < windowHeight * 0.8 && elementBottom > 0) {
            element.classList.add('visible');
        }
    });
}

// Initialize scroll animations
handleScrollAnimation();
window.addEventListener('scroll', handleScrollAnimation);

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});
