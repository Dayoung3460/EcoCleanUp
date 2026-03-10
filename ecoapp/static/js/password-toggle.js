function setupPasswordToggle(config) {
  const passwordInput = document.getElementById(config.inputId);
  const toggleButton = document.getElementById(config.buttonId);
  const eyeOpen = document.getElementById(config.eyeOpenId);
  const eyeSlash = document.getElementById(config.eyeSlashId);

  if (!passwordInput || !toggleButton || !eyeOpen || !eyeSlash) {
    return;
  }

  toggleButton.addEventListener('click', function () {
    const isHidden = passwordInput.type === 'password';
    passwordInput.type = isHidden ? 'text' : 'password';

    eyeOpen.style.display = isHidden ? 'none' : '';
    eyeSlash.style.display = isHidden ? '' : 'none';

    toggleButton.setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
    toggleButton.setAttribute('aria-pressed', isHidden ? 'true' : 'false');
  });
}

setupPasswordToggle({
  inputId: 'password',
  buttonId: 'togglePassword',
  eyeOpenId: 'eyeOpen',
  eyeSlashId: 'eyeSlash'
});

setupPasswordToggle({
  inputId: 'password',
  buttonId: 'toggleSignupPassword',
  eyeOpenId: 'signupPasswordEyeOpen',
  eyeSlashId: 'signupPasswordEyeSlash'
});

setupPasswordToggle({
  inputId: 'confirm_password',
  buttonId: 'toggleSignupConfirmPassword',
  eyeOpenId: 'signupConfirmPasswordEyeOpen',
  eyeSlashId: 'signupConfirmPasswordEyeSlash'
});