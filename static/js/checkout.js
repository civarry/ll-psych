/**
 * Checkout Payment Processing Script
 * Handles card payment form display and payment submission
 */

document.addEventListener('DOMContentLoaded', function() {
    const cardPaymentBtn = document.getElementById('cardPaymentBtn');
    const cardForm = document.getElementById('cardForm');
    const submitCardPayment = document.getElementById('submitCardPayment');
    
    // Show card form when card payment is selected
    cardPaymentBtn.addEventListener('click', function() {
      cardPaymentBtn.style.display = 'none';
      cardForm.style.display = 'block';
    });
    
    // Handle card payment submission
    submitCardPayment.addEventListener('click', function() {
      const cardNumber = document.getElementById('cardNumber').value;
      const expiryDate = document.getElementById('expiryDate').value;
      const cvc = document.getElementById('cvc').value;
      
      // Validate all required fields
      if (!validateCardDetails(cardNumber, expiryDate, cvc)) {
        return;
      }
      
      // Extract month and year from expiry date (MM/YY format)
      const [expMonth, expYear] = expiryDate.split('/');
      
      // Process the payment
      processPayment(cardNumber, expMonth, expYear, cvc);
    });
  
    /**
     * Validates card input details
     * @param {string} cardNumber - The card number
     * @param {string} expiryDate - The expiration date in MM/YY format
     * @param {string} cvc - The card security code
     * @returns {boolean} Whether the input is valid
     */
    function validateCardDetails(cardNumber, expiryDate, cvc) {
      // Basic validation
      if (!cardNumber || !expiryDate || !cvc) {
        alert('Please fill in all card details');
        return false;
      }
  
      // Check if expiry date matches MM/YY format
      if (!/^\d{1,2}\/\d{2}$/.test(expiryDate)) {
        alert('Expiry date should be in MM/YY format');
        return false;
      }
  
      // Check if card number has at least 13 digits (simplified validation)
      if (!/^\d{13,19}$/.test(cardNumber.replace(/\s/g, ''))) {
        alert('Please enter a valid card number');
        return false;
      }
  
      // Check if CVC is 3-4 digits
      if (!/^\d{3,4}$/.test(cvc)) {
        alert('CVC should be 3 or 4 digits');
        return false;
      }
  
      return true;
    }
  
    /**
     * Process the payment using the provided card details
     * @param {string} cardNumber - The card number
     * @param {string} expMonth - The expiration month
     * @param {string} expYear - The expiration year
     * @param {string} cvc - The card security code
     */
    function processPayment(cardNumber, expMonth, expYear, cvc) {
      // Display loading indicator
      submitCardPayment.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Processing...';
      submitCardPayment.disabled = true;
      
      // Create payment intent first
      fetch(paymentConfig.paymentIntentUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
      })
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          handlePaymentError('Error: ' + data.error);
          return;
        }
        
        const clientKey = paymentConfig.publicKey;
        const paymentIntentId = data.id;
        
        // Here you would normally use PayMongo's SDK to attach payment method
        // For test implementation, we'll just redirect to success
        alert('In production, this would process the payment with PayMongo. Redirecting to success page for testing.');
        window.location.href = paymentConfig.successUrl;
      })
      .catch(error => {
        handlePaymentError('There was an error processing your payment. Please try again.');
        console.error('Error:', error);
      });
    }
  
    /**
     * Handle payment errors
     * @param {string} message - The error message to display
     */
    function handlePaymentError(message) {
      alert(message);
      submitCardPayment.innerHTML = '<i class="bi bi-check-circle me-1"></i> Pay Now';
      submitCardPayment.disabled = false;
    }
  });