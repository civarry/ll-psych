document.addEventListener('DOMContentLoaded', function () {
  const examTypeSelect = document.getElementById('exam-type');
  const contentSection = document.getElementById('content-section');
  const likertSection = document.getElementById('likert-section');
  const scoringSection = document.getElementById('scoring-rules-section');
  const questionsContainer = document.getElementById('likert-questions');
  const addQuestionBtn = document.getElementById('add-question');
  const scoringRulesContainer = document.getElementById('scoring-rules-container');
  const addScoringZoneBtn = document.getElementById('add-scoring-zone');
  const scoringRulesInput = document.getElementById('scoring_rules');
  const form = document.getElementById('exam-form');
  const questionsJsonInput = document.getElementById('likert_questions_json');
  
  // Required fields for validation - handle both create and edit form field IDs
  const titleField = document.getElementById('title') || document.getElementById('exam-title');
  const priceField = document.getElementById('price') || document.getElementById('exam-price');
  const descriptionField = document.getElementById('description') || document.getElementById('exam-description');

  function createLikertValueRow(value = '', label = '') {
    const row = document.createElement('div');
    row.className = 'input-group mb-2';
    row.innerHTML = `
      <span class="input-group-text">Value</span>
      <input type="number" class="form-control" name="likert_value" value="${value}" required>
      <span class="input-group-text">Label</span>
      <input type="text" class="form-control" name="likert_label" value="${label}" required>
      <button type="button" class="btn btn-outline-danger remove-likert-value"><i class="bi bi-trash"></i></button>
    `;
    row.querySelector('.remove-likert-value').addEventListener('click', () => {
      row.remove();
    });
    return row;
  }

  function createQuestionBlock(text = '', scale = []) {
    const block = document.createElement('div');
    block.className = 'likert-question border rounded p-3 mb-3';

    block.innerHTML = `
      <div class="input-group mb-2">
        <span class="input-group-text"><i class="bi bi-question-circle"></i></span>
        <input type="text" name="question_text" class="form-control" placeholder="Enter question text" value="${text}" required>
        <button type="button" class="btn btn-outline-danger remove-question"><i class="bi bi-trash"></i></button>
      </div>

      <div class="likert-labels">
        <label class="form-label small fw-bold">Likert Labels for this Question</label>
        <div class="likert-values-container"></div>
        <button type="button" class="btn btn-sm btn-outline-secondary add-likert-value">
          <i class="bi bi-plus-circle me-1"></i> Add Likert Value
        </button>
      </div>
    `;

    const container = block.querySelector('.likert-values-container');

    if (Array.isArray(scale)) {
      scale.forEach(({ value, label }) => {
        const row = createLikertValueRow(value, label);
        container.appendChild(row);
      });
    } else {
      container.appendChild(createLikertValueRow());
    }

    block.querySelector('.add-likert-value').addEventListener('click', () => {
      container.appendChild(createLikertValueRow());
    });

    block.querySelector('.remove-question').addEventListener('click', () => {
      block.remove();
    });

    return block;
  }

  function toggleSections() {
    const isLikert = examTypeSelect.value === 'likert';
    if (likertSection && contentSection && scoringSection) {
      likertSection.classList.toggle('d-none', !isLikert);
      contentSection.classList.toggle('d-none', isLikert);
      scoringSection.classList.toggle('d-none', !isLikert);
    } else {
      document.getElementById('likert-section').style.display = isLikert ? 'block' : 'none';
      document.getElementById('scoring-rules-section').style.display = isLikert ? 'block' : 'none';
      contentSection.style.display = isLikert ? 'none' : 'block';
    }
  }

  if (addQuestionBtn) {
    addQuestionBtn.addEventListener('click', () => {
      const block = createQuestionBlock();
      questionsContainer.appendChild(block);
    });
  }

  if (addScoringZoneBtn) {
    addScoringZoneBtn.addEventListener('click', () => {
      const div = document.createElement('div');
      div.className = 'input-group mb-2';
      div.innerHTML = `
        <span class="input-group-text">Min</span>
        <input type="number" class="form-control" placeholder="Min" required>
        <span class="input-group-text">Max</span>
        <input type="number" class="form-control" placeholder="Max" required>
        <span class="input-group-text">Label</span>
        <input type="text" class="form-control" placeholder="Label" required>
        <button type="button" class="btn btn-outline-danger remove-scoring-zone"><i class="bi bi-trash"></i></button>
      `;
      div.querySelector('.remove-scoring-zone').addEventListener('click', () => div.remove());
      scoringRulesContainer.appendChild(div);
    });
  }

  if (form) {
    form.addEventListener('submit', function (event) {
      // Form validation for required fields
      const title = titleField?.value.trim() || '';
      const price = priceField?.value.trim() || '';
      const description = descriptionField?.value.trim() || '';
      
      // Check if required fields are empty
      if (!title || !price || !description) {
        // Prevent the form from submitting
        event.preventDefault();
        event.stopPropagation();
        
        // Add was-validated class for Bootstrap validation styles
        form.classList.add('was-validated');
        
        // Focus on the first empty required field
        if (!title && titleField) {
          titleField.focus();
        } else if (!price && priceField) {
          priceField.focus();
        } else if (!description && descriptionField) {
          descriptionField.focus();
        }
        
        return;
      }
      
      // Continue with form processing if validation passes
      if (questionsJsonInput) {
        const allQuestions = [];
        document.querySelectorAll('.likert-question').forEach((el, index) => {
          const questionText = el.querySelector('input[name="question_text"]').value;
          const scale = [];
          el.querySelectorAll('.likert-values-container .input-group').forEach(scaleEl => {
            const value = scaleEl.querySelector('input[name="likert_value"]').value;
            const label = scaleEl.querySelector('input[name="likert_label"]').value;
            scale.push({ value: parseInt(value), label });
          });
          allQuestions.push({ id: index + 1, text: questionText, scale });
        });
        questionsJsonInput.value = JSON.stringify(allQuestions);
      }

      if (scoringRulesInput) {
        const zones = [];
        scoringRulesContainer.querySelectorAll('.input-group').forEach(group => {
          const [minInput, maxInput, labelInput] = group.querySelectorAll('input');
          zones.push({
            min: parseInt(minInput.value, 10),
            max: parseInt(maxInput.value, 10),
            label: labelInput.value
          });
        });
        scoringRulesInput.value = JSON.stringify({ zones });
      }
    });
  }

  function preloadQuestions() {
    if (!window.location.href.includes('edit') || typeof examQuestions === 'undefined') return;
    questionsContainer.innerHTML = '';
    examQuestions.forEach(q => {
      const block = createQuestionBlock(q.text, q.scale || []);
      questionsContainer.appendChild(block);
    });
  }

  function preloadScoringRules() {
    if (!window.location.href.includes('edit') || typeof scoringRules === 'undefined') return;
    if (scoringRules && Array.isArray(scoringRules.zones)) {
      scoringRulesContainer.innerHTML = '';
      scoringRules.zones.forEach(zone => {
        const div = document.createElement('div');
        div.className = 'input-group mb-2';
        div.innerHTML = `
          <span class="input-group-text">Min</span>
          <input type="number" class="form-control" placeholder="Min" value="${zone.min}" required>
          <span class="input-group-text">Max</span>
          <input type="number" class="form-control" placeholder="Max" value="${zone.max}" required>
          <span class="input-group-text">Label</span>
          <input type="text" class="form-control" placeholder="Label" value="${zone.label}" required>
          <button type="button" class="btn btn-outline-danger remove-scoring-zone"><i class="bi bi-trash"></i></button>
        `;
        div.querySelector('.remove-scoring-zone').addEventListener('click', () => div.remove());
        scoringRulesContainer.appendChild(div);
      });
    }
  }

  if (examTypeSelect) {
    examTypeSelect.addEventListener('change', toggleSections);
    toggleSections();
  }

  // Add input event listeners to remove error styling when user starts typing
  if (titleField || priceField || descriptionField) {
    [titleField, priceField, descriptionField].filter(Boolean).forEach(field => {
      field.addEventListener('input', function() {
        if (field.value.trim()) {
          field.classList.remove('is-invalid');
        }
      });
    });
  }

  preloadQuestions();
  preloadScoringRules();
});