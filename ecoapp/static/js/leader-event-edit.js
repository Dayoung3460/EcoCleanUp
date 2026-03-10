(() => {
  const startInput = document.getElementById('edit_start_time');
  const endInput = document.getElementById('edit_end_time');
  const durationInput = document.getElementById('edit_duration');
  const warningText = document.getElementById('edit_time_warning');
  const editEventForm = startInput ? startInput.form : null;

  if (!startInput || !endInput || !durationInput) {
    return;
  }

  const MINUTES_PER_DAY = 24 * 60;
  let isProgrammaticUpdate = false;

  const toMinutes = (timeValue) => {
    if (!timeValue || !timeValue.includes(':')) {
      return null;
    }

    const [hourText, minuteText] = timeValue.split(':');
    const hours = Number(hourText);
    const minutes = Number(minuteText);

    if (Number.isNaN(hours) || Number.isNaN(minutes)) {
      return null;
    }

    return (hours * 60) + minutes;
  };

  const toTimeString = (totalMinutes) => {
    const hours = String(Math.floor(totalMinutes / 60)).padStart(2, '0');
    const minutes = String(totalMinutes % 60).padStart(2, '0');
    return `${hours}:${minutes}`;
  };

  const withProgrammaticUpdate = (callback) => {
    isProgrammaticUpdate = true;
    callback();
    isProgrammaticUpdate = false;
  };

  const clearError = () => {
    startInput.classList.remove('is-invalid');
    endInput.classList.remove('is-invalid');
    durationInput.classList.remove('is-invalid');

    if (warningText) {
      warningText.textContent = '';
      warningText.classList.add('d-none');
    }
  };

  const showError = (message, fields = []) => {
    clearError();

    fields.forEach((field) => {
      field.classList.add('is-invalid');
    });

    if (warningText) {
      warningText.textContent = message;
      warningText.classList.remove('d-none');
    }
  };

  const updateDurationFromStartEnd = () => {
    const startMinutes = toMinutes(startInput.value);
    const endMinutes = toMinutes(endInput.value);

    if (startMinutes === null || endMinutes === null) {
      clearError();
      return;
    }

    if (endMinutes < startMinutes) {
      showError('End time must be after start time.', [startInput, endInput]);
      return;
    }

    clearError();

    withProgrammaticUpdate(() => {
      durationInput.value = String(endMinutes - startMinutes);
    });
  };

  const updateEndFromStartDuration = () => {
    const startMinutes = toMinutes(startInput.value);
    const durationMinutes = Number(durationInput.value);

    if (startMinutes === null || Number.isNaN(durationMinutes) || durationMinutes < 0) {
      clearError();
      return;
    }

    const endMinutes = startMinutes + durationMinutes;
    if (endMinutes >= MINUTES_PER_DAY) {
      showError('Calculated end time exceeds 24:00.', [durationInput, endInput]);
      return;
    }

    clearError();

    withProgrammaticUpdate(() => {
      endInput.value = toTimeString(endMinutes);
    });
  };

  startInput.addEventListener('input', () => {
    if (isProgrammaticUpdate) {
      return;
    }

    if (endInput.value) {
      updateDurationFromStartEnd();
      return;
    }

    if (durationInput.value) {
      updateEndFromStartDuration();
    }
  });

  endInput.addEventListener('input', () => {
    if (isProgrammaticUpdate) {
      return;
    }
    updateDurationFromStartEnd();
  });

  durationInput.addEventListener('input', () => {
    if (isProgrammaticUpdate) {
      return;
    }
    updateEndFromStartDuration();
  });

  const validateTimeFields = () => {
    const startMinutes = toMinutes(startInput.value);
    const endMinutes = toMinutes(endInput.value);
    const durationValue = durationInput.value;
    const hasDuration = durationValue !== '';
    const durationMinutes = Number(durationValue);

    if (hasDuration && (Number.isNaN(durationMinutes) || durationMinutes < 0)) {
      showError('Duration must be a non-negative number.', [durationInput]);
      return false;
    }

    if (startMinutes !== null && endMinutes !== null && endMinutes < startMinutes) {
      showError('End time must be after start time.', [startInput, endInput]);
      return false;
    }

    if (startMinutes !== null && hasDuration) {
      if ((startMinutes + durationMinutes) >= MINUTES_PER_DAY) {
        showError('Calculated end time exceeds 24:00.', [durationInput, endInput]);
        return false;
      }
    }

    clearError();
    return true;
  };

  if (editEventForm) {
    editEventForm.addEventListener('submit', (event) => {
      if (!validateTimeFields()) {
        event.preventDefault();
      }
    });
  }
})();