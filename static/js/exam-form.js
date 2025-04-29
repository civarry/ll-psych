/**
 * exam-form.js - Common JavaScript for exam creation and editing
 * This handles both create and edit functionality for exams
 */
document.addEventListener('DOMContentLoaded', function() {
    // Common DOM elements
    const examTypeSelect = document.getElementById('exam-type');
    const contentSection = document.getElementById('content-section');
    const likertSection = document.getElementById('likert-section');
    const scoringSection = document.getElementById('scoring-rules-section');
    const questionsContainer = document.getElementById('likert-questions');
    const addQuestionBtn = document.getElementById('add-question');
    const likertValuesContainer = document.getElementById('likert-values-container');
    const addLikertValueBtn = document.getElementById('add-likert-value');
    const scoringRulesContainer = document.getElementById('scoring-rules-container');
    const addScoringZoneBtn = document.getElementById('add-scoring-zone');
    const scoringRulesInput = document.getElementById('scoring_rules') || document.getElementById('scoring-rules');
    const form = document.getElementById('exam-form');
    
    // Function to make input groups stack on mobile
    function makeInputGroupsResponsive() {
      document.querySelectorAll('.input-group').forEach(group => {
        if (window.innerWidth < 576) {
          group.classList.add('input-group-stacked');
        } else {
          group.classList.remove('input-group-stacked');
        }
      });
    }
    
    // Apply responsive styling to input groups
    window.addEventListener('resize', makeInputGroupsResponsive);
    makeInputGroupsResponsive();
    
    // Add additional CSS for responsive input groups if not already added
    if (!document.getElementById('responsive-input-groups-css')) {
      const style = document.createElement('style');
      style.id = 'responsive-input-groups-css';
      style.textContent = `
        @media (max-width: 575.98px) {
          .input-group-stacked {
            flex-direction: column;
          }
          .input-group-stacked > .input-group-text,
          .input-group-stacked > .form-control,
          .input-group-stacked > .btn {
            width: 100%;
            border-radius: 0.25rem !important;
            margin-bottom: 0.25rem;
          }
          .input-group-stacked > *:last-child {
            margin-bottom: 0;
          }
          .input-group-stacked > .input-group-text {
            text-align: left;
          }
        }
      `;
      document.head.appendChild(style);
    }
  
    /**
     * Toggle sections based on exam type selection
     */
    function toggleSectionsBasedOnType() {
      const isLikert = examTypeSelect.value === 'likert';
      
      // For create page elements that use d-none
      if (likertSection) {
        if (isLikert) {
          likertSection.classList.remove('d-none');
          contentSection.classList.add('d-none');
          scoringSection.classList.remove('d-none');
        } else {
          likertSection.classList.add('d-none');
          contentSection.classList.remove('d-none');
          scoringSection.classList.add('d-none');
        }
      } 
      // For edit page elements that use style.display
      else {
        contentSection.style.display = isLikert ? 'none' : 'block';
        document.getElementById('likert-section').style.display = isLikert ? 'block' : 'none';
        document.getElementById('scoring-rules-section').style.display = isLikert ? 'block' : 'none';
        document.getElementById('likert-scale-section').style.display = isLikert ? 'block' : 'none';
      }
    }
  
    // Set up event listeners for toggling sections
    if (examTypeSelect) {
      examTypeSelect.addEventListener('change', toggleSectionsBasedOnType);
      toggleSectionsBasedOnType(); // Initial setup
    }
  
    /**
     * Likert question management
     */
    if (addQuestionBtn) {
      addQuestionBtn.addEventListener('click', () => {
        const questionCount = questionsContainer.querySelectorAll('.input-group').length;
        const div = document.createElement('div');
        div.className = 'input-group mb-2';
        div.innerHTML = `
          <span class="input-group-text"><i class="bi bi-question-circle"></i></span>
          <input type="text" name="question_text" class="form-control" placeholder="Question ${questionCount + 1}" required>
          <button type="button" class="btn btn-outline-danger remove-question"><i class="bi bi-trash"></i></button>`;
        questionsContainer.appendChild(div);
        makeInputGroupsResponsive();
      });
  
      // Event delegation for removing questions
      questionsContainer.addEventListener('click', (e) => {
        if (e.target.closest('.remove-question')) {
          e.target.closest('.input-group').remove();
        }
      });
    }
  
    /**
     * Likert scale value management
     */
    if (addLikertValueBtn) {
      addLikertValueBtn.addEventListener('click', () => {
        const div = document.createElement('div');
        div.className = 'input-group mb-2';
        div.innerHTML = `
          <span class="input-group-text">Value</span>
          <input type="number" class="form-control" name="likert_value" required>
          <span class="input-group-text">Label</span>
          <input type="text" class="form-control" name="likert_label" required>
          <button type="button" class="btn btn-outline-danger remove-likert-value">
            <i class="bi bi-trash"></i>
          </button>`;
        likertValuesContainer.appendChild(div);
        makeInputGroupsResponsive();
      });
  
      // Event delegation for removing likert values
      likertValuesContainer.addEventListener('click', function (e) {
        if (e.target.closest('.remove-likert-value')) {
          e.target.closest('.input-group').remove();
        }
      });
    }
  
    /**
     * Scoring zones management
     */
    if (addScoringZoneBtn) {
      function addScoringZone(min = '', max = '', label = '') {
        const div = document.createElement('div');
        div.className = 'input-group mb-2';
        div.innerHTML = `
          <span class="input-group-text">Min</span>
          <input type="number" class="form-control" placeholder="Min" value="${min}" required>
          <span class="input-group-text">Max</span>
          <input type="number" class="form-control" placeholder="Max" value="${max}" required>
          <span class="input-group-text">Label</span>
          <input type="text" class="form-control" placeholder="Label" value="${label}" required>
          <button type="button" class="btn btn-outline-danger remove-scoring-zone"><i class="bi bi-trash"></i></button>`;
        scoringRulesContainer.appendChild(div);
        makeInputGroupsResponsive();
      }
  
      addScoringZoneBtn.addEventListener('click', () => addScoringZone());
  
      // Event delegation for removing scoring zones
      scoringRulesContainer.addEventListener('click', (e) => {
        if (e.target.closest('.remove-scoring-zone')) {
          e.target.closest('.input-group').remove();
        }
      });
  
      // Load existing scoring rules for edit page
      if (window.location.href.includes('edit') && typeof scoringRules !== 'undefined') {
        if (scoringRules && scoringRules.zones) {
          scoringRulesContainer.innerHTML = ''; // Clear default zone if editing
          scoringRules.zones.forEach(zone => addScoringZone(zone.min, zone.max, zone.label));
        }
      }
    }
  
    /**
     * Form submission - serialize scoring rules
     */
    if (form && scoringRulesInput) {
      form.addEventListener('submit', function (e) {
        const zones = [];
        const groups = scoringRulesContainer.querySelectorAll('.input-group');
        
        groups.forEach(group => {
          const inputs = group.querySelectorAll('input');
          if (inputs.length >= 3) {
            zones.push({
              min: parseInt(inputs[0].value, 10),
              max: parseInt(inputs[1].value, 10),
              label: inputs[2].value
            });
          }
        });
        
        scoringRulesInput.value = JSON.stringify({ zones });
      });
    }
  
    /**
     * Load existing data for edit page
     */
    function loadExistingData() {
      // Check if we're on the edit page
      if (!window.location.href.includes('edit')) return;
      
      if (examTypeSelect.value === 'likert') {
        // Load existing questions if provided
        if (typeof examQuestions !== 'undefined' && Array.isArray(examQuestions)) {
          questionsContainer.innerHTML = ''; // Clear existing content
          examQuestions.forEach((question, index) => {
            const div = document.createElement('div');
            div.className = 'input-group mb-2';
            div.innerHTML = `
              <span class="input-group-text"><i class="bi bi-question-circle"></i></span>
              <input type="text" name="question_text" class="form-control" value="${question.text}" placeholder="Question ${index + 1}" required>
              <button type="button" class="btn btn-outline-danger remove-question"><i class="bi bi-trash"></i></button>`;
            questionsContainer.appendChild(div);
          });
        }
        
        // Load existing Likert scale if provided
        if (typeof examLikertScale !== 'undefined' && typeof examLikertScale === 'object') {
          likertValuesContainer.innerHTML = ''; // Clear existing content
          Object.entries(examLikertScale).forEach(([value, label]) => {
            const div = document.createElement('div');
            div.className = 'input-group mb-2';
            div.innerHTML = `
              <span class="input-group-text">Value</span>
              <input type="number" class="form-control" name="likert_value" value="${value}" required>
              <span class="input-group-text">Label</span>
              <input type="text" class="form-control" name="likert_label" value="${label}" required>
              <button type="button" class="btn btn-outline-danger remove-likert-value">
                <i class="bi bi-trash"></i>
              </button>`;
            likertValuesContainer.appendChild(div);
          });
        }
      }
      
      makeInputGroupsResponsive();
    }
    
    // Try to load existing data
    try {
      loadExistingData();
    } catch (e) {
      console.log("Not on edit page or missing exam data", e);
    }
  });