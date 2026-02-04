import { refreshToken } from './auth';

export async function authFetch(url, options = {}) {
  const access = localStorage.getItem('access');

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (access) {
    headers.Authorization = `Bearer ${access}`;
  }

  let response = await fetch(url, {
    ...options,
    headers,
  });

  // 🔥 access 토큰 만료
  if (response.status === 401) {
    try {
      const newAccess = await refreshToken();

      // 토큰 갱신 후 재요청
      headers.Authorization = `Bearer ${newAccess}`;

      response = await fetch(url, {
        ...options,
        headers,
      });
    } catch (e) {
      // refresh도 만료 → 로그아웃
      localStorage.removeItem('access');
      localStorage.removeItem('refresh');
      window.location.href = '/login';
      throw e;
    }
  }

  return response;
}