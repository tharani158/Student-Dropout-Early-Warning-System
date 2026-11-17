const password = document.querySelector('#password');
const toggle = document.querySelector('#toggle-password');
const form = document.querySelector('#login-form');

toggle.addEventListener('click', () => {
  const showPassword = password.type === 'password';
  password.type = showPassword ? 'text' : 'password';
  toggle.textContent = showPassword ? 'Hide' : 'Show';
  toggle.setAttribute('aria-label', showPassword ? 'Hide password' : 'Show password');
  toggle.setAttribute('aria-pressed', String(showPassword));
});

form.addEventListener('submit', event => {
  event.preventDefault();
  window.location.assign('/dashboard');
});
