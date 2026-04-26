export const fetchWithAuth = async (url, options = {}) => {
  let token = localStorage.getItem('access_token');
  
  if (!options.headers) {
    options.headers = {};
  }
  
  if (token) {
    options.headers['Authorization'] = `Bearer ${token}`;
  }

  let res = await fetch(url, options);

  // Intercept 401 Unauthorized
  if (res.status === 401) {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      localStorage.removeItem('access_token');
      window.dispatchEvent(new Event('auth_expired'));
      throw new Error('Session completely expired.');
    }

    try {
      // Attempt silent refresh
      const refreshRes = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken })
      });

      if (!refreshRes.ok) {
        throw new Error('Refresh token invalid or expired.');
      }

      const data = await refreshRes.json();
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      
      // Update bearer token and replay original request safely
      options.headers['Authorization'] = `Bearer ${data.access_token}`;
      
      // We must avoid sending a consumed body. For purely JSON queries this is fine.
      res = await fetch(url, options);
    } catch (err) {
      // If refresh fails, wipe local cache 
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.dispatchEvent(new Event('auth_expired'));
      throw new Error('Session completely expired.');
    }
  }

  return res;
};
