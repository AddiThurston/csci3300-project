window.handleCredentialResponse = function(response) {
  const payload = JSON.parse(atob(response.credential.split('.')[1]));
  const user = {
    email: payload.email,
    name: payload.name,
    picture: payload.picture,
    sub: payload.sub,
  };
  sessionStorage.setItem('user', JSON.stringify(user));
  sessionStorage.setItem('credential', response.credential);
  // Redirect or update UI as needed
  window.location.href = 'index.html';
};